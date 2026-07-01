"""Request URL 解析与验证（纯 Python，不依赖 Kivy）"""
import re
from urllib.parse import urlparse, parse_qs


class URLParseResult:
    """URL 解析结果数据类"""

    def __init__(self, base_url, params, video_id, server):
        self.base_url = base_url    # 带 {:03d} 占位符的模板 URL
        self.params = params        # 查询参数字典
        self.video_id = video_id    # 视频标识
        self.server = server        # 服务器域名


def validate_url(raw_url):
    """验证 Request URL 格式

    Returns:
        (is_valid, error_title, error_detail) 三元组
    """
    if not raw_url:
        return False, "缺少 Request URL", "请粘贴完整的 https 链接"

    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        return False, "链接格式不正确", "URL 必须以 http:// 或 https:// 开头"

    parsed = urlparse(raw_url)
    if not parsed.netloc or '.' not in parsed.netloc:
        return False, "缺少服务器域名", "请确认复制的是完整 Request URL"

    if not re.search(r'CLS-\d+\.jpg', raw_url):
        return False, "未识别到切片序列", "链接中需要包含 CLS-001.jpg 这类文件名"

    return True, "", ""


def parse_video_url(raw_url):
    """解析 Request URL，提取基础模板、参数、视频ID

    Returns:
        URLParseResult 对象

    Raises:
        ValueError: URL 格式无法解析时抛出
    """
    parsed_url = urlparse(raw_url)
    queries = parse_qs(parsed_url.query)
    params = {k: v[0] for k, v in queries.items()}

    path = parsed_url.path
    standard_path = re.sub(r'CLS-\d+\.jpg', 'CLS-{:03d}.jpg', path)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{standard_path}"

    video_id_match = re.search(r'/hls/([^/]+)/', path)
    video_id = video_id_match.group(1) if video_id_match else "default_video"

    return URLParseResult(
        base_url=base_url,
        params=params,
        video_id=video_id,
        server=parsed_url.netloc,
    )
