# 视频下载器 (Video Downloader)

基于 Kivy 的 Android 视频切片抓取与合并工具，支持桌面端开发调试。

本项目已通过模块化重构与性能深度优化，具备高并发、低内存占用、非阻塞UI等工业级特性。

## 功能

- **Request URL 解析** — 通过抓包工具获取视频请求 URL，直接粘贴包含 `CLS-xxx.jpg` 序列的完整 URL 即可自动推导解析出基础 API、鉴权参数及视频 ID。
- **高并发并发下载** — 采用 `ThreadPoolExecutor` (4线程滑动窗口) 并配合共享 `requests.Session` 连接池复用，免去频繁 TCP/TLS 握手。
- **取消与断点避重** — 支持中途一键“取消下载”；本地已存在的有效切片（默认为 >100KB）会自动跳过以节省带宽。
- **非阻塞流式合并** — 视频合并移至后台线程，并通过 **8KB 分块流式读写** 物理拼接为完整 `.mp4` 文件，彻底避免大文件合并时 UI 冻结与内存爆炸。
- **SSL 校验策略** — 提供配置化的 SSL 验证控制。针对非合规视频源默认免校验警告，同时对证书异常提供智能诊断日志。
- **精美中文界面** — 完整中文 UI，深色高对比度移动端风格，带有实时滚动日志卡片（上限 35 行）。

## 界面预览

单页工具仪表盘，从上到下依次为：

| 区域 | 内容 |
|------|------|
| Header | 应用标题、状态胶囊（就绪 / 下载中 / 完成 / 警告 / 错误） |
| 进度卡片 | 任务状态（实时下载进度或后台合并进度）、进度条、切片计数 |
| URL 输入 | 多行文本输入框，带示例提示和自动分析机制 |
| 操作区 | 开始下载（多态：开始/取消）、合并视频（后台流式）、文件位置（快捷打开） |
| 日志卡片 | 滚动日志，记录下载详情与异常提示，保持最新 35 行 |

## 快速开始

### 桌面端（开发 / 测试）

**环境要求**：Python 3.10+

```bash
# 安装依赖
pip install kivy requests urllib3

# 启动应用
python main.py
```

### 运行测试

本地使用 pytest 运行包含 37 个测试用例的测试套件（覆盖核心 URL 解析、下载引擎状态码逻辑、流式合并逻辑）：

```bash
pip install pytest
python -m pytest tests/ -v
```

### Android 打包

使用 Buildozer 构建 APK：

```bash
pip install buildozer cython
buildozer android debug
```

或通过 GitHub Actions 自动构建（推送代码后自动触发），产物可在 Actions → Artifacts 中下载。

## 项目结构

重构后的包组织结构如下：

```
├── main.py              # 精简应用主入口（仅负责启动 App 类）
├── font.ttf             # 中文字体（子集化，240 KB）
├── buildozer.spec       # Buildozer Android 打包配置（已排除测试与缓存文件）
├── app/                 # 核心模块化代码
│   ├── __init__.py      # 初始化脚本，暴露 ROOT_DIR 路径
│   ├── config.py        # 外部化配置参数（线程数、超时重试、UI 主题等）
│   ├── helpers.py       # 纯数学与文本辅助计算函数（进度映射、日志截断）
│   ├── url_parser.py    # URL 校验与字段特征参数提取（免 Kivy 依赖）
│   ├── downloader.py    # 并发下载引擎类（基于滑动窗口、Session连接池复用）
│   ├── merger.py        # 8KB分块流式合并器（非阻塞、带进度回调）
│   └── ui/
│       ├── __init__.py
│       └── app.py       # Kivy UI 构建组件、事件监听路由与线程分发
├── tests/               # 独立单元测试包
│   ├── test_ui_helpers.py  # 进度条估计、文本裁剪单元测试
│   ├── test_url_parser.py  # 静态 URL 解析与校验测试
│   ├── test_downloader.py  # Mock 下载引擎及各 HTTP 状态码处理测试
│   └── test_merger.py      # 流式合并文件物理拼接正确性测试
├── .github/workflows/
│   └── build.yml        # CI 脚本（包含 Pytest 预检与 Buildozer/Gradle 缓存机制）
└── docs/                # 设计文档与规格说明
```

## 技术栈

| 层级 | 技术 |
|------|------|
| UI 框架 | [Kivy](https://kivy.org/) 2.3 |
| 网络请求 | requests + urllib3（连接池复用、退避重试、SSL验证） |
| 打包工具 | [Buildozer](https://buildozer.readthedocs.io/) + python-for-android |
| CI/CD | GitHub Actions（Ubuntu 22.04 + Java 17 + gradle 缓存 + pytest 预检） |
| 测试 | pytest |

## Android 构建参数

- **目标 API**：33
- **最低支持**：Android 7.0 (API 24)
- **架构**：arm64-v8a, armeabi-v7a
- **权限**：INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE
- **p4a 分支**：release-2024.01.21（稳定版）

## 开发与配置说明

### 常量参数修改 (在 [app/config.py](file:///e:/codex-program/video-downloader-android/app/config.py) 中定义)
- `MAX_WORKERS = 4`: 修改并发线程数。
- `MAX_INDEX = 9999`: 流尾最大查找步数。
- `MIN_VALID_SLICE_SIZE = 100000`: 单切片去重过滤体积阈值。
- `VERIFY_SSL = False`: 是否在下载时执行严格 SSL 证书验证，若下载源不支持 HTTPS 校验可保持 False。

### 运行路径规则
- **桌面运行**：缓存保存在项目同级目录下名为 `slices_<video_id>/` 的文件夹中。
- **Android 运行**：统一缓存到手机内部存储的 `Download/slices_<video_id>/`，方便用户查阅。
- **合并 MP4**：输出于上述缓存目录 of 的父级（桌面为项目根目录，手机为 `Download/` 根目录）。
