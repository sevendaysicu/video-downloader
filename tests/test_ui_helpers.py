"""辅助函数单元测试（无 Kivy 依赖，直接测试纯函数）"""
from app.helpers import clamp_progress, estimate_progress, trim_log_lines


# ── clamp_progress 测试 ─────────────────────────────────────

def test_clamp_progress_caps_active_download_below_complete():
    assert clamp_progress(125, 100, complete=False) == 99


def test_clamp_progress_allows_complete_state_to_reach_100():
    assert clamp_progress(125, 100, complete=True) == 100


def test_clamp_progress_handles_empty_total():
    assert clamp_progress(5, 0, complete=False) == 0


# ── trim_log_lines 测试 ─────────────────────────────────────

def test_trim_log_lines_keeps_header_and_latest_entries():
    existing = "运行日志:\n" + "\n".join(f"line {i}" for i in range(40))
    trimmed = trim_log_lines(existing, "latest", max_lines=6)
    assert trimmed.splitlines() == [
        "运行日志:",
        "line 36",
        "line 37",
        "line 38",
        "line 39",
        "latest",
    ]


# ── estimate_progress 测试 ──────────────────────────────────

def test_estimate_progress_zero():
    assert estimate_progress(0) == 0


def test_estimate_progress_positive_within_cap():
    result = estimate_progress(50)
    assert 0 < result <= 90
