"""下载引擎单元测试（Mock 网络请求）"""
import os
from unittest.mock import patch, MagicMock

from app.downloader import DownloadEngine


def _make_engine(tmp_path, **overrides):
    """创建测试用 DownloadEngine 实例"""
    defaults = dict(
        base_url="https://cdn.test.com/hls/vid/CLS-{:03d}.jpg",
        params={"auth": "token123"},
        save_dir=str(tmp_path),
    )
    defaults.update(overrides)
    return DownloadEngine(**defaults)


class TestDownloadEngineInit:
    """初始化与属性测试"""

    def test_default_callbacks_are_noop(self, tmp_path):
        engine = _make_engine(tmp_path)
        # 默认回调不应抛出异常
        engine.on_progress(1, 0)
        engine.on_log("test")
        engine.on_status("ok", "msg", "detail")
        engine.on_complete(10)

    def test_is_running_initially_false(self, tmp_path):
        engine = _make_engine(tmp_path)
        assert engine.is_running is False

    def test_cancel_sets_running_false(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine._running = True
        engine.cancel()
        assert engine.is_running is False


class TestDownloadWorker:
    """_download_worker 单元测试"""

    def test_existing_large_file_returns_exists(self, tmp_path):
        """已存在且大于阈值的文件应返回 EXISTS"""
        engine = _make_engine(tmp_path)
        target = os.path.join(str(tmp_path), "CLS-001.bin")
        # 创建一个 > 100KB 的文件
        with open(target, "wb") as f:
            f.write(b"\x00" * 150_000)

        session = MagicMock()
        result = engine._download_worker(1, session)
        assert result == "EXISTS"
        # 不应发起网络请求
        session.get.assert_not_called()

    def test_existing_small_file_redownloads(self, tmp_path):
        """小于阈值的文件应重新下载"""
        engine = _make_engine(tmp_path)
        target = os.path.join(str(tmp_path), "CLS-001.bin")
        with open(target, "wb") as f:
            f.write(b"\x00" * 100)  # 太小

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"new_data"
        session = MagicMock()
        session.get.return_value = mock_response

        result = engine._download_worker(1, session)
        assert result == "SUCCESS"
        session.get.assert_called_once()

    def test_404_returns_eof(self, tmp_path):
        """404 响应应返回 EOF"""
        engine = _make_engine(tmp_path)
        mock_response = MagicMock()
        mock_response.status_code = 404
        session = MagicMock()
        session.get.return_value = mock_response

        result = engine._download_worker(1, session)
        assert result == "EOF"

    def test_400_returns_eof(self, tmp_path):
        """400 响应应返回 EOF"""
        engine = _make_engine(tmp_path)
        mock_response = MagicMock()
        mock_response.status_code = 400
        session = MagicMock()
        session.get.return_value = mock_response

        result = engine._download_worker(1, session)
        assert result == "EOF"

    def test_200_writes_file_and_returns_success(self, tmp_path):
        """200 响应应写入文件并返回 SUCCESS"""
        engine = _make_engine(tmp_path)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"video_slice_data_here"
        session = MagicMock()
        session.get.return_value = mock_response

        result = engine._download_worker(5, session)
        assert result == "SUCCESS"

        # 验证文件已写入
        written = os.path.join(str(tmp_path), "CLS-005.bin")
        assert os.path.exists(written)
        with open(written, "rb") as f:
            assert f.read() == b"video_slice_data_here"

    def test_401_returns_auth_error(self, tmp_path):
        """401 响应应返回 AUTH_ERR"""
        engine = _make_engine(tmp_path)
        mock_response = MagicMock()
        mock_response.status_code = 401
        session = MagicMock()
        session.get.return_value = mock_response

        result = engine._download_worker(1, session)
        assert result == "AUTH_ERR_401"

    def test_403_returns_auth_error(self, tmp_path):
        """403 响应应返回 AUTH_ERR"""
        engine = _make_engine(tmp_path)
        mock_response = MagicMock()
        mock_response.status_code = 403
        session = MagicMock()
        session.get.return_value = mock_response

        result = engine._download_worker(1, session)
        assert result == "AUTH_ERR_403"

    def test_500_returns_server_error(self, tmp_path):
        """500 响应应返回 SERVER_ERR"""
        engine = _make_engine(tmp_path)
        mock_response = MagicMock()
        mock_response.status_code = 500
        session = MagicMock()
        session.get.return_value = mock_response

        result = engine._download_worker(1, session)
        assert result == "SERVER_ERR_500"

    def test_network_exception_returns_net_err(self, tmp_path):
        """网络异常应返回 NET_ERR 并截断错误信息"""
        engine = _make_engine(tmp_path)
        session = MagicMock()
        session.get.side_effect = ConnectionError("Connection refused by remote host server")

        result = engine._download_worker(1, session)
        assert result.startswith("NET_ERR_")
        # 错误信息应被截断到 30 字符以内
        err_msg = result.replace("NET_ERR_", "")
        assert len(err_msg) <= 30

    def test_ssl_exception_returns_ssl_err(self, tmp_path):
        """SSL证书异常应返回 SSL_ERR"""
        import requests
        engine = _make_engine(tmp_path)
        session = MagicMock()
        session.get.side_effect = requests.exceptions.SSLError("SSL verification failed")

        result = engine._download_worker(1, session)
        assert result == "SSL_ERR"

    def test_url_format_uses_index(self, tmp_path):
        """请求 URL 应正确格式化切片索引"""
        engine = _make_engine(tmp_path)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"
        session = MagicMock()
        session.get.return_value = mock_response

        engine._download_worker(42, session)

        call_args = session.get.call_args
        url = call_args[0][0]
        assert "CLS-042.jpg" in url


class TestDownloadEngineCallbacks:
    """回调函数触发测试"""

    def test_on_complete_called_on_eof(self, tmp_path):
        """检测到 EOF 时应触发 on_complete 回调"""
        completed = []
        engine = _make_engine(
            tmp_path,
            on_complete=lambda total: completed.append(total),
        )

        # Mock _create_session 返回的 session
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.content = b"x" * 16

        mock_response_eof = MagicMock()
        mock_response_eof.status_code = 404

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # 前 3 个请求成功，之后返回 EOF
            if call_count <= 3:
                return mock_response_ok
            return mock_response_eof

        mock_session = MagicMock()
        mock_session.get.side_effect = side_effect

        with patch.object(engine, '_create_session', return_value=mock_session):
            engine.run()

        # 3 个成功 + 第 4 个 EOF → actual_total = 3
        assert len(completed) == 1
        assert completed[0] == 3
        assert engine.total_known is True

    def test_on_log_called_for_each_slice(self, tmp_path):
        """每个成功切片应触发 on_log"""
        logs = []
        engine = _make_engine(
            tmp_path,
            on_log=lambda msg: logs.append(msg),
        )

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.content = b"data"

        mock_response_eof = MagicMock()
        mock_response_eof.status_code = 404

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return mock_response_ok
            return mock_response_eof

        mock_session = MagicMock()
        mock_session.get.side_effect = side_effect

        with patch.object(engine, '_create_session', return_value=mock_session):
            engine.run()

        # 应包含"成功固化"日志
        success_logs = [l for l in logs if "成功固化" in l]
        assert len(success_logs) == 2

    def test_cancel_stops_download(self, tmp_path):
        """调用 cancel() 应停止下载"""
        engine = _make_engine(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"data"

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # 下载 2 个后取消
            if call_count >= 2:
                engine.cancel()
            return mock_response

        mock_session = MagicMock()
        mock_session.get.side_effect = side_effect

        with patch.object(engine, '_create_session', return_value=mock_session):
            engine.run()

        # 下载应在取消后尽快停止（不会跑到 9999）
        assert call_count < 20
        assert engine.is_running is False
