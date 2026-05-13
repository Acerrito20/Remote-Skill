"""Tests for discovery skill tools."""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _reg():
    tools = {}
    class MCP:
        def tool(self):
            def d(fn): tools[fn.__name__] = fn; return fn
            return d
    from skills.discovery import register
    register(MCP())
    return tools


def _win(hwnd=1001, title="Test Window", cls="Window"):
    w = MagicMock()
    w.handle = hwnd
    w.window_text.return_value = title
    w.class_name.return_value = cls
    w.is_visible.return_value = True
    w.is_enabled.return_value = True
    w.process_id.return_value = 1234
    w.element_info.control_type = "Window"
    w.element_info.automation_id = "root"
    w.element_info.class_name = cls
    return w


@contextmanager
def _handle(win, key="h"):
    from core.handle_cache import HANDLES
    orig = HANDLES.get
    HANDLES.get = lambda h: win if h == key else None
    try:
        yield key
    finally:
        HANDLES.get = orig


@contextmanager
def _register(return_value="el_abc"):
    from core.handle_cache import HANDLES
    orig = HANDLES.register
    HANDLES.register = lambda w: return_value
    try:
        yield
    finally:
        HANDLES.register = orig


# ── list_windows ──────────────────────────────────────────────────────────────

def test_list_windows_returns_window_info():
    tools = _reg()
    win = _win()
    mock_pw = MagicMock()
    mock_pw.Desktop.return_value.windows.return_value = [win]
    with _register("el_test"), patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["list_windows"]()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["handle"] == "el_test"
    assert result[0]["title"] == "Test Window"
    assert result[0]["hwnd"] == 1001


def test_list_windows_skips_failing_windows():
    """A window that raises during property access is silently skipped."""
    tools = _reg()
    bad_win = MagicMock()
    bad_win.window_text.side_effect = Exception("access denied")
    mock_pw = MagicMock()
    mock_pw.Desktop.return_value.windows.return_value = [bad_win]
    with _register("el_bad"), patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["list_windows"]()
    # The bad window was skipped; result may be empty or contain partial info
    assert isinstance(result, list)


# ── list_processes ────────────────────────────────────────────────────────────

def test_list_processes_no_filter():
    tools = _reg()
    mock_psutil = MagicMock()
    p1 = MagicMock(); p1.info = {"pid": 42, "name": "notepad.exe", "exe": r"C:\notepad.exe"}
    p2 = MagicMock(); p2.info = {"pid": 99, "name": "calc.exe", "exe": r"C:\calc.exe"}
    mock_psutil.process_iter.return_value = [p1, p2]
    with patch.dict(sys.modules, {"psutil": mock_psutil}):
        result = tools["list_processes"]()
    assert len(result) == 2
    assert result[0]["pid"] == 42


def test_list_processes_with_filter():
    tools = _reg()
    mock_psutil = MagicMock()
    p1 = MagicMock(); p1.info = {"pid": 1, "name": "notepad.exe", "exe": ""}
    p2 = MagicMock(); p2.info = {"pid": 2, "name": "calc.exe", "exe": ""}
    mock_psutil.process_iter.return_value = [p1, p2]
    with patch.dict(sys.modules, {"psutil": mock_psutil}):
        result = tools["list_processes"](name_filter="calc")
    assert len(result) == 1
    assert result[0]["name"] == "calc.exe"


def test_list_processes_psutil_missing():
    tools = _reg()
    # Remove psutil from sys.modules to simulate it not being installed
    saved = sys.modules.pop("psutil", None)
    try:
        result = tools["list_processes"]()
    finally:
        if saved is not None:
            sys.modules["psutil"] = saved
    assert len(result) == 1
    assert "error" in result[0]


# ── connect_app ───────────────────────────────────────────────────────────────

def test_connect_app_playwright_engine_returns_cdp_info():
    tools = _reg()
    mock_override = MagicMock()
    mock_override.engine = "playwright"
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = mock_override
    mock_cfg.cdp_url_for.return_value = "http://localhost:9222"
    with patch("skills.discovery.CFG", mock_cfg):
        result = tools["connect_app"](path="slack.exe")
    assert result["engine"] == "playwright"
    assert result["cdp_url"] == "http://localhost:9222"
    assert "browser_open" in result["note"]


def test_connect_app_uia_via_pid():
    tools = _reg()
    win = _win()
    mock_app = MagicMock()
    mock_app.connect.return_value = mock_app
    mock_app.top_window.return_value = win
    mock_pw = MagicMock()
    mock_pw.Application.return_value = mock_app
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = None
    mock_cfg.default_engine = "pywinauto"
    mock_cfg.timeouts.connect_seconds = 5
    with _register("el_notepad"), patch("skills.discovery.CFG", mock_cfg), \
         patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["connect_app"](pid=1234)
    assert result["handle"] == "el_notepad"
    assert result["engine"] == "pywinauto"


def test_connect_app_no_criteria_returns_error():
    tools = _reg()
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = None
    mock_cfg.default_engine = "pywinauto"
    mock_cfg.timeouts.connect_seconds = 5
    mock_pw = MagicMock()
    mock_pw.Application.return_value.connect.return_value = MagicMock()
    with patch("skills.discovery.CFG", mock_cfg), \
         patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["connect_app"]()
    assert "error" in result


# ── get_tree ──────────────────────────────────────────────────────────────────

def test_get_tree_stale_handle():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["get_tree"](h)
    assert result == {"error": "stale_handle"}


def test_get_tree_returns_node_structure():
    tools = _reg()
    win = _win()
    child = _win(hwnd=2002, title="Edit1")
    child.children.return_value = []
    win.children.return_value = [child]
    with _handle(win) as h:
        result = tools["get_tree"](h, max_depth=1)
    assert "control_type" in result
    assert "children" in result
    assert result["title"] == "Test Window"


# ── find_element ──────────────────────────────────────────────────────────────

def test_find_element_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["find_element"](h, auto_id="x")
    assert result == {"error": "stale_handle"}


def test_find_element_ok():
    tools = _reg()
    win = _win()
    child = _win(hwnd=2002, title="Submit")
    win.child_window.return_value = child
    with _handle(win) as h, _register("el_btn"):
        result = tools["find_element"](h, name="Submit")
    assert result["handle"] == "el_btn"
    assert result["title"] == "Submit"
    win.child_window.assert_called_once_with(title="Submit")


# ── inspect_element ───────────────────────────────────────────────────────────

def test_inspect_element_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["inspect_element"](h)
    assert result == {"error": "stale_handle"}


def test_inspect_element_returns_properties():
    tools = _reg()
    elem = _win()
    with _handle(elem) as h:
        result = tools["inspect_element"](h)
    assert result["title"] == "Test Window"
    assert "control_type" in result
    assert "enabled" in result


# ── find_by_path ──────────────────────────────────────────────────────────────

def test_find_by_path_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["find_by_path"](h, "Button[title='x']")
    assert result == {"error": "stale_handle"}


def test_find_by_path_ok():
    tools = _reg()
    win = _win()
    child = _win(hwnd=3003, title="OK")
    mock_selector = MagicMock()
    mock_selector.resolve.return_value = child
    mock_selector.SelectorError = Exception
    with _handle(win) as h, _register("el_ok"), \
         patch.dict(sys.modules, {"core.selector": mock_selector}):
        result = tools["find_by_path"](h, "Button[title='OK']")
    assert result["handle"] == "el_ok"
