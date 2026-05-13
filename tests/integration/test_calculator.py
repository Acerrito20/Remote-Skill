"""Integration tests against Windows Calculator (calc.exe).

Requires Windows. Skipped automatically on non-Windows.
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
def calc_pid():
    proc = subprocess.Popen(["calc.exe"])
    time.sleep(1.2)
    yield proc.pid
    try:
        proc.kill()
        proc.wait(timeout=3)
    except Exception:
        pass


def test_calculator_launches(calc_pid):
    from pywinauto import Application
    app = Application(backend="uia").connect(process=calc_pid, timeout=5)
    win = app.top_window()
    assert win.is_visible()


def test_invoke_button(calc_pid):
    from pywinauto import Application
    app = Application(backend="uia").connect(process=calc_pid, timeout=5)
    win = app.top_window()
    btn_1 = win.child_window(title="One", control_type="Button")
    btn_1.invoke()
    btn_plus = win.child_window(title="Plus", control_type="Button")
    btn_plus.invoke()
    btn_1.invoke()
    btn_eq = win.child_window(title="Equals", control_type="Button")
    btn_eq.invoke()
    result_display = win.child_window(auto_id="CalculatorResults")
    assert "2" in result_display.window_text()
