# Video Downloader UI Dashboard Redesign

Date: 2026-06-30

## Goal

Improve the Android-facing Kivy UI from a plain script-style form into a focused mobile utility dashboard. The app should remain a single-screen downloader, but the screen should clearly show what the user should do, what the app is doing, and what the next action is.

## Current Context

The project is a compact Kivy Android app in `main.py`, packaged with Buildozer. The existing UI has four functional areas:

- A multiline Request URL input.
- A status label.
- Three action buttons: download, merge, open directory.
- A scrolling log.

Current problems:

- Chinese text in `main.py` appears corrupted, hurting readability and maintainability.
- The layout is visually flat; input, status, actions, progress, and logs have similar weight.
- Download progress is only shown through log text.
- Touch controls are usable but visually cramped and lack a consistent mobile style.
- Errors and completion states are buried in the log instead of being surfaced.

## Selected Direction

Use option B, the tool dashboard.

The optimized screen will use a dark, high-contrast mobile utility style:

- Top title and compact state pill.
- Progress/status card near the top.
- Request URL input card.
- One clear primary action for downloading.
- Secondary actions for merge and file location.
- Log area with better spacing and bounded history.

## Design System

Visual direction:

- Dark background: `#0f172a`.
- Surface panels: `#111827` and `#172033`.
- Primary action: blue/cyan.
- Completion/success: green.
- Warning/error: amber/red.
- Text hierarchy: high-contrast white primary text, slate secondary text.

Interaction rules:

- Tap targets should be at least 48dp high.
- Buttons should have clear disabled and active states.
- Downloading should visibly change the primary button and status pill.
- The progress card should show percentage plus current/estimated slice count.
- Logs remain available, but they should support the status card rather than being the only feedback.

## UI Structure

Single vertical scroll-safe screen:

1. Header
   - App name: `视频下载器`
   - Subtitle: `切片抓取与合并工具`
   - Status pill: `就绪`, `下载中`, `完成`, or `错误`

2. Progress card
   - Main status text.
   - Progress bar.
   - Progress detail such as `68 / 100 切片`.
   - Save directory or server summary when available.

3. URL input card
   - Visible label.
   - Multiline input with concise placeholder.
   - Helper text that explains the required `CLS-001.jpg` style URL.

4. Action area
   - Primary button: start download.
   - Secondary buttons: merge video, file location.
   - Disabled state during active download.

5. Log card
   - Latest log lines, capped to avoid runaway rendering.
   - Monospace-style layout if practical in Kivy.

## Behavioral Scope

Keep the downloader logic intact unless small UI state hooks are needed.

Allowed changes:

- Refactor `build()` UI construction into small helper methods.
- Add progress tracking fields and update methods.
- Replace corrupted visible Chinese strings with clean UTF-8 Chinese text.
- Improve log/status messages for common states.
- Add Kivy canvas-backed card backgrounds and progress bar widgets.

Out of scope:

- Migrating from Kivy to native Android or Jetpack Compose.
- Reworking network/download logic.
- Adding history, pause/resume, or background service behavior.
- Changing Buildozer packaging beyond metadata if needed for UI text.

## Verification

Before delivery:

- Run Python syntax validation on `main.py`.
- Smoke-test that the Kivy app can instantiate the UI if local dependencies allow it.
- Check small-phone layout assumptions: vertical flow, no fixed horizontal overflow, touch targets at least 48dp high.
- Confirm main states are represented: empty input, invalid URL, downloading, completed, merge success/failure.

