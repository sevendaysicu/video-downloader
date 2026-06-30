# UI Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Kivy single-screen video downloader into a clearer mobile dashboard UI without changing the download protocol.

**Architecture:** Keep the app in `main.py`, following the current compact project structure. Add small UI helper widgets and pure helper functions for progress/log behavior, then connect the existing downloader flow to dashboard status updates.

**Tech Stack:** Python 3, Kivy, Buildozer Android packaging, `requests`.

---

## File Structure

- Modify `main.py`: UI layout, style helpers, status/progress hooks, cleaned visible text.
- Create `tests/test_ui_helpers.py`: pure Python tests for progress clamping, log line capping, and status model behavior.

## Task 1: Add Pure UI Helper Tests

**Files:**
- Create: `tests/test_ui_helpers.py`
- Modify: `main.py`

- [ ] **Step 1: Write the failing tests**

```python
from main import clamp_progress, trim_log_lines


def test_clamp_progress_caps_active_download_below_complete():
    assert clamp_progress(125, 100, complete=False) == 99


def test_clamp_progress_allows_complete_state_to_reach_100():
    assert clamp_progress(125, 100, complete=True) == 100


def test_clamp_progress_handles_empty_total():
    assert clamp_progress(5, 0, complete=False) == 0


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_helpers.py -q`

Expected: import failure for `clamp_progress` and `trim_log_lines`, because they do not exist yet.

- [ ] **Step 3: Add minimal helpers**

Add these top-level functions to `main.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_helpers.py -q`

Expected: 4 passed.

## Task 2: Build Dashboard UI Structure

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add Kivy imports and style tokens**

Add Kivy imports for `Widget`, `dp`, `Color`, `RoundedRectangle`, and `Rectangle`.

Define color constants on `VideoDownloaderAndroid` for background, surfaces, text, primary, success, warning, and danger.

- [ ] **Step 2: Replace `build()` body with dashboard composition**

Create helper methods:

```python
def build_header(self):
    ...

def build_progress_card(self):
    ...

def build_input_card(self):
    ...

def build_action_area(self):
    ...

def build_log_card(self):
    ...
```

The root layout stays vertical, but uses a dark background and a `ScrollView` containing the dashboard content.

- [ ] **Step 3: Add reusable card/background helpers**

Add methods:

```python
def apply_background(self, widget, color, radius=0):
    ...

def update_rect(self, instance, value):
    ...
```

Use Kivy canvas instructions to draw stable surface cards.

- [ ] **Step 4: Preserve existing event bindings**

Ensure `self.main_btn.bind(on_press=self.start_download_flow)`, `self.merge_btn.bind(on_press=self.merge_slices)`, and `self.open_dir_btn.bind(on_press=self.open_directory)` remain connected.

## Task 3: Connect Progress and State Feedback

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update status methods**

Replace `update_info()` with dashboard-aware updates:

```python
@mainthread
def set_status(self, state, message, detail=""):
    ...

@mainthread
def update_progress(self, current, total, complete=False):
    ...
```

- [ ] **Step 2: Use helpers in download flow**

Call:

```python
self.set_status("下载中", "正在分析 Request URL", "请保持应用在前台")
self.update_progress(0, self.estimated_total)
```

when starting.

Call `self.update_progress(idx, self.estimated_total)` for each processed slice.

Call `self.update_progress(self.estimated_total, self.estimated_total, complete=True)` and `self.set_status("完成", "切片下载完成", "可以合并视频")` when EOF confirms completion.

- [ ] **Step 3: Surface validation errors**

For empty input, invalid URL, missing host, missing `CLS-xxx.jpg`, parse exceptions, and repeated failures, call `self.set_status("错误", "...", "...")` with a concise recovery hint.

- [ ] **Step 4: Update button states**

When downloading starts:

```python
self.main_btn.disabled = True
self.main_btn.text = "下载中..."
```

When finished:

```python
self.main_btn.disabled = False
self.main_btn.text = "开始下载"
```

## Task 4: Verify

**Files:**
- Modify: `main.py`
- Test: `tests/test_ui_helpers.py`

- [ ] **Step 1: Run helper tests**

Run: `python -m pytest tests/test_ui_helpers.py -q`

Expected: all tests pass.

- [ ] **Step 2: Run syntax validation**

Run: `python -m py_compile main.py`

Expected: no output and exit code 0.

- [ ] **Step 3: Smoke-check imports**

Run: `python -c "import main; print(main.clamp_progress(1, 2))"`

Expected output: `50`.

- [ ] **Step 4: Manual UI checklist**

Check in code:

- Root background is dark.
- Header, progress, input, actions, and log are separated.
- Primary and secondary actions are at least 48dp high.
- Status pill can show ready, downloading, complete, and error states.
- Log is capped with `trim_log_lines`.

