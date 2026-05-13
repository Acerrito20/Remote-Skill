"""Audit middleware — wraps every registered MCP tool automatically.

Instead of each tool calling AUDIT.record() manually, install_audit_middleware()
patches the FastMCP tool registry once at server startup so every tool invocation
is recorded without any per-tool boilerplate.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Callable

from core.audit import AUDIT
from core.config import CFG
from core.logging import log


def _wrap_tool(fn: Callable, tool_name: str) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        result = None
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception as exc:
            result = {"error": str(exc), "type": type(exc).__name__}
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            if CFG.audit.enabled:
                # Redact large bodies (e.g. chapter text) from audit args.
                safe_kwargs = {
                    k: (v[:120] + "…" if isinstance(v, str) and len(v) > 120 else v)
                    for k, v in kwargs.items()
                }
                AUDIT.record(
                    tool=tool_name,
                    args=safe_kwargs,
                    result=result if isinstance(result, dict) else {},
                    duration_ms=duration_ms,
                    session_id=CFG.server.session_id,
                )
            log.debug("tool", name=tool_name, duration_ms=round(duration_ms, 1))
    return wrapper


def install_audit_middleware(mcp) -> None:
    """Wrap every tool already registered on `mcp` with audit + timing.

    Call this after all skill modules have called register(mcp), before mcp.run().

    FastMCP stores tools in `._tools` (a dict of name → Tool). We access this
    internal attribute because FastMCP has no public wrapping API. If it changes,
    the server still starts cleanly — middleware is skipped with a warning rather
    than crashing.
    """
    # FastMCP relocated the tool dict to mcp._tool_manager._tools at some point
    # (was mcp._tools in older releases). Probe the new location first, fall
    # back to the old, then warn-and-skip rather than crash.
    tool_registry = None
    tool_manager = getattr(mcp, "_tool_manager", None)
    if tool_manager is not None:
        tool_registry = getattr(tool_manager, "_tools", None)
    if tool_registry is None:
        tool_registry = getattr(mcp, "_tools", None)
    if tool_registry is None:
        log.warning(
            "audit_middleware_skipped",
            reason="Neither mcp._tool_manager._tools nor mcp._tools found",
        )
        return
    for name, tool in list(tool_registry.items()):
        original_fn = getattr(tool, "fn", None)
        if original_fn is None:
            continue
        tool.fn = _wrap_tool(original_fn, name)
