"""Tests for audit middleware.

Uses a mock FastMCP object so no Windows/MCP runtime is needed.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_mock_mcp(tools: dict):
    """Build a minimal FastMCP mock with ._tools populated."""
    mcp = MagicMock()
    mcp._tools = {}
    for name, fn in tools.items():
        tool = MagicMock()
        tool.fn = fn
        mcp._tools[name] = tool
    return mcp


def test_wraps_all_tools():
    from core.middleware import install_audit_middleware

    called = []

    def my_tool(x: int) -> dict:
        called.append(x)
        return {"value": x}

    mcp = _make_mock_mcp({"my_tool": my_tool})
    install_audit_middleware(mcp)

    # The fn was replaced with a wrapper.
    wrapped = mcp._tools["my_tool"].fn
    assert wrapped is not my_tool
    result = wrapped(x=42)
    assert result == {"value": 42}
    assert called == [42]


def test_records_to_audit_log(tmp_path):
    from core.audit import AuditLog
    from core.middleware import install_audit_middleware

    log_path = tmp_path / "audit.jsonl"

    def my_tool(name: str) -> dict:
        return {"ok": True}

    mcp = _make_mock_mcp({"my_tool": my_tool})

    with patch("core.middleware.AUDIT", AuditLog(log_path)), \
         patch("core.middleware.CFG") as mock_cfg:
        mock_cfg.audit.enabled = True
        mock_cfg.server.session_id = "test"
        install_audit_middleware(mcp)
        mcp._tools["my_tool"].fn(name="hello")

    entries = AuditLog(log_path).read_all()
    assert len(entries) == 1
    assert entries[0]["tool"] == "my_tool"
    assert entries[0]["result"] == {"ok": True}


def test_skips_gracefully_when_tools_missing():
    """No crash if mcp._tools is absent (FastMCP API change)."""
    from core.middleware import install_audit_middleware

    mcp = MagicMock(spec=[])  # no _tools attribute
    install_audit_middleware(mcp)  # must not raise


def test_skips_tool_with_no_fn():
    from core.middleware import install_audit_middleware

    tool_no_fn = MagicMock(spec=[])  # no .fn attribute
    mcp = MagicMock()
    mcp._tools = {"broken_tool": tool_no_fn}
    install_audit_middleware(mcp)  # must not raise


def test_redacts_long_string_args(tmp_path):
    from core.audit import AuditLog
    from core.middleware import install_audit_middleware

    log_path = tmp_path / "audit.jsonl"

    def tool(body: str) -> dict:
        return {"ok": True}

    mcp = _make_mock_mcp({"tool": tool})
    long_str = "x" * 300

    with patch("core.middleware.AUDIT", AuditLog(log_path)), \
         patch("core.middleware.CFG") as mock_cfg:
        mock_cfg.audit.enabled = True
        mock_cfg.server.session_id = "s"
        install_audit_middleware(mcp)
        mcp._tools["tool"].fn(body=long_str)

    entries = AuditLog(log_path).read_all()
    assert len(entries[0]["args"]["body"]) <= 124  # 120 + "…"


def test_records_duration_ms(tmp_path):
    from core.audit import AuditLog
    from core.middleware import install_audit_middleware

    log_path = tmp_path / "audit.jsonl"

    def slow_tool() -> dict:
        time.sleep(0.05)
        return {"ok": True}

    mcp = _make_mock_mcp({"slow_tool": slow_tool})

    with patch("core.middleware.AUDIT", AuditLog(log_path)), \
         patch("core.middleware.CFG") as mock_cfg:
        mock_cfg.audit.enabled = True
        mock_cfg.server.session_id = "s"
        install_audit_middleware(mcp)
        mcp._tools["slow_tool"].fn()

    entries = AuditLog(log_path).read_all()
    assert entries[0]["duration_ms"] >= 40.0
