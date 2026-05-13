"""Tests for non-drag action tools (invoke, set_text, background_click, etc.)."""

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
    from skills.actions import register
    register(MCP())
    return tools


def _win(hwnd=1001):
    w = MagicMock()
    w.handle = hwnd
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


# ── invoke ────────────────────────────────────────────────────────────────────

def test_invoke_ok():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["invoke"](h)
    assert result == {"ok": True}
    win.invoke.assert_called_once()


def test_invoke_stale_handle():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["invoke"](h)
    assert result == {"error": "stale_handle"}


def test_invoke_exception_returns_dict():
    tools = _reg()
    win = _win()
    win.invoke.side_effect = RuntimeError("no invoke pattern")
    with _handle(win) as h:
        result = tools["invoke"](h)
    assert "error" in result
    assert result["type"] == "RuntimeError"


# ── set_text ──────────────────────────────────────────────────────────────────

def test_set_text_via_uia():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["set_text"](h, "hello")
    assert result == {"ok": True}
    win.set_edit_text.assert_called_once_with("hello")


def test_set_text_fallback_wm_settext():
    tools = _reg()
    win = _win()
    win.set_edit_text.side_effect = Exception("no value pattern")
    mock_win32gui = MagicMock()
    mock_win32con = MagicMock()
    mock_win32con.WM_SETTEXT = 0x000C
    with _handle(win) as h, patch.dict(sys.modules, {
        "win32gui": mock_win32gui, "win32con": mock_win32con,
    }):
        result = tools["set_text"](h, "fallback text")
    assert result["ok"] is True
    assert result["method"] == "WM_SETTEXT"


def test_set_text_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["set_text"](h, "x")
    assert result == {"error": "stale_handle"}


# ── get_text ──────────────────────────────────────────────────────────────────

def test_get_text_via_get_value():
    tools = _reg()
    win = _win()
    win.get_value.return_value = "the value"
    with _handle(win) as h:
        result = tools["get_text"](h)
    assert result == {"value": "the value"}


def test_get_text_falls_back_to_window_text():
    tools = _reg()
    win = _win()
    win.get_value.side_effect = Exception("no value")
    win.window_text.return_value = "window text"
    with _handle(win) as h:
        result = tools["get_text"](h)
    assert result == {"value": "window text"}


def test_get_text_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["get_text"](h)
    assert result == {"error": "stale_handle"}


# ── select_combo_item ─────────────────────────────────────────────────────────

def test_select_combo_item_ok():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["select_combo_item"](h, "Option A")
    assert result == {"ok": True}
    win.select.assert_called_once_with("Option A")


# ── toggle_checkbox / set_checkbox ────────────────────────────────────────────

def test_toggle_checkbox_ok():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["toggle_checkbox"](h)
    assert result == {"ok": True}
    win.toggle.assert_called_once()


def test_set_checkbox_already_checked_no_toggle():
    tools = _reg()
    win = _win()
    win.get_toggle_state.return_value = 1  # On
    with _handle(win) as h:
        result = tools["set_checkbox"](h, True)
    assert result == {"ok": True, "checked": True}
    win.toggle.assert_not_called()


def test_set_checkbox_needs_toggle():
    tools = _reg()
    win = _win()
    win.get_toggle_state.return_value = 0  # Off
    with _handle(win) as h:
        result = tools["set_checkbox"](h, True)
    assert result == {"ok": True, "checked": True}
    win.toggle.assert_called_once()


# ── tree node / scroll ────────────────────────────────────────────────────────

def test_expand_tree_node_ok():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["expand_tree_node"](h)
    assert result == {"ok": True}
    win.expand.assert_called_once()


def test_collapse_tree_node_ok():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["collapse_tree_node"](h)
    assert result == {"ok": True}
    win.collapse.assert_called_once()


def test_scroll_into_view_ok():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["scroll_into_view"](h)
    assert result == {"ok": True}
    win.scroll_into_view.assert_called_once()


# ── menu_select ───────────────────────────────────────────────────────────────

def test_menu_select_arrow_separator():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["menu_select"](h, "File→Save")
    assert result == {"ok": True}
    win.menu_select.assert_called_once_with("File", "Save")


def test_menu_select_gt_separator():
    tools = _reg()
    win = _win()
    with _handle(win) as h:
        result = tools["menu_select"](h, "Edit > Copy")
    assert result == {"ok": True}
    win.menu_select.assert_called_once_with("Edit", "Copy")


# ── background_click / background_type ───────────────────────────────────────

def test_background_click_posts_two_messages():
    tools = _reg()
    win = _win(hwnd=2002)
    mock_win32gui = MagicMock()
    mock_win32con = MagicMock()
    mock_win32con.WM_LBUTTONDOWN = 0x0201
    mock_win32con.WM_LBUTTONUP = 0x0202
    mock_win32con.MK_LBUTTON = 0x0001
    mock_win32api = MagicMock()
    mock_win32api.MAKELONG.return_value = 12345
    with _handle(win) as h, patch.dict(sys.modules, {
        "win32gui": mock_win32gui,
        "win32con": mock_win32con,
        "win32api": mock_win32api,
    }):
        result = tools["background_click"](h, 50, 75)
    assert result == {"ok": True}
    assert mock_win32gui.PostMessage.call_count == 2


def test_background_type_sends_one_message_per_char():
    tools = _reg()
    win = _win(hwnd=3003)
    mock_win32gui = MagicMock()
    mock_win32con = MagicMock()
    mock_win32con.WM_CHAR = 0x0102
    with _handle(win) as h, patch.dict(sys.modules, {
        "win32gui": mock_win32gui,
        "win32con": mock_win32con,
    }):
        result = tools["background_type"](h, "hi!")
    assert result == {"ok": True, "chars_sent": 3}
    assert mock_win32gui.PostMessage.call_count == 3


# ── send_raw_message ──────────────────────────────────────────────────────────

def test_send_raw_message_post_mode():
    tools = _reg()
    win = _win(hwnd=4004)
    mock_win32gui = MagicMock()
    with _handle(win) as h, patch.dict(sys.modules, {"win32gui": mock_win32gui}):
        result = tools["send_raw_message"](h, 0x000C, post=True)
    assert result["ok"] is True
    assert result["sent"] == "posted"
    mock_win32gui.PostMessage.assert_called_once()
    mock_win32gui.SendMessage.assert_not_called()


def test_send_raw_message_send_mode():
    tools = _reg()
    win = _win(hwnd=5005)
    mock_win32gui = MagicMock()
    mock_win32gui.SendMessage.return_value = 42
    with _handle(win) as h, patch.dict(sys.modules, {"win32gui": mock_win32gui}):
        result = tools["send_raw_message"](h, 0x000C, post=False)
    assert result["ok"] is True
    assert result["result"] == 42
    mock_win32gui.SendMessage.assert_called_once()
