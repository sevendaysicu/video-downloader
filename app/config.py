"""视频下载器配置常量"""

# ── 下载引擎参数 ──────────────────────────────────────────
MAX_WORKERS = 4                 # 并发线程数
MAX_INDEX = 9999                # 切片索引上限（取消原 600 硬编码）
REQUEST_TIMEOUT = 10            # 单次请求超时（秒）
MAX_CONTINUOUS_ERRORS = 10      # 连续失败阈值，触发硬拉闸
MIN_VALID_SLICE_SIZE = 100_000  # 最小有效切片大小（字节），低于此视为无效
RETRY_TOTAL = 3                 # HTTP 重试次数
RETRY_BACKOFF = 0.2             # 重试退避因子
RETRY_STATUS_CODES = [500, 502, 503, 504]  # 触发自动重试的状态码
VERIFY_SSL = False              # 是否验证 SSL 证书（某些视频切片源证书配置不合规，默认关闭以防下载失败）


# ── UI 参数 ───────────────────────────────────────────────
LOG_MAX_LINES = 35              # 日志区域保留行数上限

# ── 颜色主题（深色高对比度移动端风格）───────────────────────
COLORS = {
    "background":   (0.059, 0.090, 0.165, 1),
    "surface":      (0.067, 0.094, 0.153, 1),
    "surface_alt":  (0.090, 0.125, 0.200, 1),
    "border":       (1, 1, 1, 0.08),
    "text":         (0.973, 0.980, 0.988, 1),
    "muted":        (0.580, 0.640, 0.720, 1),
    "primary":      (0.220, 0.741, 0.973, 1),
    "primary_dark": (0.031, 0.184, 0.286, 1),
    "success":      (0.133, 0.773, 0.369, 1),
    "warning":      (0.961, 0.620, 0.043, 1),
    "danger":       (0.937, 0.267, 0.267, 1),
}

# ── HTTP 默认请求头 ───────────────────────────────────────
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://rou.video/",
    "Connection": "keep-alive",
}
