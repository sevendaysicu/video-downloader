import sys
import types


class DummyApp:
    pass


class DummyWidget:
    def __init__(self, *args, **kwargs):
        pass

    def bind(self, *args, **kwargs):
        pass

    def add_widget(self, *args, **kwargs):
        pass


def install_kivy_stubs():
    modules = {
        "kivy": types.ModuleType("kivy"),
        "kivy.app": types.ModuleType("kivy.app"),
        "kivy.uix": types.ModuleType("kivy.uix"),
        "kivy.uix.boxlayout": types.ModuleType("kivy.uix.boxlayout"),
        "kivy.uix.label": types.ModuleType("kivy.uix.label"),
        "kivy.uix.textinput": types.ModuleType("kivy.uix.textinput"),
        "kivy.uix.button": types.ModuleType("kivy.uix.button"),
        "kivy.uix.scrollview": types.ModuleType("kivy.uix.scrollview"),
        "kivy.uix.widget": types.ModuleType("kivy.uix.widget"),
        "kivy.clock": types.ModuleType("kivy.clock"),
        "kivy.graphics": types.ModuleType("kivy.graphics"),
        "kivy.metrics": types.ModuleType("kivy.metrics"),
        "kivy.utils": types.ModuleType("kivy.utils"),
        "kivy.core": types.ModuleType("kivy.core"),
        "kivy.core.text": types.ModuleType("kivy.core.text"),
    }
    modules["kivy.app"].App = DummyApp
    modules["kivy.uix.boxlayout"].BoxLayout = DummyWidget
    modules["kivy.uix.label"].Label = DummyWidget
    modules["kivy.uix.textinput"].TextInput = DummyWidget
    modules["kivy.uix.button"].Button = DummyWidget
    modules["kivy.uix.scrollview"].ScrollView = DummyWidget
    modules["kivy.uix.widget"].Widget = DummyWidget
    modules["kivy.clock"].Clock = types.SimpleNamespace(schedule_once=lambda *args, **kwargs: None)
    modules["kivy.clock"].mainthread = lambda func: func
    modules["kivy.graphics"].Color = DummyWidget
    modules["kivy.graphics"].Rectangle = DummyWidget
    modules["kivy.graphics"].RoundedRectangle = DummyWidget
    modules["kivy.metrics"].dp = lambda value: value
    modules["kivy.utils"].platform = "linux"
    modules["kivy.core.text"].DEFAULT_FONT = "Roboto"
    modules["kivy.core.text"].LabelBase = types.SimpleNamespace(register=lambda *args, **kwargs: None)
    sys.modules.update(modules)


install_kivy_stubs()

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
