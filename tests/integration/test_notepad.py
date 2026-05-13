"""Integration tests against real Notepad.exe.

Requires Windows with Notepad available. Skipped automatically on non-Windows.
"""

import platform
import subprocess
import time

import pytest

pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Windows-only integration test",
)


@pytest.fixture
def notepad_pid():
    proc = subprocess.Popen(["notepad.exe"])
    time.sleep(0.8)
    yield proc.pid
    try:
        proc.kill()
        proc.wait(timeout=3)
    except Exception:
        pass


def test_list_windows_finds_notepad(notepad_pid):
    from pywinauto import Desktop
    desk = Desktop(backend="uia")
    titles = [w.window_text() for w in desk.windows()]
    assert any("Notepad" in t or "Untitled" in t for t in titles)


def test_find_edit_and_set_text(notepad_pid):
    from pywinauto import Application
    app = Application(backend="uia").connect(process=notepad_pid, timeout=5)
    win = app.top_window()
    edit = win.child_window(control_type="Edit")
    edit.set_edit_text("CDG background write test")
    value = edit.get_value()
    assert "CDG" in value


def test_background_type_does_not_steal_focus(notepad_pid):
    """Typing via PostMessage leaves system focus unchanged."""
    import ctypes

    from pywinauto import Application

    initial_focus = ctypes.windll.user32.GetForegroundWindow()
    app = Application(backend="uia").connect(process=notepad_pid, timeout=5)
    win = app.top_window()
    import win32con
    import win32gui
    hwnd = win.handle
    for ch in "hello":
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(ch), 0)
    time.sleep(0.1)
    after_focus = ctypes.windll.user32.GetForegroundWindow()
    assert initial_focus == after_focus, "Focus was stolen — guardrail failure"
