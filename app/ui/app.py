"""视频下载器主界面"""
import os
import threading

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.clock import Clock, mainthread
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.animation import Animation

# 全局中文字体注册
from kivy.core.text import LabelBase, DEFAULT_FONT
from app import ROOT_DIR
LabelBase.register(DEFAULT_FONT, os.path.join(ROOT_DIR, 'font.ttf'))

from app.config import COLORS, LOG_MAX_LINES
from app.helpers import clamp_progress, estimate_progress, trim_log_lines
from app.url_parser import validate_url, parse_video_url
from app.downloader import DownloadEngine
from app.merger import merge_slices


class VideoDownloaderAndroid(App):
    """视频切片下载与合并工具"""

    def build(self):
        self.title = "视频下载器"
        self.save_dir = ""
        self.is_downloading = False
        self.progress_percent = 0
        self.actual_total = 0
        self.total_known = False
        self._engine = None

        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ])

        # ── 1. 动态启动屏幕构建 (Splash Loader) ────────────────
        splash_screen = Screen(name='splash')
        splash_layout = BoxLayout(orientation='vertical', padding=dp(24))
        self._apply_background(splash_layout, COLORS["background"])

        # 顶部伸缩占位
        splash_layout.add_widget(Widget(size_hint_y=0.22))

        # 渐进式圆环 Logo 标志 (带圆角背景)
        logo_container = BoxLayout(
            orientation='vertical', size_hint=(None, None),
            width=dp(96), height=dp(96),
            pos_hint={'center_x': 0.5}
        )
        self._apply_background(logo_container, COLORS["primary"], radius=48)
        logo_label = Label(
            text="↓", font_size=dp(48), bold=True,
            color=COLORS["primary_dark"],
            halign="center", valign="middle"
        )
        logo_label.bind(size=logo_label.setter('text_size'))
        logo_container.add_widget(logo_label)
        splash_layout.add_widget(logo_container)

        splash_layout.add_widget(Widget(size_hint_y=0.04))

        # App 标题与定位语
        app_title = Label(
            text="视频下载器", font_size=dp(28), bold=True,
            color=COLORS["text"], size_hint_y=None, height=dp(36),
            halign="center"
        )
        app_title.bind(size=app_title.setter('text_size'))
        splash_layout.add_widget(app_title)

        app_subtitle = Label(
            text="并发拉取 · 物理合流 · 极速固化", font_size=dp(13),
            color=COLORS["muted"], size_hint_y=None, height=dp(22),
            halign="center"
        )
        app_subtitle.bind(size=app_subtitle.setter('text_size'))
        splash_layout.add_widget(app_subtitle)

        # 中段占位
        splash_layout.add_widget(Widget(size_hint_y=0.22))

        # 底端初始化状态描述
        self.splash_status = Label(
            text="正在初始化系统组件...", font_size=dp(12),
            color=COLORS["muted"], size_hint_y=None, height=dp(20),
            halign="center"
        )
        self.splash_status.bind(size=self.splash_status.setter('text_size'))
        splash_layout.add_widget(self.splash_status)

        # 底部留白占位
        splash_layout.add_widget(Widget(size_hint_y=0.12))
        splash_screen.add_widget(splash_layout)

        # ── 2. 主控制界面构建 (Main Dashboard) ────────────────
        main_screen = Screen(name='main')
        main_layout = BoxLayout(orientation='vertical')
        self._apply_background(main_layout, COLORS["background"])

        scroll = ScrollView()
        content = BoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(18), dp(16), dp(18)],
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter('height'))

        content.add_widget(self._build_header())
        content.add_widget(self._build_progress_card())
        content.add_widget(self._build_input_card())
        content.add_widget(self._build_action_area())
        content.add_widget(self._build_log_card())

        scroll.add_widget(content)
        main_layout.add_widget(scroll)
        main_screen.add_widget(main_layout)

        # ── 3. 屏幕管理器及过渡控制 (ScreenManager) ────────────
        self.screen_manager = ScreenManager(transition=FadeTransition(duration=0.4))
        self.screen_manager.add_widget(splash_screen)
        self.screen_manager.add_widget(main_screen)

        self._set_status("就绪", "等待下载任务", "粘贴 Request URL 后开始下载")
        self._update_progress(0, 0)

        # 启动呼吸灯动画
        self.logo_anim = Animation(opacity=0.3, duration=0.8) + Animation(opacity=1.0, duration=0.8)
        self.logo_anim.repeat = True
        self.logo_anim.start(logo_container)

        # 触发延迟任务完成加载态转换
        Clock.schedule_once(lambda dt: self._update_splash_status("正在校验安全沙箱环境..."), 0.5)
        Clock.schedule_once(lambda dt: self._update_splash_status("正在就绪本地缓存目录..."), 1.0)
        Clock.schedule_once(lambda dt: self._update_splash_status("核心引擎就绪"), 1.5)
        Clock.schedule_once(self._switch_to_main, 1.8)

        return self.screen_manager

    def _update_splash_status(self, text):
        """更新启动加载过程中的指示语"""
        if hasattr(self, 'splash_status'):
            self.splash_status.text = text

    def _switch_to_main(self, dt):
        """切换至主控制台，释放动画算力"""
        if hasattr(self, 'logo_anim'):
            self.logo_anim.stop_all()
        if hasattr(self, 'screen_manager'):
            self.screen_manager.current = 'main'

    # ── UI 组件构建 ──────────────────────────────────────────

    def _build_header(self):
        header = BoxLayout(
            orientation='horizontal', size_hint_y=None,
            height=dp(64), spacing=dp(12),
        )

        title_box = BoxLayout(orientation='vertical', spacing=dp(2))
        title_box.add_widget(Label(
            text="视频下载器", color=COLORS["text"],
            font_size=dp(22), bold=True,
            halign="left", valign="bottom",
        ))
        title_box.add_widget(Label(
            text="切片抓取与合并工具", color=COLORS["muted"],
            font_size=dp(13), halign="left", valign="top",
        ))
        for child in title_box.children:
            child.bind(size=child.setter('text_size'))
        header.add_widget(title_box)

        self.status_pill = Label(
            text="就绪", color=COLORS["text"],
            size_hint=(None, None), width=dp(78), height=dp(36),
            font_size=dp(13), bold=True,
        )
        self._apply_background(self.status_pill, COLORS["surface_alt"], radius=18)
        header.add_widget(self.status_pill)
        return header

    def _build_progress_card(self):
        card = self._create_card(height=dp(132))
        card.add_widget(Label(
            text="任务状态", color=COLORS["muted"],
            size_hint_y=None, height=dp(22),
            font_size=dp(12), bold=True, halign="left",
        ))

        self.status_title = Label(
            text="等待下载任务", color=COLORS["text"],
            size_hint_y=None, height=dp(30),
            font_size=dp(18), bold=True, halign="left",
        )
        self.status_title.bind(size=self.status_title.setter('text_size'))
        card.add_widget(self.status_title)

        self.progress_bar = Widget(size_hint_y=None, height=dp(10))
        self.progress_bar.bind(
            pos=self._update_progress_graphics,
            size=self._update_progress_graphics,
        )
        with self.progress_bar.canvas:
            Color(*COLORS["surface_alt"])
            self.progress_track_rect = RoundedRectangle(
                pos=self.progress_bar.pos, size=self.progress_bar.size,
                radius=[dp(5)],
            )
            Color(*COLORS["primary"])
            self.progress_fill_rect = RoundedRectangle(
                pos=self.progress_bar.pos, size=(0, dp(10)),
                radius=[dp(5)],
            )
        card.add_widget(self.progress_bar)

        self.progress_detail = Label(
            text="0% · 等待开始", color=COLORS["muted"],
            size_hint_y=None, height=dp(24),
            font_size=dp(13), halign="left",
        )
        self.progress_detail.bind(size=self.progress_detail.setter('text_size'))
        card.add_widget(self.progress_detail)

        self.status_detail = Label(
            text="粘贴 Request URL 后开始下载", color=COLORS["muted"],
            size_hint_y=None, height=dp(30),
            font_size=dp(12), halign="left", valign="top",
        )
        self.status_detail.bind(size=self.status_detail.setter('text_size'))
        card.add_widget(self.status_detail)
        return card

    def _build_input_card(self):
        card = self._create_card(height=dp(220))
        card.add_widget(Label(
            text="Request URL", color=COLORS["text"],
            size_hint_y=None, height=dp(28),
            font_size=dp(16), bold=True, halign="left",
        ))
        self.url_input = TextInput(
            multiline=True,
            hint_text="示例: https://example.com/hls/video/CLS-001.jpg?v=6&auth=...",
            size_hint_y=None, height=dp(130),
            background_color=(1, 1, 1, 0.06),
            foreground_color=COLORS["text"],
            hint_text_color=(0.580, 0.640, 0.720, 0.85),
            cursor_color=COLORS["primary"],
            padding=[dp(12), dp(12), dp(12), dp(12)],
            font_size=dp(14),
        )
        card.add_widget(self.url_input)

        helper = Label(
            text="需要包含 CLS-001.jpg 这类切片序列和完整鉴权参数。",
            color=COLORS["muted"], size_hint_y=None, height=dp(28),
            font_size=dp(12), halign="left",
        )
        helper.bind(size=helper.setter('text_size'))
        card.add_widget(helper)
        return card

    def _build_action_area(self):
        actions = BoxLayout(
            orientation='vertical', spacing=dp(10),
            size_hint_y=None, height=dp(112),
        )

        self.main_btn = Button(
            text="开始下载", size_hint_y=None, height=dp(52),
            color=COLORS["primary_dark"],
            background_normal="", background_down="",
            background_color=COLORS["primary"],
            bold=True, font_size=dp(16),
        )
        self.main_btn.bind(on_press=self._on_start_download)
        actions.add_widget(self.main_btn)

        secondary = BoxLayout(
            orientation='horizontal', spacing=dp(10),
            size_hint_y=None, height=dp(50),
        )
        self.merge_btn = Button(
            text="合并视频", color=COLORS["text"],
            background_normal="", background_down="",
            background_color=COLORS["surface_alt"],
            font_size=dp(14),
        )
        self.merge_btn.bind(on_press=self._on_merge)
        secondary.add_widget(self.merge_btn)

        self.open_dir_btn = Button(
            text="文件位置", color=COLORS["text"],
            background_normal="", background_down="",
            background_color=COLORS["surface_alt"],
            font_size=dp(14),
        )
        self.open_dir_btn.bind(on_press=self._on_open_directory)
        secondary.add_widget(self.open_dir_btn)
        actions.add_widget(secondary)
        return actions

    def _build_log_card(self):
        card = self._create_card(height=dp(260))
        card.add_widget(Label(
            text="运行日志", color=COLORS["text"],
            size_hint_y=None, height=dp(28),
            font_size=dp(16), bold=True, halign="left",
        ))
        scroll = ScrollView(size_hint_y=None, height=dp(196))
        self.log_label = Label(
            text="运行日志:", size_hint_y=None,
            color=COLORS["muted"], font_size=dp(12),
            halign="left", valign="top",
        )
        self.log_label.bind(size=self.log_label.setter('text_size'))
        self.log_label.bind(
            texture_size=lambda inst, val: setattr(inst, 'height', val[1]),
        )
        scroll.add_widget(self.log_label)
        card.add_widget(scroll)
        return card

    # ── UI 工具方法 ──────────────────────────────────────────

    def _create_card(self, height):
        """创建标准卡片容器"""
        card = BoxLayout(
            orientation='vertical',
            padding=[dp(14), dp(12), dp(14), dp(12)],
            spacing=dp(8), size_hint_y=None, height=height,
        )
        self._apply_background(card, COLORS["surface"], radius=12)
        return card

    def _apply_background(self, widget, color, radius=0):
        """为 Widget 添加圆角或纯色背景"""
        with widget.canvas.before:
            widget._bg_color = Color(*color)
            if radius:
                widget._bg_rect = RoundedRectangle(
                    pos=widget.pos, size=widget.size, radius=[dp(radius)],
                )
            else:
                widget._bg_rect = Rectangle(pos=widget.pos, size=widget.size)
        widget.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        if hasattr(instance, "_bg_rect"):
            instance._bg_rect.pos = instance.pos
            instance._bg_rect.size = instance.size

    def _update_progress_graphics(self, instance, value):
        if not hasattr(self, "progress_track_rect"):
            return
        self.progress_track_rect.pos = instance.pos
        self.progress_track_rect.size = instance.size
        self.progress_fill_rect.pos = instance.pos
        fill_width = instance.width * (self.progress_percent / 100)
        self.progress_fill_rect.size = (fill_width, instance.height)

    # ── 状态更新（线程安全） ────────────────────────────────

    @mainthread
    def _log(self, message):
        """追加日志（自动保持 LOG_MAX_LINES 行上限）"""
        self.log_label.text = trim_log_lines(
            self.log_label.text, message, LOG_MAX_LINES,
        )

    @mainthread
    def _set_status(self, state, message, detail=""):
        """更新状态胶囊与描述"""
        state_colors = {
            "就绪": COLORS["surface_alt"],
            "下载中": COLORS["primary"],
            "完成": COLORS["success"],
            "警告": COLORS["warning"],
            "错误": COLORS["danger"],
        }
        self.status_pill.text = state
        self.status_pill.color = (
            COLORS["primary_dark"]
            if state in ("下载中", "完成", "警告")
            else COLORS["text"]
        )
        if hasattr(self.status_pill, "_bg_color"):
            self.status_pill._bg_color.rgba = state_colors.get(
                state, COLORS["surface_alt"],
            )
        self.status_title.text = str(message)
        self.status_detail.text = str(detail)

    @mainthread
    def _update_progress(self, current, total, complete=False):
        """更新进度条和百分比文字"""
        if complete:
            self.progress_percent = 100
            self.progress_detail.text = f"100% · {current} / {current} 切片"
        elif total > 0:
            self.progress_percent = clamp_progress(current, total)
            self.progress_detail.text = (
                f"{self.progress_percent}% · {current} / {total} 切片"
            )
        else:
            self.progress_percent = estimate_progress(current)
            self.progress_detail.text = (
                f"{self.progress_percent}% · 已下载 {current} 个切片"
            )
        if hasattr(self, "progress_bar"):
            self._update_progress_graphics(self.progress_bar, None)

    @mainthread
    def _set_downloading_ui(self, active):
        """切换下载按钮为 开始/取消 双态"""
        if active:
            self.main_btn.text = "取消下载"
            self.main_btn.background_color = COLORS["danger"]
            self.main_btn.color = COLORS["text"]
        else:
            self.main_btn.text = "开始下载"
            self.main_btn.background_color = COLORS["primary"]
            self.main_btn.color = COLORS["primary_dark"]
        self.main_btn.disabled = False

    # ── 事件处理（委托给业务模块） ────────────────────────────

    def _on_start_download(self, instance):
        """开始/取消下载按钮回调"""
        # 如果正在下载，执行取消
        if self.is_downloading:
            if self._engine:
                self._engine.cancel()
            self._log("[*] 用户请求取消下载...")
            self._set_status("警告", "正在取消下载", "等待当前请求完成后停止")
            return

        raw_url = self.url_input.text.strip()

        # 验证 URL
        is_valid, err_title, err_detail = validate_url(raw_url)
        if not is_valid:
            self._log(f"[错误] {err_detail}")
            self._set_status("错误", err_title, err_detail)
            return

        self._log("\n" + "=" * 30)
        self._log("[*] 正在分析 Request URL 特征...")
        self._set_status("下载中", "正在分析 Request URL", "请保持应用在前台")
        self.actual_total = 0
        self.total_known = False
        self._update_progress(0, 0)

        # 解析 URL
        try:
            result = parse_video_url(raw_url)
        except Exception as e:
            self._set_status("错误", "解析 Request URL 失败", str(e))
            self._log(f"[错误] 静态解析失败: {str(e)}")
            return

        # 计算保存目录
        if platform == 'android':
            from android.storage import primary_external_storage_path
            downloads = os.path.join(
                primary_external_storage_path(), "Download",
            )
            self.save_dir = os.path.join(
                downloads, f"slices_{result.video_id}",
            )
        else:
            self.save_dir = os.path.join(
                ROOT_DIR, f"slices_{result.video_id}",
            )

        os.makedirs(self.save_dir, exist_ok=True)

        self._set_status(
            "下载中", "下载环境已就绪",
            f"服务器: {result.server}\n缓存目录: {self.save_dir}",
        )
        self._log("[+] 目标链识别成功，准备进入高频拉取阶段...")

        # 创建并启动下载引擎
        self._engine = DownloadEngine(
            base_url=result.base_url,
            params=result.params,
            save_dir=self.save_dir,
            on_progress=self._update_progress,
            on_log=self._log,
            on_status=self._set_status,
            on_complete=self._on_download_complete,
        )

        self.is_downloading = True
        self._set_downloading_ui(True)
        threading.Thread(target=self._run_download, daemon=True).start()

    def _run_download(self):
        """下载线程入口"""
        try:
            self._engine.run()
        finally:
            self.is_downloading = False
            Clock.schedule_once(lambda dt: self._set_downloading_ui(False))

    @mainthread
    def _on_download_complete(self, total):
        """下载完成回调"""
        self.actual_total = total
        self.total_known = True
        self._update_progress(total, total, complete=True)
        self._set_status("完成", "切片下载完成", "可以点击合并视频")
        self._log(f"\n[完成] 共 {total} 个切片，全部下载完成 (100%)")
        self._log("[完成] 成功捕获流尾部信号，切片拉取完毕。")

    def _on_merge(self, instance):
        """合并按钮回调（后台线程执行，避免 UI 冻结）"""
        if not self.save_dir or not os.path.exists(self.save_dir):
            self._log("[错误] 下载路径为空或不存在。")
            self._set_status("错误", "没有可合并的目录", "请先完成切片下载")
            return

        bin_files = [
            f for f in os.listdir(self.save_dir) if f.endswith(".bin")
        ]
        if not bin_files:
            self._log("[错误] 未侦测到可拼装的数据块。")
            self._set_status("错误", "未找到切片文件", "请先下载或确认保存目录")
            return

        self._log(
            f"[*] 正在将这 {len(bin_files)} 个数据流进行物理二进制拼接..."
        )
        self._set_status("下载中", "正在合并视频", f"共 {len(bin_files)} 个切片")
        self.merge_btn.disabled = True

        threading.Thread(target=self._run_merge, daemon=True).start()

    def _run_merge(self):
        """后台线程执行合并（流式读写，不阻塞 UI）"""
        try:
            output_path, count = merge_slices(
                self.save_dir,
                on_progress=self._on_merge_progress,
            )
            self._set_status("完成", "视频合并完成", output_path)
            self._log(
                f"\n[完成] 物理合流成功，MP4 已归档至 Download 目录:"
                f"\n{output_path}"
            )
        except Exception as e:
            self._set_status("错误", "合并失败", str(e))
            self._log(f"[合并失败] {str(e)}")
        finally:
            Clock.schedule_once(lambda dt: self._set_merge_btn_enabled())

    @mainthread
    def _on_merge_progress(self, current, total):
        """合并进度回调"""
        self._set_status(
            "下载中", "正在合并视频",
            f"进度: {current}/{total} 个切片",
        )

    @mainthread
    def _set_merge_btn_enabled(self):
        """恢复合并按钮可点击状态"""
        self.merge_btn.disabled = False

    def _on_open_directory(self, instance):
        """文件位置按钮回调"""
        if platform == 'android':
            self._log(
                "\n[提示] 视频文件和缓存均保存在手机系统的"
                "【文件管理】 -> 【内部存储】 -> 【Download】 中。"
            )
        else:
            if self.save_dir and os.path.exists(self.save_dir):
                os.startfile(self.save_dir)
