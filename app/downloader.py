"""切片并发下载引擎"""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3

from app.config import (
    MAX_WORKERS, MAX_INDEX, REQUEST_TIMEOUT,
    MAX_CONTINUOUS_ERRORS, MIN_VALID_SLICE_SIZE,
    RETRY_TOTAL, RETRY_BACKOFF, RETRY_STATUS_CODES,
    DEFAULT_HEADERS, VERIFY_SSL,
)

# 若不验证 SSL，则禁用不安全连接警告，避免刷屏日志
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DownloadEngine:
    """并发下载引擎：线程池滑动窗口 + Session 连接池复用

    通过回调函数与 UI 层解耦，不依赖 Kivy。
    """

    def __init__(self, base_url, params, save_dir,
                 on_progress=None, on_log=None, on_status=None,
                 on_complete=None):
        """
        Args:
            base_url: 带 {:03d} 占位符的切片 URL 模板
            params: 鉴权查询参数字典
            save_dir: 切片保存目录
            on_progress: 进度回调 (current, total)
            on_log: 日志回调 (message)
            on_status: 状态回调 (state, message, detail)
            on_complete: 下载完成回调 (total_slices)
        """
        self.base_url = base_url
        self.params = params
        self.save_dir = save_dir

        # 回调函数（与 UI 解耦）
        self.on_progress = on_progress or (lambda *a: None)
        self.on_log = on_log or (lambda msg: None)
        self.on_status = on_status or (lambda *a: None)
        self.on_complete = on_complete or (lambda total: None)

        self._running = False
        self.actual_total = 0
        self.total_known = False

    @property
    def is_running(self):
        return self._running

    def cancel(self):
        """请求取消当前下载"""
        self._running = False

    def _create_session(self):
        """创建带重试和连接池的 HTTP Session"""
        session = requests.Session()
        retries = Retry(
            total=RETRY_TOTAL,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=RETRY_STATUS_CODES,
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.headers.update(DEFAULT_HEADERS)
        return session

    def _download_worker(self, index, session):
        """下载单个切片，使用共享 Session 复用 TCP 连接池"""
        try:
            target_path = os.path.join(self.save_dir, f"CLS-{index:03d}.bin")
            if (os.path.exists(target_path)
                    and os.path.getsize(target_path) > MIN_VALID_SLICE_SIZE):
                return "EXISTS"

            url = self.base_url.format(index)
            response = session.get(
                url, params=self.params,
                timeout=REQUEST_TIMEOUT, verify=VERIFY_SSL,
            )
            if response.status_code in [400, 404]:
                return "EOF"
            elif response.status_code == 200:
                with open(target_path, "wb") as f:
                    f.write(response.content)
                return "SUCCESS"
            elif response.status_code in [401, 403]:
                return f"AUTH_ERR_{response.status_code}"
            else:
                return f"SERVER_ERR_{response.status_code}"
        except requests.exceptions.SSLError:
            return "SSL_ERR"
        except Exception as e:
            # 截取前 30 个字符作为精简错误输出，防止撑爆屏幕
            return f"NET_ERR_{str(e)[:30]}"

    def run(self):
        """执行并发下载（应在后台线程中调用）"""
        self._running = True
        session = self._create_session()
        try:
            self.on_log(
                f"[*] 并发下载引擎启动（{MAX_WORKERS} 线程连接池复用）..."
            )

            continuous_errors = 0
            downloaded_count = 0
            eof_index = None  # 首次遇到 EOF 的切片索引

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                pending = {}  # {future: slice_index}
                next_idx = 1

                # 预提交初始批次任务填满线程池
                for i in range(1, min(MAX_WORKERS, MAX_INDEX) + 1):
                    f = executor.submit(self._download_worker, i, session)
                    pending[f] = i
                next_idx = min(MAX_WORKERS, MAX_INDEX) + 1

                while pending:
                    if not self._running:
                        for f in pending:
                            f.cancel()
                        break

                    # 收集已完成的 futures
                    done = [f for f in pending if f.done()]
                    if not done:
                        time.sleep(0.02)
                        continue

                    for future in done:
                        idx = pending.pop(future)
                        try:
                            res = future.result()
                        except Exception as e:
                            res = f"NET_ERR_{str(e)[:30]}"

                        if res == "EOF":
                            # 记录最小 EOF 索引作为真实流尾边界
                            if eof_index is None or idx < eof_index:
                                eof_index = idx
                        elif res == "SUCCESS":
                            downloaded_count += 1
                            continuous_errors = 0
                            self.on_progress(downloaded_count, 0)
                            self.on_log(
                                f"[+] 成功固化: CLS-{idx:03d}.bin"
                                f" -> 已下载 {downloaded_count} 个切片"
                            )
                        elif res == "EXISTS":
                            downloaded_count += 1
                            continuous_errors = 0
                            self.on_progress(downloaded_count, 0)
                            self.on_log(
                                f"[-] 跳过重复: CLS-{idx:03d}.bin"
                                f" -> 已下载 {downloaded_count} 个切片"
                            )
                        elif res.startswith("AUTH_ERR_"):
                            code = res.split('_')[-1]
                            self.on_status(
                                "错误", "鉴权失败",
                                "auth/exp 参数可能过期或复制不完整",
                            )
                            self.on_log(
                                f"[错误] 权限遭拒: CLS-{idx:03d} 状态码 {code}。"
                                "鉴权参数可能过期或复制不全。"
                            )
                            continuous_errors += 1
                        elif res.startswith("SERVER_ERR_"):
                            code = res.split('_')[-1]
                            self.on_status(
                                "警告", "服务器响应异常",
                                f"CLS-{idx:03d} 状态码: {code}",
                            )
                            self.on_log(
                                f"[警告] 服务器响应异常:"
                                f" CLS-{idx:03d} 状态码 {code}"
                            )
                            continuous_errors += 1
                        elif res.startswith("NET_ERR_"):
                            err_info = res.replace("NET_ERR_", "")
                            self.on_status("警告", "网络波动", err_info)
                            self.on_log(
                                f"[警告] 网络波动:"
                                f" CLS-{idx:03d} 失败: {err_info}"
                            )
                            continuous_errors += 1
                        elif res == "SSL_ERR":
                            self.on_status(
                                "错误", "SSL 验证失败",
                                "请在 config.py 中将 VERIFY_SSL 设为 False 重新打包",
                            )
                            self.on_log(
                                f"[错误] SSL 证书验证失败: CLS-{idx:03d}。"
                                "若目标网站证书无效，请将 config.py 的 VERIFY_SSL 改为 False 重新编译。"
                            )
                            continuous_errors += 1

                        # 连续失败硬拉闸
                        if continuous_errors >= MAX_CONTINUOUS_ERRORS:
                            self.on_status(
                                "错误", "连续请求失败",
                                "请检查 ? 后面的鉴权参数是否完整",
                            )
                            self.on_log(
                                f"\n[错误] 连续 {MAX_CONTINUOUS_ERRORS}"
                                " 个切片请求失败。"
                                "请检查链接中 ? 后面的鉴权参数是否完整。"
                            )
                            for f in pending:
                                f.cancel()
                            pending.clear()
                            break

                        # 未到 EOF 且未超阈值，继续提交新任务（滑动窗口）
                        if (eof_index is None
                                and continuous_errors < MAX_CONTINUOUS_ERRORS
                                and next_idx <= MAX_INDEX
                                and self._running):
                            f = executor.submit(
                                self._download_worker, next_idx, session,
                            )
                            pending[f] = next_idx
                            next_idx += 1

            # EOF 收尾
            if eof_index is not None:
                self.actual_total = eof_index - 1
                self.total_known = True
                self.on_complete(self.actual_total)

            self.on_log("\n[完成] 下载流程结束。请点击【合并视频】。")
        except Exception as e:
            self.on_status("错误", "下载线程异常", str(e))
            self.on_log(f"\n[线程崩溃]: {str(e)}")
        finally:
            session.close()
            self._running = False
