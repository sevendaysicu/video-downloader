import os
import re
import time
import random
import threading
from urllib.parse import urlparse, parse_qs

# Kivy UI 组件
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.clock import Clock, mainthread
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import platform

# 全局中文字体支持
from kivy.core.text import LabelBase, DEFAULT_FONT
LabelBase.register(DEFAULT_FONT, 'font.ttf')

# 网络通信组件
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def clamp_progress(current, total, complete=False):
    if total <= 0:
        return 100 if complete else 0
    percent = int((current / total) * 100)
    if complete:
        return max(0, min(percent, 100))
    return max(0, min(percent, 99))


def trim_log_lines(existing_text, message, max_lines=35):
    lines = existing_text.splitlines() if existing_text else ["运行日志:"]
    if not lines:
        lines = ["运行日志:"]
    if lines[0] != "运行日志:":
        lines.insert(0, "运行日志:")
    lines.append(str(message))
    if len(lines) > max_lines:
        lines = [lines[0]] + lines[-(max_lines - 1):]
    return "\n".join(lines)


class VideoDownloaderAndroid(App):
    COLORS = {
        "background": (0.059, 0.090, 0.165, 1),
        "surface": (0.067, 0.094, 0.153, 1),
        "surface_alt": (0.090, 0.125, 0.200, 1),
        "border": (1, 1, 1, 0.08),
        "text": (0.973, 0.980, 0.988, 1),
        "muted": (0.580, 0.640, 0.720, 1),
        "primary": (0.220, 0.741, 0.973, 1),
        "primary_dark": (0.031, 0.184, 0.286, 1),
        "success": (0.133, 0.773, 0.369, 1),
        "warning": (0.961, 0.620, 0.043, 1),
        "danger": (0.937, 0.267, 0.267, 1),
    }

    def build(self):
        self.title = "视频下载器"
        self.base_url = ""
        self.params = {}
        self.save_dir = ""
        self.is_downloading = False
        self.progress_percent = 0
        
        # 预设估计最大切片数（用于计算进度百分比，捕获到 EOF 后会自动更新精确值）
        self.estimated_total = 100 
        
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])

        root = BoxLayout(orientation='vertical')
        self.apply_background(root, self.COLORS["background"])

        scroll = ScrollView()
        content = BoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(18), dp(16), dp(18)],
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))

        content.add_widget(self.build_header())
        content.add_widget(self.build_progress_card())
        content.add_widget(self.build_input_card())
        content.add_widget(self.build_action_area())
        content.add_widget(self.build_log_card())

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.set_status("就绪", "等待下载任务", "粘贴 Request URL 后开始下载")
        self.update_progress(0, self.estimated_total)
        return root

    def build_header(self):
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(64), spacing=dp(12))

        title_box = BoxLayout(orientation='vertical', spacing=dp(2))
        title_box.add_widget(Label(
            text="视频下载器",
            color=self.COLORS["text"],
            font_size=dp(22),
            bold=True,
            halign="left",
            valign="bottom",
        ))
        title_box.add_widget(Label(
            text="切片抓取与合并工具",
            color=self.COLORS["muted"],
            font_size=dp(13),
            halign="left",
            valign="top",
        ))
        for child in title_box.children:
            child.bind(size=child.setter('text_size'))
        header.add_widget(title_box)

        self.status_pill = Label(
            text="就绪",
            color=self.COLORS["text"],
            size_hint=(None, None),
            width=dp(78),
            height=dp(36),
            font_size=dp(13),
            bold=True,
        )
        self.apply_background(self.status_pill, self.COLORS["surface_alt"], radius=18)
        header.add_widget(self.status_pill)
        return header

    def build_progress_card(self):
        card = self.create_card(height=dp(132))
        card.add_widget(Label(
            text="任务状态",
            color=self.COLORS["muted"],
            size_hint_y=None,
            height=dp(22),
            font_size=dp(12),
            bold=True,
            halign="left",
        ))
        self.status_title = Label(
            text="等待下载任务",
            color=self.COLORS["text"],
            size_hint_y=None,
            height=dp(30),
            font_size=dp(18),
            bold=True,
            halign="left",
        )
        self.status_title.bind(size=self.status_title.setter('text_size'))
        card.add_widget(self.status_title)

        self.progress_bar = Widget(size_hint_y=None, height=dp(10))
        self.progress_bar.bind(pos=self.update_progress_graphics, size=self.update_progress_graphics)
        with self.progress_bar.canvas:
            Color(*self.COLORS["surface_alt"])
            self.progress_track_rect = RoundedRectangle(pos=self.progress_bar.pos, size=self.progress_bar.size, radius=[dp(5)])
            Color(*self.COLORS["primary"])
            self.progress_fill_rect = RoundedRectangle(pos=self.progress_bar.pos, size=(0, dp(10)), radius=[dp(5)])
        card.add_widget(self.progress_bar)

        self.progress_detail = Label(
            text="0% · 0 / 100 切片",
            color=self.COLORS["muted"],
            size_hint_y=None,
            height=dp(24),
            font_size=dp(13),
            halign="left",
        )
        self.progress_detail.bind(size=self.progress_detail.setter('text_size'))
        card.add_widget(self.progress_detail)

        self.status_detail = Label(
            text="粘贴 Request URL 后开始下载",
            color=self.COLORS["muted"],
            size_hint_y=None,
            height=dp(30),
            font_size=dp(12),
            halign="left",
            valign="top",
        )
        self.status_detail.bind(size=self.status_detail.setter('text_size'))
        card.add_widget(self.status_detail)
        return card

    def build_input_card(self):
        card = self.create_card(height=dp(220))
        card.add_widget(Label(
            text="Request URL",
            color=self.COLORS["text"],
            size_hint_y=None,
            height=dp(28),
            font_size=dp(16),
            bold=True,
            halign="left",
        ))
        self.url_input = TextInput(
            multiline=True,
            hint_text="示例: https://example.com/hls/video/CLS-001.jpg?v=6&auth=...",
            size_hint_y=None,
            height=dp(130),
            background_color=(1, 1, 1, 0.06),
            foreground_color=self.COLORS["text"],
            hint_text_color=(0.580, 0.640, 0.720, 0.85),
            cursor_color=self.COLORS["primary"],
            padding=[dp(12), dp(12), dp(12), dp(12)],
            font_size=dp(14),
        )
        card.add_widget(self.url_input)
        helper = Label(
            text="需要包含 CLS-001.jpg 这类切片序列和完整鉴权参数。",
            color=self.COLORS["muted"],
            size_hint_y=None,
            height=dp(28),
            font_size=dp(12),
            halign="left",
        )
        helper.bind(size=helper.setter('text_size'))
        card.add_widget(helper)
        return card

    def build_action_area(self):
        actions = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(112))

        self.main_btn = Button(
            text="开始下载",
            size_hint_y=None,
            height=dp(52),
            color=self.COLORS["primary_dark"],
            background_normal="",
            background_down="",
            background_color=self.COLORS["primary"],
            bold=True,
            font_size=dp(16),
        )
        self.main_btn.bind(on_press=self.start_download_flow)
        actions.add_widget(self.main_btn)

        secondary = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
        self.merge_btn = Button(
            text="合并视频",
            color=self.COLORS["text"],
            background_normal="",
            background_down="",
            background_color=self.COLORS["surface_alt"],
            font_size=dp(14),
        )
        self.merge_btn.bind(on_press=self.merge_slices)
        secondary.add_widget(self.merge_btn)

        self.open_dir_btn = Button(
            text="文件位置",
            color=self.COLORS["text"],
            background_normal="",
            background_down="",
            background_color=self.COLORS["surface_alt"],
            font_size=dp(14),
        )
        self.open_dir_btn.bind(on_press=self.open_directory)
        secondary.add_widget(self.open_dir_btn)
        actions.add_widget(secondary)
        return actions

    def build_log_card(self):
        card = self.create_card(height=dp(260))
        card.add_widget(Label(
            text="运行日志",
            color=self.COLORS["text"],
            size_hint_y=None,
            height=dp(28),
            font_size=dp(16),
            bold=True,
            halign="left",
        ))
        scroll = ScrollView(size_hint_y=None, height=dp(196))
        self.log_label = Label(
            text="运行日志:",
            size_hint_y=None,
            color=self.COLORS["muted"],
            font_size=dp(12),
            halign="left",
            valign="top",
        )
        self.log_label.bind(size=self.log_label.setter('text_size'))
        self.log_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
        scroll.add_widget(self.log_label)
        card.add_widget(scroll)
        return card

    def create_card(self, height):
        card = BoxLayout(
            orientation='vertical',
            padding=[dp(14), dp(12), dp(14), dp(12)],
            spacing=dp(8),
            size_hint_y=None,
            height=height,
        )
        self.apply_background(card, self.COLORS["surface"], radius=12)
        return card

    def apply_background(self, widget, color, radius=0):
        with widget.canvas.before:
            widget._bg_color = Color(*color)
            if radius:
                widget._bg_rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
            else:
                widget._bg_rect = Rectangle(pos=widget.pos, size=widget.size)
        widget.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, instance, value):
        if hasattr(instance, "_bg_rect"):
            instance._bg_rect.pos = instance.pos
            instance._bg_rect.size = instance.size

    def update_progress_graphics(self, instance, value):
        if not hasattr(self, "progress_track_rect"):
            return
        self.progress_track_rect.pos = instance.pos
        self.progress_track_rect.size = instance.size
        self.progress_fill_rect.pos = instance.pos
        fill_width = instance.width * (self.progress_percent / 100)
        self.progress_fill_rect.size = (fill_width, instance.height)

    # 【防爆显存安全日志机制】永远只保留屏幕最新的 35 行，确保丝滑滚动不隐身
    @mainthread
    def log(self, message):
        self.log_label.text = trim_log_lines(self.log_label.text, message)

    @mainthread
    def set_status(self, state, message, detail=""):
        state_colors = {
            "就绪": self.COLORS["surface_alt"],
            "下载中": self.COLORS["primary"],
            "完成": self.COLORS["success"],
            "错误": self.COLORS["danger"],
            "警告": self.COLORS["warning"],
        }
        self.status_pill.text = state
        self.status_pill.color = self.COLORS["primary_dark"] if state in ("下载中", "完成", "警告") else self.COLORS["text"]
        if hasattr(self.status_pill, "_bg_color"):
            self.status_pill._bg_color.rgba = state_colors.get(state, self.COLORS["surface_alt"])
        self.status_title.text = str(message)
        self.status_detail.text = str(detail)

    @mainthread
    def update_progress(self, current, total, complete=False):
        self.progress_percent = clamp_progress(current, total, complete=complete)
        safe_total = max(total, 0)
        self.progress_detail.text = f"{self.progress_percent}% · {current} / {safe_total} 切片"
        if hasattr(self, "progress_bar"):
            self.update_progress_graphics(self.progress_bar, None)

    @mainthread
    def set_downloading_ui(self, active):
        self.main_btn.disabled = active
        self.main_btn.text = "下载中..." if active else "开始下载"

    def start_download_flow(self, instance):
        raw_url = self.url_input.text.strip()
        if not raw_url:
            self.log("[错误] 输入框内容为空，请粘贴网址。")
            self.set_status("错误", "缺少 Request URL", "请粘贴完整的 https 链接")
            return
        if self.is_downloading:
            return
            
        self.log("\n" + "="*30)
        self.log("[*] 正在分析 Request URL 特征...")
        self.set_status("下载中", "正在分析 Request URL", "请保持应用在前台")
        self.update_progress(0, self.estimated_total)
        
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            self.log("[错误] 链接不合法，必须包含 https:// 开头。")
            self.set_status("错误", "链接格式不正确", "URL 必须以 http:// 或 https:// 开头")
            return
            
        parsed = urlparse(raw_url)
        if not parsed.netloc or '.' not in parsed.netloc:
            self.log("[错误] 网址缺失核心服务器域名。")
            self.set_status("错误", "缺少服务器域名", "请确认复制的是完整 Request URL")
            return

        if not re.search(r'CLS-\d+\.jpg', raw_url):
            self.log("[错误] 该链接不包含 CLS-xxx.jpg 切片序列特征。")
            self.set_status("错误", "未识别到切片序列", "链接中需要包含 CLS-001.jpg 这类文件名")
            return

        if not self.parse_url_parameters(raw_url):
            return
            
        self.is_downloading = True
        self.set_downloading_ui(True)
        threading.Thread(target=self.download_logic, daemon=True).start()

    def parse_url_parameters(self, raw_url):
        try:
            parsed_url = urlparse(raw_url)
            queries = parse_qs(parsed_url.query)
            self.params = {k: v[0] for k, v in queries.items()}
            
            path = parsed_url.path
            standard_path = re.sub(r'CLS-\d+\.jpg', 'CLS-{:03d}.jpg', path)
            self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{standard_path}"
            
            video_id_match = re.search(r'/hls/([^/]+)/', path)
            video_id = video_id_match.group(1) if video_id_match else "default_video"
            
            if platform == 'android':
                from android.storage import primary_external_storage_path
                downloads_path = os.path.join(primary_external_storage_path(), "Download")
                self.save_dir = os.path.join(downloads_path, f"slices_{video_id}")
            else:
                self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"slices_{video_id}")
                
            os.makedirs(self.save_dir, exist_ok=True)
            self.set_status("下载中", "下载环境已就绪", f"服务器: {parsed_url.netloc}\n缓存目录: {self.save_dir}")
            self.log("[+] 目标链识别成功，准备进入高频拉取阶段...")
            return True
        except Exception as e:
            self.set_status("错误", "解析 Request URL 失败", str(e))
            self.log(f"[错误] 静态解析失败: {str(e)}")
            return False

    def create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://rou.video/",
            "Connection": "keep-alive"
        })
        return session

    def download_worker(self, index):
        try:
            target_path = os.path.join(self.save_dir, f"CLS-{index:03d}.bin")
            if os.path.exists(target_path) and os.path.getsize(target_path) > 100000:
                return "EXISTS"
                
            url = self.base_url.format(index)
            session = self.create_session()
            time.sleep(random.uniform(0.05, 0.15)) # 略微加快下载频率
            
            response = session.get(url, params=self.params, timeout=10, verify=False)
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
        except Exception as e:
            # 截取前 30 个字符作为精简错误输出，防止撑爆屏幕
            return f"NET_ERR_{str(e)[:30]}"
        finally:
            if 'session' in locals():
                session.close()

    def download_logic(self):
        try:
            self.log("[*] 高并发进度监听打捞引擎启动...")
            continuous_errors = 0
            
            for idx in range(1, 600):
                if not self.is_downloading:
                    break
                
                res = self.download_worker(idx)
                
                # 计算并输出当前进度的数字百分比
                progress_percent = clamp_progress(idx, self.estimated_total)
                self.update_progress(idx, self.estimated_total)
                progress_text = f" -> 进度: {progress_percent}% ({idx}/{self.estimated_total})"
                
                if res == "EOF":
                    # 再次校验确认真实尾部
                    if self.download_worker(idx + 1) == "EOF":
                        self.estimated_total = idx - 1
                        self.update_progress(self.estimated_total, self.estimated_total, complete=True)
                        self.set_status("完成", "切片下载完成", "可以点击合并视频")
                        self.log(f"\n[完成] 进度: 100% ({self.estimated_total}/{self.estimated_total})")
                        self.log("[完成] 成功捕获流尾部信号，切片拉取完毕。")
                        break
                elif res == "SUCCESS":
                    self.log(f"[+] 成功固化: CLS-{idx:03d}.bin" + progress_text)
                    continuous_errors = 0
                elif res == "EXISTS":
                    self.log(f"[-] 跳过重复: CLS-{idx:03d}.bin" + progress_text)
                    continuous_errors = 0
                elif res.startswith("AUTH_ERR_"):
                    code = res.split('_')[-1]
                    self.set_status("错误", "鉴权失败", "auth/exp 参数可能过期或复制不完整")
                    self.log(f"[错误] 权限遭拒: CLS-{idx:03d} 状态码 {code}。鉴权参数可能过期或复制不全。")
                    continuous_errors += 1
                elif res.startswith("SERVER_ERR_"):
                    code = res.split('_')[-1]
                    self.set_status("警告", "服务器响应异常", f"CLS-{idx:03d} 状态码: {code}")
                    self.log(f"[警告] 服务器响应异常: CLS-{idx:03d} 状态码 {code}")
                    continuous_errors += 1
                elif res.startswith("NET_ERR_"):
                    err_info = res.replace("NET_ERR_", "")
                    self.set_status("警告", "网络波动", err_info)
                    self.log(f"[警告] 网络波动: CLS-{idx:03d} 失败: {err_info}")
                    continuous_errors += 1
                
                # 连续失败 10 次才进行硬拉闸，给网络波动留够容错空间
                if continuous_errors >= 10:
                    self.set_status("错误", "连续请求失败", "请检查 ? 后面的鉴权参数是否完整")
                    self.log("\n[错误] 连续 10 个切片请求失败。请检查链接中 ? 后面的鉴权参数是否完整。")
                    break
                    
            self.log("\n[完成] 下载流程结束。请点击【合并视频】。")
        except Exception as e:
            self.set_status("错误", "下载线程异常", str(e))
            self.log(f"\n[线程崩溃]: {str(e)}")
        finally:
            self.is_downloading = False
            Clock.schedule_once(lambda dt: self.set_downloading_ui(False))

    def merge_slices(self, instance):
        if not self.save_dir or not os.path.exists(self.save_dir):
            self.log("[错误] 下载路径为空或不存在。")
            self.set_status("错误", "没有可合并的目录", "请先完成切片下载")
            return
        files = [f for f in os.listdir(self.save_dir) if f.endswith(".bin")]
        files.sort()
        if not files:
            self.log("[错误] 未侦测到可拼装的数据块。")
            self.set_status("错误", "未找到切片文件", "请先下载或确认保存目录")
            return
            
        parent_dir = os.path.dirname(self.save_dir)
        video_name = os.path.basename(self.save_dir).replace("slices_", "video_")
        output_mp4 = os.path.join(parent_dir, f"{video_name}.mp4")
        
        self.log(f"[*] 正在将这 {len(files)} 个数据流进行物理二进制拼接...")
        self.set_status("下载中", "正在合并视频", f"共 {len(files)} 个切片")
        try:
            with open(output_mp4, "wb") as out_f:
                for f in files:
                    with open(os.path.join(self.save_dir, f), "rb") as in_f:
                        out_f.write(in_f.read())
            self.set_status("完成", "视频合并完成", output_mp4)
            self.log(f"\n[完成] 物理合流成功，MP4 已归档至 Download 目录:\n{output_mp4}")
        except Exception as e:
            self.set_status("错误", "合并失败", str(e))
            self.log(f"[合并失败] {str(e)}")

    def open_directory(self, instance):
        if platform == 'android':
            self.log("\n[提示] 视频文件和缓存均保存在手机系统的【文件管理】 -> 【内部存储】 -> 【Download】 中。")
        else:
            if self.save_dir and os.path.exists(self.save_dir):
                os.startfile(self.save_dir)

if __name__ == "__main__":
    VideoDownloaderAndroid().run()
