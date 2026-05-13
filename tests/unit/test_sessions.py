"""Tests for sessions skill tools."""

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
    from skills.sessions import register
    register(MCP())
    return tools


# ── list_sessions ─────────────────────────────────────────────────────────────

_QUERY_SESSION_OUTPUT = """\
 SESSIONNAME       USERNAME             ID  STATE   TYPE        DEVICE
 services                                0  Disc
>console            operator             1  Active
 rdp-tcp#0          agent                2  Active  rdpwd
"""


def test_list_sessions_parses_output():
    tools = _reg()
    with patch("subprocess.check_output", return_value=_QUERY_SESSION_OUTPUT):
        result = tools["list_sessions"]()
    assert isinstance(result, list)
    # Three non-header lines → three sessions
    assert len(result) == 3


def test_list_sessions_returns_session_fields():
    tools = _reg()
    with patch("subprocess.check_output", return_value=_QUERY_SESSION_OUTPUT):
        result = tools["list_sessions"]()
    names = [s["name"] for s in result]
    # The leading ">" on console should be stripped
    assert "console" in names


def test_list_sessions_subprocess_error():
    tools = _reg()
    with patch("subprocess.check_output", side_effect=Exception("command not found")):
        result = tools["list_sessions"]()
    assert len(result) == 1
    assert "error" in result[0]


# ── get_session_info ──────────────────────────────────────────────────────────

def test_get_session_info_returns_resolution():
    tools = _reg()
    mock_user32 = MagicMock()
    mock_user32.GetSystemMetrics.side_effect = lambda n: 1920 if n == 0 else 1080
    with patch("ctypes.windll") as mock_windll:
        mock_windll.user32 = mock_user32
        result = tools["get_session_info"]()
    assert result["resolution"] == "1920x1080"


def test_get_session_info_error():
    tools = _reg()
    with patch("ctypes.windll") as mock_windll:
        mock_windll.user32.GetSystemMetrics.side_effect = OSError("no display")
        result = tools["get_session_info"]()
    assert "error" in result


# ── lock_session ──────────────────────────────────────────────────────────────

def test_lock_session_ok():
    tools = _reg()
    with patch("ctypes.windll") as mock_windll:
        mock_windll.user32.LockWorkStation.return_value = 1
        result = tools["lock_session"]()
    assert result == {"ok": True}
    mock_windll.user32.LockWorkStation.assert_called_once()


def test_lock_session_error():
    tools = _reg()
    with patch("ctypes.windll") as mock_windll:
        mock_windll.user32.LockWorkStation.side_effect = OSError("access denied")
        result = tools["lock_session"]()
    assert "error" in result


# ── attach_virtual_display ────────────────────────────────────────────────────

def test_attach_virtual_display_returns_guidance():
    tools = _reg()
    result = tools["attach_virtual_display"](width=2560, height=1440)
    assert "note" in result
    assert "2560" in result["note"]
    assert "1440" in result["note"]


def test_attach_virtual_display_default_resolution():
    tools = _reg()
    result = tools["attach_virtual_display"]()
    assert "1920" in result["note"]
    assert "1080" in result["note"]
