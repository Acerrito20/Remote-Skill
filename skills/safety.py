"""Safety / guardrail skills — meta-tools for verifying safe operation.

Claude can call these to introspect its own safety envelope before acting.
"""

from __future__ import annotations

import time

from core.audit import AUDIT
from core.handle_cache import HANDLES

_IN_FLIGHT: list[dict] = []
_STOP_REQUESTED = False


def register(mcp) -> None:

    @mcp.tool()
    def assert_background_safe(action: str) -> dict:
        """Verify that the named action is on the background-safe allowlist.

        Returns ok=True if safe, error with reason if not.
        """
        from server.guardrail import BANNED_METHODS
        if action in BANNED_METHODS:
            return {
                "error": "not_background_safe",
                "action": action,
                "reason": (
                    f"'{action}' moves the real cursor or steals focus. "
                    "Use the UIA pattern equivalent or PostMessage instead."
                ),
            }
        return {"ok": True, "action": action}

    @mcp.tool()
    def get_audit_log(last_n: int = 50) -> list[dict]:
        """Return the most recent N audit log entries (read-only)."""
        entries = AUDIT.read_all()
        return entries[-last_n:] if last_n else entries

    @mcp.tool()
    def dry_run(window_handle: str, selector: str, action: str) -> dict:
        """Resolve a selector and describe the planned action without executing it.

        Use this to verify targeting before committing.
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            from core.selector import SelectorError, resolve
            elem = resolve(selector, win)
            return {
                "dry_run": True,
                "resolved": {
                    "control_type": elem.element_info.control_type,
                    "title": elem.window_text(),
                    "auto_id": elem.element_info.automation_id,
                    "enabled": elem.is_enabled(),
                    "visible": elem.is_visible(),
                },
                "planned_action": action,
                "will_execute": False,
            }
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def get_guardrail_status() -> dict:
        """List active guardrails and their current state."""
        from server.guardrail import BANNED_METHODS
        return {
            "banned_input_guardrail": {
                "active": True,
                "banned_methods": BANNED_METHODS,
            },
            "stop_requested": _STOP_REQUESTED,
            "handle_cache_size": len(HANDLES),
        }

    @mcp.tool()
    def panic_stop() -> dict:
        """Immediately set the stop flag to abort any pending agent actions.

        Does not kill the server process itself; call kill_app for that.
        """
        global _STOP_REQUESTED
        _STOP_REQUESTED = True
        return {"ok": True, "stop_requested": True}

    @mcp.tool()
    def clear_stop() -> dict:
        """Clear the panic_stop flag to resume normal operation."""
        global _STOP_REQUESTED
        _STOP_REQUESTED = False
        return {"ok": True, "stop_requested": False}
