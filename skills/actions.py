"""Action skills — background-safe interactions only.

Every method here avoids focus theft. Banned methods (click_input, type_keys,
etc.) are intercepted at the guardrail layer before they can reach the OS.
"""

from __future__ import annotations

from core.com_threading import com_thread
from core.handle_cache import HANDLES
from core.retry import with_retry


def register(mcp) -> None:

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def invoke(element_handle: str) -> dict:
        """Activate an element via UIA InvokePattern (background-safe click)."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            elem.invoke()
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def set_text(element_handle: str, text: str) -> dict:
        """Set the value of an Edit or ComboBox via UIA ValuePattern.

        Falls back to WM_SETTEXT if ValuePattern is unavailable.
        """
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            elem.set_edit_text(text)
            return {"ok": True}
        except Exception as uia_exc:
            try:
                import win32con
                import win32gui
                win32gui.SendMessage(elem.handle, win32con.WM_SETTEXT, 0, text)
                return {"ok": True, "method": "WM_SETTEXT"}
            except Exception as win32_exc:
                return {
                    "error": str(uia_exc),
                    "win32_error": str(win32_exc),
                }

    @mcp.tool()
    @com_thread
    def get_text(element_handle: str) -> dict:
        """Read the current text/value of an element."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            value = elem.get_value()
            return {"value": value}
        except Exception:
            try:
                return {"value": elem.window_text()}
            except Exception as exc:
                return {"error": str(exc)}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def select_combo_item(element_handle: str, item_text: str) -> dict:
        """Select a ComboBox item by its visible text via UIA SelectionItemPattern."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            elem.select(item_text)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def toggle_checkbox(element_handle: str) -> dict:
        """Flip the state of a checkbox via UIA TogglePattern."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            elem.toggle()
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def set_checkbox(element_handle: str, checked: bool) -> dict:
        """Set a checkbox to a specific checked/unchecked state."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            current = elem.get_toggle_state()
            # ToggleState: 0=Off, 1=On, 2=Indeterminate
            is_checked = current == 1
            if is_checked != checked:
                elem.toggle()
            return {"ok": True, "checked": checked}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def expand_tree_node(element_handle: str) -> dict:
        """Expand a tree node or menu via UIA ExpandCollapsePattern."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            elem.expand()
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def collapse_tree_node(element_handle: str) -> dict:
        """Collapse a tree node via UIA ExpandCollapsePattern."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            elem.collapse()
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def scroll_into_view(element_handle: str) -> dict:
        """Bring an element into the visible viewport via UIA ScrollItemPattern."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            elem.scroll_into_view()
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def menu_select(window_handle: str, menu_path: str) -> dict:
        """Select a menu item by path, e.g. 'File→Save As'.

        Uses WM_COMMAND posted to the HWND — does not steal focus.
        Separator character is '→' or '>'.
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            parts = [p.strip() for p in menu_path.replace("→", ">").split(">")]
            win.menu_select(*parts)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def background_click(window_handle: str, x: int, y: int) -> dict:
        """Synthesize a left-click at (x, y) relative to window client area.

        Uses PostMessage(WM_LBUTTONDOWN/UP) — never moves the real cursor.
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            import win32api
            import win32con
            import win32gui
            hwnd = win.handle
            lp = win32api.MAKELONG(x, y)
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def background_type(window_handle: str, text: str) -> dict:
        """Synthesize keyboard input into an HWND via WM_CHAR per character.

        Does not route through the raw input queue; safe in background sessions.
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            import win32con
            import win32gui
            hwnd = win.handle
            for ch in text:
                win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(ch), 0)
            return {"ok": True, "chars_sent": len(text)}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def send_raw_message(
        window_handle: str,
        msg: int,
        wparam: int = 0,
        lparam: int = 0,
        post: bool = False,
    ) -> dict:
        """Send or post an arbitrary Win32 message to an HWND.

        post=True uses PostMessage (async); post=False uses SendMessage (sync).
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            import win32gui
            hwnd = win.handle
            if post:
                win32gui.PostMessage(hwnd, msg, wparam, lparam)
                return {"ok": True, "sent": "posted"}
            else:
                result = win32gui.SendMessage(hwnd, msg, wparam, lparam)
                return {"ok": True, "result": result}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}
