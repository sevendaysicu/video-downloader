"""URL 解析器单元测试"""
from app.url_parser import validate_url, parse_video_url


# ── validate_url 测试 ───────────────────────────────────────

def test_validate_url_empty():
    valid, title, _ = validate_url("")
    assert not valid
    assert "缺少" in title


def test_validate_url_missing_scheme():
    valid, title, _ = validate_url("example.com/hls/v/CLS-001.jpg")
    assert not valid
    assert "格式" in title


def test_validate_url_missing_domain():
    valid, _, _ = validate_url("https:///hls/v/CLS-001.jpg")
    assert not valid


def test_validate_url_missing_cls_pattern():
    valid, _, _ = validate_url("https://example.com/video.mp4")
    assert not valid


def test_validate_url_valid_simple():
    valid, title, detail = validate_url(
        "https://cdn.example.com/hls/abc/CLS-001.jpg?auth=123"
    )
    assert valid
    assert title == ""
    assert detail == ""


def test_validate_url_valid_complex():
    """复合格式 CLS-6-v1-a1.jpg 也应验证通过"""
    valid, title, detail = validate_url(
        "https://v.rn248.xyz/hls/clau307t/L6fyWOAj7wU/CLS-6-v1-a1.jpg?v=6&auth=abc"
    )
    assert valid
    assert title == ""


# ── parse_video_url 测试（纯数字格式） ──────────────────────

def test_parse_video_url_extracts_fields():
    url = "https://cdn.example.com/hls/abc123/CLS-001.jpg?v=6&auth=secret"
    result = parse_video_url(url)
    assert result.server == "cdn.example.com"
    assert result.video_id == "abc123"
    assert result.params["auth"] == "secret"
    assert result.params["v"] == "6"
    assert "{:03d}" in result.base_url


def test_parse_video_url_default_video_id():
    url = "https://cdn.example.com/path/CLS-005.jpg?k=v"
    result = parse_video_url(url)
    assert result.video_id == "default_video"


# ── parse_video_url 测试（复合格式） ────────────────────────

def test_parse_complex_url_extracts_fields():
    """复合格式应保留版本和音频轨后缀"""
    url = (
        "https://v.rn248.xyz/hls/clau307t2016413kfxy20bkli"
        "/L6fyWOAj7wU/CLS-6-v1-a1.jpg"
        "?v=6&exp=1783126800&auth=EsRUZL_H9-YNUOLJK7HP6NOhJmzFdh9GjtQuFjIMM1A"
    )
    result = parse_video_url(url)
    assert result.server == "v.rn248.xyz"
    assert result.video_id == "clau307t2016413kfxy20bkli"
    assert result.params["auth"] == "EsRUZL_H9-YNUOLJK7HP6NOhJmzFdh9GjtQuFjIMM1A"
    assert result.params["exp"] == "1783126800"
    # 模板中应保留 -v1-a1 后缀，只替换序号
    assert "-v1-a1.jpg" in result.base_url
    assert "{}" in result.base_url


def test_parse_complex_url_template_format():
    """复合格式模板 URL 应能通过 format() 生成正确的切片地址"""
    url = (
        "https://v.rn248.xyz/hls/vid/sub/CLS-6-v1-a1.jpg?v=6&auth=token"
    )
    result = parse_video_url(url)
    # 用序号 42 格式化，应生成 CLS-42-v1-a1.jpg
    formatted = result.base_url.format(42)
    assert "CLS-42-v1-a1.jpg" in formatted


def test_parse_simple_url_template_format():
    """纯数字格式模板 URL 应能生成零填充的切片地址"""
    url = "https://cdn.example.com/hls/vid/CLS-001.jpg?auth=x"
    result = parse_video_url(url)
    formatted = result.base_url.format(42)
    assert "CLS-042.jpg" in formatted
