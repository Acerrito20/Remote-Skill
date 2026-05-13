"""Tests for dialogs skill tools and the background watcher helpers."""

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
    from skills.dialogs import register
    register(MCP())
    return tools


def _win(title="Test Dialog", cls="#32770", hwnd=1001):
    w = MagicMock()
    w.handle = hwnd
    w.window_text.return_value = title
    w.class_name.return_value = cls
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


# ── _match_window ─────────────────────────────────────────────────────────────

def test_match_window_title_re_match():
    from skills.dialogs import _match_window
    win = _win(title="Save Changes?")
    rule = {"match": {"title_re": "Save"}}
    assert _match_window(win, rule) is True


def test_match_window_title_re_no_match():
    from skills.dialogs import _match_window
    win = _win(title="About Notepad")
    rule = {"match": {"title_re": "Save"}}
    assert _match_window(win, rule) is False


def test_match_window_class_name_match():
    from skills.dialogs import _match_window
    win = _win(cls="#32770")
    rule = {"match": {"class_name": "#32770"}}
    assert _match_window(win, rule) is True


def test_match_window_class_name_no_match():
    from skills.dialogs import _match_window
    win = _win(cls="Notepad")
    rule = {"match": {"class_name": "#32770"}}
    assert _match_window(win, rule) is False


def test_match_window_no_criteria_matches_all():
    from skills.dialogs import _match_window
    win = _win()
    assert _match_window(win, {"match": {}}) is True


# ── _apply_rule ───────────────────────────────────────────────────────────────

def test_apply_rule_click_button():
    from skills.dialogs import _apply_rule
    win = _win()
    btn = MagicMock()
    win.child_window.return_value = btn
    _apply_rule(win, {"action": "click_button", "target": "OK"})
    win.child_window.assert_called_once_with(title="OK", control_type="Button")
    btn.invoke.assert_called_once()


def test_apply_rule_close():
    from skills.dialogs import _apply_rule
    win = _win()
    _apply_rule(win, {"action": "close", "target": ""})
    win.close.assert_called_once()


def test_apply_rule_exception_is_swallowed():
    from skills.dialogs import _apply_rule
    win = _win()
    win.close.side_effect = Exception("already closed")
    _apply_rule(win, {"action": "close", "target": ""})  # must not raise


# ── dismiss_dialog ────────────────────────────────────────────────────────────

def test_dismiss_dialog_found():
    tools = _reg()
    dialog = _win(title="Save Changes?")
    btn = MagicMock()
    dialog.child_window.return_value = btn
    mock_pw = MagicMock()
    mock_pw.Desktop.return_value.windows.return_value = [dialog]
    with patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["dismiss_dialog"](title_re="Save", button_title="OK")
    assert result["ok"] is True
    assert "Save Changes?" in result["dismissed"]
    btn.invoke.assert_called_once()


def test_dismiss_dialog_no_match():
    tools = _reg()
    dialog = _win(title="About Notepad")
    mock_pw = MagicMock()
    mock_pw.Desktop.return_value.windows.return_value = [dialog]
    with patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["dismiss_dialog"](title_re="Save", button_title="OK")
    assert result == {"error": "no_matching_dialog"}


# ── register_dialog_rule ──────────────────────────────────────────────────────

def test_register_dialog_rule_adds_to_rules():
    import skills.dialogs as d
    original_rules = d._RULES[:]
    d._RULES.clear()
    tools = _reg()
    with patch("skills.dialogs._ensure_watcher"):
        result = tools["register_dialog_rule"]("Save", "Discard")
    assert result["ok"] is True
    assert result["rules_registered"] == 1
    assert d._RULES[0]["match"]["title_re"] == "Save"
    assert d._RULES[0]["target"] == "Discard"
    # Restore original state
    d._RULES.clear()
    d._RULES.extend(original_rules)


def test_register_dialog_rule_starts_watcher():
    tools = _reg()
    with patch("skills.dialogs._ensure_watcher") as mock_ew:
        tools["register_dialog_rule"]("Error", "OK")
    mock_ew.assert_called_once()


# ── list_modal_dialogs ────────────────────────────────────────────────────────

def test_list_modal_dialogs_returns_dialog_class_windows():
    tools = _reg()
    d1 = _win(title="Save?", cls="#32770", hwnd=101)
    d2 = _win(title="Error", cls="Notepad", hwnd=102)
    mock_pw = MagicMock()
    mock_pw.Desktop.return_value.windows.return_value = [d1, d2]
    with _register("el_dlg"), patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["list_modal_dialogs"]()
    # Only d1 (cls="#32770") should appear
    assert len(result) == 1
    assert result[0]["title"] == "Save?"


# ── screenshot_window ─────────────────────────────────────────────────────────

def test_screenshot_window_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["screenshot_window"](h)
    assert result == {"error": "stale_handle"}


def test_screenshot_window_ok(tmp_path):
    tools = _reg()
    win = _win()
    mock_img = MagicMock()
    win.capture_as_image.return_value = mock_img
    out = str(tmp_path / "shot.png")
    with _handle(win) as h:
        result = tools["screenshot_window"](h, path=out)
    assert result["ok"] is True
    assert result["path"] == out
    mock_img.save.assert_called_once_with(out)
