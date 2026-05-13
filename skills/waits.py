"""State / wait skills — synchronize against UI state changes.

Never use time.sleep() inside tool bodies — always explicit UIA waits with timeouts.
"""

from __future__ import annotations

import time

from core.com_threading import com_thread
from core.handle_cache import HANDLES


def register(mcp) -> None:

    @mcp.tool()
    @com_thread
    def wait_for(
        element_handle: str,
        state: str = "exists",
        timeout: float = 10.0,
    ) -> dict:
        """Wait until element reaches a target state.

        state options: 'exists', 'visible', 'enabled', 'ready' (visible + enabled)
        """
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    ok = False
                    if state == "exists":
                        ok = elem.exists()
                    elif state == "visible":
                        ok = elem.is_visible()
                    elif state == "enabled":
                        ok = elem.is_enabled()
                    elif state == "ready":
                        ok = elem.is_visible() and elem.is_enabled()
                    if ok:
                        return {"ok": True, "state": state}
                except Exception:
                    pass
                time.sleep(0.1)
            return {"error": "timeout", "state": state, "timeout_seconds": timeout}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    @com_thread
    def wait_for_idle(window_handle: str, timeout: float = 10.0) -> dict:
        """Wait until the window's UI thread is quiescent."""
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            win.wait("exists ready", timeout=timeout)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "timeout_seconds": timeout}

    @mcp.tool()
    @com_thread
    def wait_for_window(
        title_re: str = "",
        class_name: str = "",
        timeout: float = 15.0,
    ) -> dict:
        """Block until a top-level window matching criteria appears."""
        try:
            from pywinauto import Desktop
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    desk = Desktop(backend="uia")
                    for win in desk.windows():
                        try:
                            title_ok = (not title_re) or __import__("re").search(
                                title_re, win.window_text()
                            )
                            class_ok = (not class_name) or win.class_name() == class_name
                            if title_ok and class_ok:
                                handle = HANDLES.register(win)
                                return {
                                    "handle": handle,
                                    "title": win.window_text(),
                                    "hwnd": win.handle,
                                }
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(0.25)
            return {"error": "timeout", "timeout_seconds": timeout}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    @com_thread
    def poll_until(
        element_handle: str,
        property_name: str,
        expected_value: str,
        timeout: float = 15.0,
        interval: float = 0.5,
    ) -> dict:
        """Poll element.property_name until it equals expected_value (as string)."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                actual = str(getattr(elem, property_name, None) or elem.window_text())
                if actual == expected_value:
                    return {"ok": True, "value": actual}
            except Exception:
                pass
            time.sleep(interval)
        return {
            "error": "timeout",
            "property": property_name,
            "expected": expected_value,
            "timeout_seconds": timeout,
        }
