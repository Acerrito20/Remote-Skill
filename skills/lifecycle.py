"""Process and app lifecycle skills — spawn, attach, kill, monitor.

start_app resolves engine from CFG when the executable has a config override.
"""

from __future__ import annotations

import subprocess
import time

from core.com_threading import com_thread
from core.config import CFG
from core.handle_cache import HANDLES


def register(mcp) -> None:

    @mcp.tool()
    def start_app(executable: str, args: list[str] | None = None) -> dict:
        """Launch an executable and return its PID.

        If the executable has a config override (e.g. engine=playwright),
        the response includes guidance on how to connect to it.
        """
        try:
            override = CFG.override_for(executable)
            engine = override.engine if override else CFG.default_engine

            # For Electron apps, inject the CDP debug port automatically.
            effective_args = list(args or [])
            if engine == "playwright" and override:
                port_arg = f"--remote-debugging-port={override.cdp_port}"
                if port_arg not in effective_args:
                    effective_args.append(port_arg)

            cmd = [executable] + effective_args
            proc = subprocess.Popen(cmd)
            result: dict = {"pid": proc.pid, "executable": executable, "engine": engine}
            if engine == "playwright" and override:
                result["cdp_url"] = override.effective_cdp_url()
                result["note"] = (
                    f"App started with CDP debug port {override.cdp_port}. "
                    f"Call browser_open(cdp_url='{override.effective_cdp_url()}') to connect."
                )
            return result
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def kill_app(pid: int) -> dict:
        """Terminate a process by PID."""
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.kill()
            proc.wait(timeout=5)
            return {"ok": True, "pid": pid}
        except ImportError:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
            ctypes.windll.kernel32.TerminateProcess(handle, 0)
            ctypes.windll.kernel32.CloseHandle(handle)
            return {"ok": True, "pid": pid, "method": "Win32"}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def restart_app(pid: int, executable: str, args: list[str] | None = None) -> dict:
        """Kill the process then relaunch with the same executable and args."""
        kill_result = kill_app(pid)
        if "error" in kill_result:
            return kill_result
        time.sleep(0.5)
        return start_app(executable, args)

    @mcp.tool()
    @com_thread
    def wait_for_app(
        title_re: str = "",
        pid: int = 0,
        timeout: float = 10.0,
    ) -> dict:
        """Block until a window matching criteria appears or timeout expires."""
        try:
            from pywinauto import Application
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    app = Application(backend="uia")
                    if pid:
                        app = app.connect(process=pid, timeout=0.5)
                    elif title_re:
                        app = app.connect(title_re=title_re, timeout=0.5)
                    else:
                        return {"error": "Provide title_re or pid"}
                    win = app.top_window()
                    handle = HANDLES.register(win)
                    return {"handle": handle, "title": win.window_text()}
                except Exception:
                    time.sleep(0.3)
            return {"error": "timeout", "timeout_seconds": timeout}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def get_app_state(pid: int) -> dict:
        """Return process state: running, hung, or not_found."""
        try:
            import psutil
            proc = psutil.Process(pid)
            status = proc.status()
            return {"pid": pid, "status": status, "name": proc.name()}
        except ImportError:
            # Fall back to IsHungAppWindow heuristic if we can find an hwnd.
            return {"pid": pid, "status": "unknown", "note": "psutil not installed"}
        except Exception as exc:
            return {"pid": pid, "status": "not_found", "error": str(exc)}

    @mcp.tool()
    @com_thread
    def list_app_windows(pid: int) -> list[dict]:
        """List all top-level windows owned by a PID."""
        try:
            from pywinauto import Application
            app = Application(backend="uia").connect(process=pid, timeout=3)
            result = []
            for win in app.windows():
                try:
                    result.append({
                        "handle": HANDLES.register(win),
                        "hwnd": win.handle,
                        "title": win.window_text(),
                        "visible": win.is_visible(),
                    })
                except Exception:
                    pass
            return result
        except Exception as exc:
            return [{"error": str(exc)}]
