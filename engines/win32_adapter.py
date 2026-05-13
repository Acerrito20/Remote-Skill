"""Win32 adapter — raw user32/kernel32 bindings via pywin32.

Use for:
 - Custom-drawn controls with no UIA tree.
 - Sending WM_COMMAND to trigger menu items by ID.
 - Reading text from controls via WM_GETTEXT.
 - Any HWND-level operation pywinauto's UIA backend can't reach.
"""

from __future__ import annotations


def find_window(class_name: str = "", title: str = "") -> int:
    import win32gui
    return win32gui.FindWindow(class_name or None, title or None)


def enum_child_windows(hwnd: int) -> list[int]:
    import win32gui
    children: list[int] = []
    win32gui.EnumChildWindows(hwnd, lambda h, _: children.append(h), None)
    return children


def send_message(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> int:
    import win32gui
    return win32gui.SendMessage(hwnd, msg, wparam, lparam)


def post_message(hwnd: int, msg: int, wparam: int = 0, lparam: int = 0) -> None:
    import win32gui
    win32gui.PostMessage(hwnd, msg, wparam, lparam)


def get_window_text(hwnd: int) -> str:
    import win32gui
    return win32gui.GetWindowText(hwnd)


def set_window_text(hwnd: int, text: str) -> None:
    import win32con
    import win32gui
    win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, 0, text)


def simulate_click(hwnd: int, x: int = 5, y: int = 5) -> None:
    """Post WM_LBUTTONDOWN/UP to hwnd client coords — never moves the real cursor."""
    import win32api
    import win32con
    import win32gui
    lp = win32api.MAKELONG(x, y)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
