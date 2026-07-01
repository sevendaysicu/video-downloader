"""纯辅助函数（无外部依赖，便于独立测试）"""
import math


def clamp_progress(current, total, complete=False):
    """计算进度百分比，支持已知/未知总数两种模式"""
    if complete:
        return 100
    if total <= 0:
        return 0
    percent = int((current / total) * 100)
    return max(0, min(percent, 99))


def estimate_progress(current, cap=90):
    """未知总数时，用对数曲线估算进度（上限 cap%），避免进度条长期不动"""
    if current <= 0:
        return 0
    # 对数增长：下载越多增速越缓，50个切片≈60%，200个≈80%，永远不超过cap
    progress = int(cap * (1 - 1 / (1 + math.log(1 + current * 0.15))))
    return max(0, min(progress, cap))


def trim_log_lines(existing_text, message, max_lines=35):
    """裁剪日志文本，保留首行标题和最新的 max_lines-1 行"""
    lines = existing_text.splitlines() if existing_text else ["运行日志:"]
    if not lines:
        lines = ["运行日志:"]
    if lines[0] != "运行日志:":
        lines.insert(0, "运行日志:")
    lines.append(str(message))
    if len(lines) > max_lines:
        lines = [lines[0]] + lines[-(max_lines - 1):]
    return "\n".join(lines)
