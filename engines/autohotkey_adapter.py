"""AutoHotkey v2 adapter — legacy / stubborn apps.

ControlSend and ControlClick in AHK work background-safe on many ancient apps
that ignore UIA entirely. Wrap scripts in Python so the MCP server never
exposes raw AHK to Claude.

Requires AutoHotkey v2 installed and on PATH (or AHK_EXE env var set).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

AHK_EXE = os.environ.get("AHK_EXE", "AutoHotkey64.exe")


def run_script(script: str, args: list[str] | None = None, timeout: float = 10.0) -> str:
    """Write script to a temp file and run it, returning stdout."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ahk", delete=False) as fh:
        fh.write(script)
        tmp = fh.name
    try:
        result = subprocess.run(
            [AHK_EXE, tmp] + (args or []),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout or result.stderr
    finally:
        Path(tmp).unlink(missing_ok=True)


def control_click(hwnd: int, button: str = "Button1") -> str:
    script = f'ControlClick, % "{button}", % "ahk_id {hwnd}"\n'
    return run_script(script)


def control_send(hwnd: int, keys: str) -> str:
    script = f'ControlSend, , % "{keys}", % "ahk_id {hwnd}"\n'
    return run_script(script)
