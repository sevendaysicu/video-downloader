"""辅助函数单元测试（无 Kivy 依赖，直接测试纯函数）"""
from app.helpers import (
    build_android_output_root,
    build_android_save_dir,
    clamp_progress,
    estimate_progress,
    get_loading_phase,
    should_log_download_progress,
    trim_log_lines,
)


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


# ── splash loading phase 测试 ───────────────────────────────

def test_get_loading_phase_returns_ordered_progress_and_message():
    progress, message = get_loading_phase(0)
    assert progress == 0.28
    assert "界面" in message


def test_get_loading_phase_clamps_to_last_phase():
    progress, message = get_loading_phase(99)
    assert progress == 1.0
    assert "就绪" in message


# ── Android 保存路径测试 ───────────────────────────────────

def test_build_android_save_dir_uses_video_downloader_root_folder():
    save_dir = build_android_save_dir("/storage/emulated/0", "abc123")
    assert save_dir == "/storage/emulated/0/VideoDownloader/slices_abc123"


def test_build_android_output_root_uses_video_downloader_folder():
    assert (
        build_android_output_root("/storage/emulated/0/")
        == "/storage/emulated/0/VideoDownloader"
    )


# ── 下载日志节流测试 ───────────────────────────────────────

def test_should_log_download_progress_keeps_early_and_milestone_logs():
    assert should_log_download_progress(1)
    assert should_log_download_progress(3)
    assert should_log_download_progress(10)
    assert should_log_download_progress(20)


def test_should_log_download_progress_skips_noisy_middle_logs():
    assert not should_log_download_progress(4)
    assert not should_log_download_progress(19)
