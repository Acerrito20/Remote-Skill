"""pywinauto adapter — primary UIA engine.

Wraps Application connect/start with the guardrail already installed.
Backend selection: 'uia' (default) or 'win32' for legacy MFC apps.
"""

from __future__ import annotations


def connect(
    title_re: str = "",
    pid: int = 0,
    path: str = "",
    backend: str = "uia",
    timeout: float = 5.0,
):
    from pywinauto import Application
    app = Application(backend=backend)
    if pid:
        return app.connect(process=pid, timeout=timeout)
    if path:
        return app.connect(path=path, timeout=timeout)
    if title_re:
        return app.connect(title_re=title_re, timeout=timeout)
    raise ValueError("Provide title_re, pid, or path")


def start(executable: str, args: str = "", backend: str = "uia"):
    from pywinauto import Application
    cmd = f'"{executable}" {args}'.strip()
    return Application(backend=backend).start(cmd)
