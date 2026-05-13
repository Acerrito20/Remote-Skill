"""FlaUI adapter — .NET UIA bridge via pythonnet.

Handles edge cases pywinauto misses: WPF custom controls, certain ComboBox
patterns, UIA3-specific property variants.

Requires:
  uv pip install pythonnet
  FlaUI.Core.dll + FlaUI.UIA3.dll on the Python path or in engines/flaui_dlls/
"""

from __future__ import annotations

from pathlib import Path

_DLL_DIR = Path(__file__).parent / "flaui_dlls"


def _load_clr():
    import clr
    if _DLL_DIR.exists():
        import sys
        sys.path.insert(0, str(_DLL_DIR))
    clr.AddReference("FlaUI.Core")
    clr.AddReference("FlaUI.UIA3")
    return clr


def attach(process_name: str):
    """Attach to a running process by name. Returns (app, automation, window)."""
    _load_clr()
    from FlaUI.Core import Application  # type: ignore[import]
    from FlaUI.UIA3 import UIA3Automation  # type: ignore[import]
    app = Application.Attach(process_name)
    automation = UIA3Automation()
    window = app.GetMainWindow(automation)
    return app, automation, window


def launch(executable: str, args: str = ""):
    """Launch an executable. Returns (app, automation, window)."""
    _load_clr()
    from FlaUI.Core import Application  # type: ignore[import]
    from FlaUI.UIA3 import UIA3Automation  # type: ignore[import]
    app = Application.Launch(executable)
    automation = UIA3Automation()
    window = app.GetMainWindow(automation)
    return app, automation, window
