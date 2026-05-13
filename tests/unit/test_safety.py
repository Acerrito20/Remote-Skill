"""Tests for safety skill tools."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _reg():
    tools = {}
    class MCP:
        def tool(self):
            def d(fn): tools[fn.__name__] = fn; return fn
            return d
    from skills.safety import register
    register(MCP())
    return tools


@contextmanager
def _handle(win, key="h"):
    from core.handle_cache import HANDLES
    orig = HANDLES.get
    HANDLES.get = lambda h: win if h == key else None
    try:
        yield key
    finally:
        HANDLES.get = orig


# ── assert_background_safe ────────────────────────────────────────────────────

def test_assert_background_safe_allowed_action():
    tools = _reg()
    result = tools["assert_background_safe"]("invoke")
    assert result == {"ok": True, "action": "invoke"}


def test_assert_background_safe_banned_action():
    tools = _reg()
    result = tools["assert_background_safe"]("click_input")
    assert result["error"] == "not_background_safe"
    assert result["action"] == "click_input"
    assert "reason" in result


def test_assert_background_safe_all_banned_methods_are_flagged():
    tools = _reg()
    from server.guardrail import BANNED_METHODS
    for method in BANNED_METHODS:
        result = tools["assert_background_safe"](method)
        assert result["error"] == "not_background_safe", f"{method} should be banned"


# ── get_audit_log ─────────────────────────────────────────────────────────────

def test_get_audit_log_returns_entries(tmp_path):
    tools = _reg()
    from core.audit import AuditLog
    log = AuditLog(tmp_path / "test.jsonl")
    log.record("invoke", {"handle": "h"}, {"ok": True}, 5.0, "s1")
    log.record("set_text", {"handle": "h"}, {"ok": True}, 3.0, "s1")
    with patch("skills.safety.AUDIT", log):
        result = tools["get_audit_log"](last_n=10)
    assert len(result) == 2
    assert result[0]["tool"] == "invoke"


def test_get_audit_log_last_n():
    tools = _reg()
    from core.audit import AuditLog
    import tempfile
    from pathlib import Path
    log = AuditLog(Path(tempfile.mktemp(suffix=".jsonl")))
    for i in range(5):
        log.record(f"tool_{i}", {}, {"ok": True}, 1.0, "s")
    with patch("skills.safety.AUDIT", log):
        result = tools["get_audit_log"](last_n=2)
    assert len(result) == 2
    assert result[-1]["tool"] == "tool_4"


# ── dry_run ───────────────────────────────────────────────────────────────────

def test_dry_run_stale_handle():
    tools = _reg()
    with _handle(None, "bad") as h:
        result = tools["dry_run"](h, "Button[title='OK']", "invoke")
    assert result == {"error": "stale_handle"}


def test_dry_run_ok():
    tools = _reg()
    win = MagicMock()
    child = MagicMock()
    child.element_info.control_type = "Button"
    child.window_text.return_value = "OK"
    child.element_info.automation_id = "btn_ok"
    child.is_enabled.return_value = True
    child.is_visible.return_value = True
    mock_selector = MagicMock()
    mock_selector.resolve.return_value = child
    mock_selector.SelectorError = Exception
    import sys
    with _handle(win) as h, patch.dict(sys.modules, {"core.selector": mock_selector}):
        result = tools["dry_run"](h, "Button[title='OK']", "invoke")
    assert result["dry_run"] is True
    assert result["will_execute"] is False
    assert result["resolved"]["title"] == "OK"
    assert result["planned_action"] == "invoke"


def test_dry_run_selector_error():
    tools = _reg()
    win = MagicMock()
    mock_selector = MagicMock()
    mock_selector.resolve.side_effect = Exception("parse error")
    mock_selector.SelectorError = Exception
    import sys
    with _handle(win) as h, patch.dict(sys.modules, {"core.selector": mock_selector}):
        result = tools["dry_run"](h, "???invalid", "invoke")
    assert "error" in result


# ── get_guardrail_status ──────────────────────────────────────────────────────

def test_get_guardrail_status_shape():
    tools = _reg()
    result = tools["get_guardrail_status"]()
    assert result["banned_input_guardrail"]["active"] is True
    assert isinstance(result["banned_input_guardrail"]["banned_methods"], (set, list))
    assert "stop_requested" in result
    assert "handle_cache_size" in result


# ── panic_stop / clear_stop ───────────────────────────────────────────────────

def test_panic_stop_sets_flag():
    import skills.safety as sm
    sm._STOP_REQUESTED = False
    tools = _reg()
    result = tools["panic_stop"]()
    assert result == {"ok": True, "stop_requested": True}
    assert sm._STOP_REQUESTED is True
    sm._STOP_REQUESTED = False  # cleanup


def test_clear_stop_clears_flag():
    import skills.safety as sm
    sm._STOP_REQUESTED = True
    tools = _reg()
    result = tools["clear_stop"]()
    assert result == {"ok": True, "stop_requested": False}
    assert sm._STOP_REQUESTED is False


def test_get_guardrail_status_reflects_stop_flag():
    import skills.safety as sm
    sm._STOP_REQUESTED = True
    tools = _reg()
    result = tools["get_guardrail_status"]()
    assert result["stop_requested"] is True
    sm._STOP_REQUESTED = False  # cleanup
