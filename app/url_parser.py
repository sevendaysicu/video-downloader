"""Request URL 解析与验证（纯 Python，不依赖 Kivy）"""
import re
from urllib.parse import urlparse, parse_qs


class URLParseResult:
    """URL 解析结果数据类"""

    def __init__(self, base_url, params, video_id, server):
        self.base_url = base_url    # 带占位符的模板 URL
        self.params = params        # 查询参数字典
        self.video_id = video_id    # 视频标识
        self.server = server        # 服务器域名


# 支持的切片文件名模式列表（按优先级排列）
# 模式 1: CLS-001.jpg（纯数字序列号）
# 模式 2: CLS-6-v1-a1.jpg（编号-版本-音频轨复合格式）
_CLS_PATTERNS = [
    re.compile(r'CLS-\d+-v\d+-a\d+\.jpg'),   # 复合格式优先匹配
    re.compile(r'CLS-\d+\.jpg'),               # 纯数字格式
]


def _find_cls_pattern(text):
    """在文本中查找 CLS 切片文件名模式

    Returns:
        匹配到的 re.Match 对象，或 None
    """
    for pattern in _CLS_PATTERNS:
        match = pattern.search(text)
        if match:
            return match
    return None


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

    if not _find_cls_pattern(raw_url):
        return (
            False,
            "未识别到切片序列",
            "链接中需要包含 CLS-001.jpg 或 CLS-6-v1-a1.jpg 这类文件名",
        )

    return True, "", ""


def parse_video_url(raw_url):
    """解析 Request URL，提取基础模板、参数、视频ID

    支持两种切片 URL 格式：
    - CLS-001.jpg         → 模板: CLS-{:03d}.jpg
    - CLS-6-v1-a1.jpg     → 模板: CLS-{}-v1-a1.jpg

    Returns:
        URLParseResult 对象

    Raises:
        ValueError: URL 格式无法解析时抛出
    """
    parsed_url = urlparse(raw_url)
    queries = parse_qs(parsed_url.query)
    params = {k: v[0] for k, v in queries.items()}

    path = parsed_url.path

    # 根据匹配到的模式决定模板替换策略
    match = _find_cls_pattern(path)
    if match:
        matched_text = match.group()
        # 检测是否为复合格式（CLS-6-v1-a1.jpg）
        complex_match = re.match(
            r'CLS-(\d+)(-v\d+-a\d+)\.jpg', matched_text,
        )
        if complex_match:
            # 复合格式：保留版本和音频轨后缀，仅替换序号
            suffix = complex_match.group(2)
            standard_path = path.replace(
                matched_text, 'CLS-{}{}.jpg'.format('{}', suffix),
            )
        else:
            # 纯数字格式：替换为 {:03d} 占位符
            standard_path = re.sub(
                r'CLS-\d+\.jpg', 'CLS-{:03d}.jpg', path,
            )
    else:
        raise ValueError(
            f"无法在路径中识别 CLS 切片模式: {path}"
        )

    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{standard_path}"

    video_id_match = re.search(r'/hls/([^/]+)/', path)
    video_id = video_id_match.group(1) if video_id_match else "default_video"

    return URLParseResult(
        base_url=base_url,
        params=params,
        video_id=video_id,
        server=parsed_url.netloc,
    )
