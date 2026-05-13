"""Tests for waits skill tools (wait_for, wait_for_idle, wait_for_window, poll_until)."""

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
    from skills.waits import register
    register(MCP())
    return tools


def _elem():
    e = MagicMock()
    e.exists.return_value = True
    e.is_visible.return_value = True
    e.is_enabled.return_value = True
    return e


@contextmanager
def _handle(win, key="h"):
    from core.handle_cache import HANDLES
    orig = HANDLES.get
    HANDLES.get = lambda h: win if h == key else None
    try:
        yield key
    finally:
        HANDLES.get = orig


# ── wait_for ──────────────────────────────────────────────────────────────────

def test_wait_for_stale_handle():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["wait_for"](h)
    assert result == {"error": "stale_handle"}


def test_wait_for_exists_immediately():
    tools = _reg()
    elem = _elem()
    with _handle(elem) as h, patch("time.sleep"):
        result = tools["wait_for"](h, state="exists", timeout=5.0)
    assert result == {"ok": True, "state": "exists"}


def test_wait_for_visible():
    tools = _reg()
    elem = _elem()
    with _handle(elem) as h, patch("time.sleep"):
        result = tools["wait_for"](h, state="visible", timeout=5.0)
    assert result == {"ok": True, "state": "visible"}


def test_wait_for_enabled():
    tools = _reg()
    elem = _elem()
    with _handle(elem) as h, patch("time.sleep"):
        result = tools["wait_for"](h, state="enabled", timeout=5.0)
    assert result == {"ok": True, "state": "enabled"}


def test_wait_for_ready():
    tools = _reg()
    elem = _elem()
    with _handle(elem) as h, patch("time.sleep"):
        result = tools["wait_for"](h, state="ready", timeout=5.0)
    assert result == {"ok": True, "state": "ready"}


def test_wait_for_timeout():
    """Element never becomes visible; should return timeout error."""
    tools = _reg()
    elem = _elem()
    elem.exists.return_value = False
    with _handle(elem) as h, patch("time.sleep"):
        result = tools["wait_for"](h, state="exists", timeout=0.0)
    assert result["error"] == "timeout"
    assert result["state"] == "exists"


# ── wait_for_idle ─────────────────────────────────────────────────────────────

def test_wait_for_idle_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["wait_for_idle"](h)
    assert result == {"error": "stale_handle"}


def test_wait_for_idle_ok():
    tools = _reg()
    win = MagicMock()
    with _handle(win) as h:
        result = tools["wait_for_idle"](h, timeout=5.0)
    assert result == {"ok": True}
    win.wait.assert_called_once_with("exists ready", timeout=5.0)


def test_wait_for_idle_exception():
    tools = _reg()
    win = MagicMock()
    win.wait.side_effect = Exception("timeout waiting")
    with _handle(win) as h:
        result = tools["wait_for_idle"](h, timeout=1.0)
    assert "error" in result
    assert result["timeout_seconds"] == 1.0


# ── wait_for_window ───────────────────────────────────────────────────────────

def test_wait_for_window_found():
    tools = _reg()
    win = MagicMock()
    win.window_text.return_value = "Notepad"
    win.class_name.return_value = "Notepad"
    win.handle = 9001
    from core.handle_cache import HANDLES
    orig_reg = HANDLES.register
    HANDLES.register = lambda w: "el_found"
    mock_pw = MagicMock()
    mock_pw.Desktop.return_value.windows.return_value = [win]
    try:
        with patch.dict(sys.modules, {"pywinauto": mock_pw}), patch("time.sleep"):
            result = tools["wait_for_window"](title_re="Notepad", timeout=5.0)
    finally:
        HANDLES.register = orig_reg
    assert result["handle"] == "el_found"
    assert result["title"] == "Notepad"


def test_wait_for_window_timeout():
    tools = _reg()
    mock_pw = MagicMock()
    mock_pw.Desktop.return_value.windows.return_value = []
    with patch.dict(sys.modules, {"pywinauto": mock_pw}), patch("time.sleep"):
        result = tools["wait_for_window"](title_re="DoesNotExist", timeout=0.0)
    assert result["error"] == "timeout"


# ── poll_until ────────────────────────────────────────────────────────────────

def test_poll_until_stale():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["poll_until"](h, "window_text", "Done")
    assert result == {"error": "stale_handle"}


def test_poll_until_matches_immediately():
    tools = _reg()
    elem = MagicMock()
    elem.window_text.return_value = "Done"
    with _handle(elem) as h, patch("time.sleep"):
        result = tools["poll_until"](h, "window_text", "Done", timeout=5.0)
    assert result["ok"] is True
    assert result["value"] == "Done"


def test_poll_until_timeout():
    tools = _reg()
    elem = MagicMock()
    elem.window_text.return_value = "Pending"
    with _handle(elem) as h, patch("time.sleep"):
        result = tools["poll_until"](h, "window_text", "Done", timeout=0.0)
    assert result["error"] == "timeout"
    assert result["expected"] == "Done"
