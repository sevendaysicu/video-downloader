# 视频下载器 (Video Downloader)

基于 Kivy 的 Android 视频切片抓取与合并工具，支持桌面端开发调试。

## 功能

- **Request URL 解析** — 粘贴包含 `CLS-xxx.jpg` 切片序列和鉴权参数的完整 URL，自动识别服务器、视频 ID 和缓存目录
- **高频切片下载** — 多线程拉取 `.bin` 数据块，带重试机制和连接复用
- **进度可视化** — 进度条 + 百分比 + 切片计数，实时反馈下载状态
- **二进制合并** — 将全部切片物理拼接为完整 `.mp4` 文件
- **中文界面** — 完整中文 UI，深色高对比度移动端风格
- **日志系统** — 滚动日志区域（自动上限 35 行），清晰展示每一步状态

## 界面预览

单页工具仪表盘，从上到下依次为：

| 区域 | 内容 |
|------|------|
| Header | 应用标题、状态胶囊（就绪 / 下载中 / 完成 / 错误） |
| 进度卡片 | 任务状态、进度条、切片计数、目录信息 |
| URL 输入 | 多行文本输入框，带示例提示和辅助说明 |
| 操作区 | 开始下载（主按钮）、合并视频、文件位置 |
| 日志卡片 | 滚动日志，最新 35 行 |

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

```bash
pip install pytest
pytest tests/
```

### Android 打包

使用 Buildozer 构建 APK：

```bash
pip install buildozer
buildozer android debug
```

或通过 GitHub Actions 自动构建（推送代码后自动触发），产物可在 Actions → Artifacts 中下载。

## 项目结构

```
├── main.py              # 应用主入口，包含全部 UI 与下载逻辑
├── font.ttf             # 中文字体（子集化，240 KB）
├── buildozer.spec       # Buildozer Android 打包配置
├── tests/
│   └── test_ui_helpers.py  # UI 辅助函数单元测试
├── .github/workflows/
│   └── build.yml        # CI：自动构建 Android APK
└── docs/                # 设计文档与规格说明
```

## 技术栈

| 层级 | 技术 |
|------|------|
| UI 框架 | [Kivy](https://kivy.org/) 2.3 |
| 网络请求 | requests + urllib3（连接池、重试、SSL） |
| 打包工具 | [Buildozer](https://buildozer.readthedocs.io/) + python-for-android |
| CI/CD | GitHub Actions（Ubuntu 22.04 + Java 17） |
| 测试 | pytest |

## Android 构建参数

- **目标 API**：33
- **最低支持**：Android 7.0 (API 24)
- **架构**：arm64-v8a, armeabi-v7a
- **权限**：INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
- **p4a 分支**：release-2024.01.21（稳定版）

## 开发说明

- 桌面运行时，下载缓存保存在项目同级的 `slices_<video_id>/` 目录
- Android 运行时，保存在 `内部存储/Download/slices_<video_id>/`
- 合并后的 MP4 输出到缓存目录的父级（Download 目录）
- 每个切片文件需大于 100KB 才视为有效（跳过重复下载）
- 连续 10 次请求失败自动停止（网络波动容错）
