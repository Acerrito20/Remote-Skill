"""Action skills — background-safe interactions only.

Every method here avoids focus theft. Banned methods (click_input, type_keys,
etc.) are intercepted at the guardrail layer before they can reach the OS.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import time

from core.com_threading import com_thread
from core.handle_cache import HANDLES
from core.retry import with_retry

# ── SendInput structures (safe to define on any OS; windll is only touched
#    at call-time inside the tools, which are Windows-only code paths) ─────────

class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),  # ULONG_PTR, pointer-sized
    ]

class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("mi", _MOUSEINPUT)]


def _sendinput_drag(
    screen_start: tuple[int, int],
    screen_end: tuple[int, int],
    duration_ms: int,
    steps: int,
) -> None:
    """Execute a drag via SendInput within the agent's isolated RDP session.

    Safe because SendInput here moves the agent's virtual cursor on the virtual
    display — it never touches the operator's real cursor in the console session.
    Do NOT call this from a process running in Session 0 or the user's session.
    """
    MOVE = 0x0001
    LDOWN = 0x0002
    LUP = 0x0004
    ABS = 0x8000
    user32 = ctypes.windll.user32

    sm_cx = user32.GetSystemMetrics(0)
    sm_cy = user32.GetSystemMetrics(1)

    def _to_abs(sx: int, sy: int) -> tuple[int, int]:
        return int(sx * 65535 / sm_cx), int(sy * 65535 / sm_cy)

    def _send(x: int, y: int, flags: int) -> None:
        inp = _INPUT()
        inp.type = 0  # INPUT_MOUSE
        inp.mi.dx, inp.mi.dy = x, y
        inp.mi.dwFlags = flags
        inp.mi.mouseData = 0
        inp.mi.time = 0
        inp.mi.dwExtraInfo = None
        ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

    ax, ay = _to_abs(*screen_start)
    ex, ey = _to_abs(*screen_end)
    step_delay = (duration_ms / steps) / 1000.0

    _send(ax, ay, MOVE | ABS)
    _send(ax, ay, LDOWN | ABS)
    for i in range(1, steps + 1):
        t = i / steps
        _send(int(ax + (ex - ax) * t), int(ay + (ey - ay) * t), MOVE | ABS)
        time.sleep(step_delay)
    _send(ex, ey, LUP | ABS)


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

    @mcp.tool()
    def virtual_drag(
        window_handle: str,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 500,
        steps: int = 20,
    ) -> dict:
        """Drag from one point to another within a window's client area.

        Tries three strategies in order:
        1. UIA DragPattern — cleanest, but rarely implemented by apps.
        2. PostMessage WM_LBUTTONDOWN → WM_MOUSEMOVE×N → WM_LBUTTONUP —
           works for standard Win32/WPF apps that process WM_MOUSE messages.
        3. Session-scoped SendInput — for GPU-accelerated apps (CapCut,
           DaVinci Resolve, etc.) that read raw/direct input and ignore the
           Win32 message queue.

        Strategy 3 is safe: the server runs inside the isolated 'agent' RDP
        session. SendInput there moves the agent's virtual cursor on the virtual
        display only — the operator's real cursor on the console session is
        completely unaffected.
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}

        hwnd = win.handle

        # Tier 1: UIA DragPattern
        try:
            drag = win.iface_drag
            drag.Start(start_x, start_y)
            drag.Stop(end_x, end_y)
            return {"ok": True, "method": "uia_drag"}
        except Exception:
            pass

        # Tier 2: PostMessage WM_MOUSEMOVE sequence
        try:
            import win32api
            import win32con
            import win32gui

            step_delay = (duration_ms / steps) / 1000.0
            win32gui.PostMessage(
                hwnd, win32con.WM_LBUTTONDOWN,
                win32con.MK_LBUTTON, win32api.MAKELONG(start_x, start_y),
            )
            for i in range(1, steps + 1):
                t = i / steps
                mx = int(start_x + (end_x - start_x) * t)
                my = int(start_y + (end_y - start_y) * t)
                win32gui.PostMessage(
                    hwnd, win32con.WM_MOUSEMOVE,
                    win32con.MK_LBUTTON, win32api.MAKELONG(mx, my),
                )
                time.sleep(step_delay)
            win32gui.PostMessage(
                hwnd, win32con.WM_LBUTTONUP, 0, win32api.MAKELONG(end_x, end_y),
            )
            return {"ok": True, "method": "postmessage_sequence"}
        except Exception:
            pass

        # Tier 3: Session-scoped SendInput (raw-input apps like CapCut)
        try:
            import win32gui
            screen_start = win32gui.ClientToScreen(hwnd, (start_x, start_y))
            screen_end = win32gui.ClientToScreen(hwnd, (end_x, end_y))
            _sendinput_drag(screen_start, screen_end, duration_ms, steps)
            return {"ok": True, "method": "sendinput_session"}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def drag_screen(
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 500,
        steps: int = 20,
    ) -> dict:
        """Drag between absolute screen coordinates in the agent's virtual display.

        Use this when OCR (find_text_in_hwnd / ocr_region) gives you screen
        coordinates and you need to drag without a window handle.

        All coordinates are screen-absolute within the agent session only —
        they have no effect on the operator's console session.
        """
        try:
            _sendinput_drag(
                (start_x, start_y), (end_x, end_y), duration_ms, steps
            )
            return {
                "ok": True,
                "method": "sendinput_session",
                "screen_start": [start_x, start_y],
                "screen_end": [end_x, end_y],
            }
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}
