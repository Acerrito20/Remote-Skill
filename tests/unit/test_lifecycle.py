"""Tests for lifecycle skill tools (start_app, kill_app, etc.)."""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, call, patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _reg():
    tools = {}
    class MCP:
        def tool(self):
            def d(fn): tools[fn.__name__] = fn; return fn
            return d
    from skills.lifecycle import register
    register(MCP())
    return tools


def _win(hwnd=1001, title="App"):
    w = MagicMock()
    w.handle = hwnd
    w.window_text.return_value = title
    w.is_visible.return_value = True
    return w


@contextmanager
def _register(return_value="el_abc"):
    from core.handle_cache import HANDLES
    orig = HANDLES.register
    HANDLES.register = lambda w: return_value
    try:
        yield
    finally:
        HANDLES.register = orig


# ── start_app ─────────────────────────────────────────────────────────────────

def test_start_app_basic():
    tools = _reg()
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = None
    mock_cfg.default_engine = "pywinauto"
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    with patch("skills.lifecycle.CFG", mock_cfg), \
         patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        result = tools["start_app"]("notepad.exe")
    assert result["pid"] == 9999
    assert result["executable"] == "notepad.exe"
    assert result["engine"] == "pywinauto"
    mock_popen.assert_called_once_with(["notepad.exe"])


def test_start_app_with_args():
    tools = _reg()
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = None
    mock_cfg.default_engine = "pywinauto"
    mock_proc = MagicMock()
    mock_proc.pid = 1111
    with patch("skills.lifecycle.CFG", mock_cfg), \
         patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        result = tools["start_app"]("app.exe", ["--flag", "value"])
    mock_popen.assert_called_once_with(["app.exe", "--flag", "value"])


def test_start_app_playwright_injects_cdp_port():
    tools = _reg()
    mock_override = MagicMock()
    mock_override.engine = "playwright"
    mock_override.cdp_port = 9222
    mock_override.effective_cdp_url.return_value = "http://localhost:9222"
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = mock_override
    mock_cfg.default_engine = "playwright"
    mock_proc = MagicMock()
    mock_proc.pid = 8888
    with patch("skills.lifecycle.CFG", mock_cfg), \
         patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        result = tools["start_app"]("slack.exe")
    assert result["pid"] == 8888
    assert result["cdp_url"] == "http://localhost:9222"
    cmd = mock_popen.call_args[0][0]
    assert "--remote-debugging-port=9222" in cmd


def test_start_app_playwright_no_duplicate_port_arg():
    """CDP port arg is not injected twice if already present."""
    tools = _reg()
    mock_override = MagicMock()
    mock_override.engine = "playwright"
    mock_override.cdp_port = 9222
    mock_override.effective_cdp_url.return_value = "http://localhost:9222"
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = mock_override
    mock_cfg.default_engine = "playwright"
    mock_proc = MagicMock()
    mock_proc.pid = 7777
    with patch("skills.lifecycle.CFG", mock_cfg), \
         patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        result = tools["start_app"]("slack.exe", ["--remote-debugging-port=9222"])
    cmd = mock_popen.call_args[0][0]
    assert cmd.count("--remote-debugging-port=9222") == 1


# ── kill_app ──────────────────────────────────────────────────────────────────

def test_kill_app_ok():
    tools = _reg()
    mock_psutil = MagicMock()
    mock_proc = MagicMock()
    mock_psutil.Process.return_value = mock_proc
    with patch.dict(sys.modules, {"psutil": mock_psutil}):
        result = tools["kill_app"](1234)
    assert result == {"ok": True, "pid": 1234}
    mock_proc.kill.assert_called_once()
    mock_proc.wait.assert_called_once_with(timeout=5)


def test_kill_app_process_not_found():
    tools = _reg()
    mock_psutil = MagicMock()
    mock_psutil.Process.side_effect = Exception("NoSuchProcess")
    with patch.dict(sys.modules, {"psutil": mock_psutil}):
        result = tools["kill_app"](9999)
    assert "error" in result


# ── restart_app ───────────────────────────────────────────────────────────────

def test_restart_app_kills_then_relaunches():
    tools = _reg()
    mock_psutil = MagicMock()
    mock_proc = MagicMock()
    mock_psutil.Process.return_value = mock_proc
    mock_cfg = MagicMock()
    mock_cfg.override_for.return_value = None
    mock_cfg.default_engine = "pywinauto"
    new_proc = MagicMock()
    new_proc.pid = 5555
    with patch.dict(sys.modules, {"psutil": mock_psutil}), \
         patch("skills.lifecycle.CFG", mock_cfg), \
         patch("subprocess.Popen", return_value=new_proc), \
         patch("time.sleep"):
        result = tools["restart_app"](1234, "app.exe")
    assert result["pid"] == 5555
    mock_proc.kill.assert_called_once()


def test_restart_app_aborts_on_kill_failure():
    tools = _reg()
    mock_psutil = MagicMock()
    mock_psutil.Process.side_effect = Exception("permission denied")
    with patch.dict(sys.modules, {"psutil": mock_psutil}), \
         patch("time.sleep"):
        result = tools["restart_app"](9999, "app.exe")
    assert "error" in result


# ── get_app_state ─────────────────────────────────────────────────────────────

def test_get_app_state_running():
    tools = _reg()
    mock_psutil = MagicMock()
    mock_proc = MagicMock()
    mock_proc.status.return_value = "running"
    mock_proc.name.return_value = "app.exe"
    mock_psutil.Process.return_value = mock_proc
    with patch.dict(sys.modules, {"psutil": mock_psutil}):
        result = tools["get_app_state"](1234)
    assert result["status"] == "running"
    assert result["name"] == "app.exe"


def test_get_app_state_not_found():
    tools = _reg()
    mock_psutil = MagicMock()
    mock_psutil.Process.side_effect = Exception("no such process")
    with patch.dict(sys.modules, {"psutil": mock_psutil}):
        result = tools["get_app_state"](9999)
    assert result["status"] == "not_found"
    assert "error" in result


# ── wait_for_app ──────────────────────────────────────────────────────────────

def test_wait_for_app_no_criteria():
    tools = _reg()
    mock_pw = MagicMock()
    with patch.dict(sys.modules, {"pywinauto": mock_pw}):
        result = tools["wait_for_app"](timeout=0.01)
    assert "error" in result


def test_wait_for_app_timeout():
    tools = _reg()
    mock_pw = MagicMock()
    mock_pw.Application.return_value.connect.side_effect = Exception("not found yet")
    with patch.dict(sys.modules, {"pywinauto": mock_pw}), patch("time.sleep"):
        result = tools["wait_for_app"](title_re="Notepad", timeout=0.0)
    assert result["error"] == "timeout"
