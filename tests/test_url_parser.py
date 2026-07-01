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


def test_validate_url_valid():
    valid, title, detail = validate_url(
        "https://cdn.example.com/hls/abc/CLS-001.jpg?auth=123"
    )
    assert valid
    assert title == ""
    assert detail == ""


# ── parse_video_url 测试 ────────────────────────────────────

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
