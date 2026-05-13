"""Discovery skills — find windows, processes, and elements.

These are always called first in any automation flow.
Engine selection for connect_app is driven by CFG.engine_for(path).
"""

from __future__ import annotations

from core.com_threading import com_thread
from core.config import CFG
from core.handle_cache import HANDLES
from core.retry import with_retry


def register(mcp) -> None:

    @mcp.tool()
    @com_thread
    def list_windows() -> list[dict]:
        """Enumerate all visible top-level windows."""
        try:
            from pywinauto import Desktop
            windows = []
            for win in Desktop(backend="uia").windows():
                try:
                    windows.append({
                        "handle": HANDLES.register(win),
                        "hwnd": win.handle,
                        "title": win.window_text(),
                        "class_name": win.class_name(),
                        "visible": win.is_visible(),
                        "enabled": win.is_enabled(),
                    })
                except Exception:
                    pass
            return windows
        except Exception as exc:
            return [{"error": str(exc)}]

    @mcp.tool()
    def list_processes(name_filter: str = "") -> list[dict]:
        """List running processes. Optionally filter by executable name (case-insensitive)."""
        try:
            import psutil
            results = []
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                info = proc.info
                if name_filter and name_filter.lower() not in (info.get("name") or "").lower():
                    continue
                results.append({
                    "pid": info["pid"],
                    "name": info.get("name", ""),
                    "exe": info.get("exe", ""),
                })
            return results
        except ImportError:
            return [{"error": "psutil not installed; run: uv pip install psutil"}]
        except Exception as exc:
            return [{"error": str(exc)}]

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def connect_app(
        title_re: str = "",
        pid: int = 0,
        path: str = "",
        backend: str = "",
    ) -> dict:
        """Attach to a running app by title regex, PID, or executable path.

        Engine and backend are resolved from config/app_overrides/ based on the
        executable name. Pass backend explicitly to override the config value.
        Returns a window handle for use with other tools.
        """
        try:
            override = CFG.override_for(path) if path else None
            engine = override.engine if override else CFG.default_engine
            effective_backend = backend or (override.backend if override else "uia")
            timeout = CFG.timeouts.connect_seconds

            if engine == "playwright":
                # Electron app — return CDP connection info instead of a UIA handle.
                cdp_url = CFG.cdp_url_for(path)
                return {
                    "engine": "playwright",
                    "cdp_url": cdp_url,
                    "note": (
                        f"Use browser_open(cdp_url='{cdp_url}') for Electron apps. "
                        "Start the app with --remote-debugging-port first."
                    ),
                }

            from pywinauto import Application
            app = Application(backend=effective_backend)
            if pid:
                app = app.connect(process=pid, timeout=timeout)
            elif path:
                app = app.connect(path=path, timeout=timeout)
            elif title_re:
                app = app.connect(title_re=title_re, timeout=timeout)
            else:
                return {"error": "Provide title_re, pid, or path"}

            win = app.top_window()
            handle = HANDLES.register(win)
            return {
                "handle": handle,
                "title": win.window_text(),
                "hwnd": win.handle,
                "pid": win.process_id(),
                "engine": engine,
                "backend": effective_backend,
            }
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    def get_tree(window_handle: str, max_depth: int = 4) -> dict:
        """Dump the UIA subtree from a window, depth-limited.

        max_depth > 6 on complex apps can take 10+ seconds — default is 4.
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}

        def _node(elem, depth: int) -> dict:
            try:
                node = {
                    "control_type": elem.element_info.control_type,
                    "title": elem.window_text(),
                    "auto_id": elem.element_info.automation_id,
                    "class_name": elem.element_info.class_name,
                    "enabled": elem.is_enabled(),
                    "visible": elem.is_visible(),
                }
                if depth > 0:
                    children = []
                    for child in elem.children():
                        try:
                            children.append(_node(child, depth - 1))
                        except Exception:
                            pass
                    node["children"] = children
                return node
            except Exception as exc:
                return {"error": str(exc)}

        try:
            return _node(win, max_depth)
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def find_element(
        window_handle: str,
        auto_id: str = "",
        name: str = "",
        control_type: str = "",
        class_name: str = "",
        title_re: str = "",
    ) -> dict:
        """Search a window's descendants by UIA criteria."""
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            kwargs: dict = {}
            if auto_id:
                kwargs["auto_id"] = auto_id
            if name:
                kwargs["title"] = name
            if control_type:
                kwargs["control_type"] = control_type
            if class_name:
                kwargs["class_name"] = class_name
            if title_re:
                kwargs["title_re"] = title_re
            elem = win.child_window(**kwargs)
            handle = HANDLES.register(elem)
            return {
                "handle": handle,
                "control_type": elem.element_info.control_type,
                "title": elem.window_text(),
                "auto_id": elem.element_info.automation_id,
                "enabled": elem.is_enabled(),
                "visible": elem.is_visible(),
            }
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    @com_thread
    def inspect_element(element_handle: str) -> dict:
        """Full property dump of one element."""
        elem = HANDLES.get(element_handle)
        if elem is None:
            return {"error": "stale_handle"}
        try:
            info = elem.element_info
            props = {
                "control_type": info.control_type,
                "class_name": info.class_name,
                "automation_id": info.automation_id,
                "title": elem.window_text(),
                "enabled": elem.is_enabled(),
                "visible": elem.is_visible(),
                "hwnd": elem.handle,
                "rectangle": elem.rectangle().__repr__() if elem.handle else None,
            }
            try:
                props["value"] = elem.get_value()
            except Exception:
                pass
            try:
                props["legacy_properties"] = elem.legacy_properties()
            except Exception:
                pass
            return props
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    @com_thread
    @with_retry(max_attempts=3)
    def find_by_path(window_handle: str, selector: str) -> dict:
        """Resolve a selector string against a window.

        Example: "Edit[auto_id='15']"
                 "ToolBar[name='Standard'] > Button[title~='Save']"
        """
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            from core.selector import SelectorError, resolve
            elem = resolve(selector, win)
            handle = HANDLES.register(elem)
            return {
                "handle": handle,
                "control_type": elem.element_info.control_type,
                "title": elem.window_text(),
                "auto_id": elem.element_info.automation_id,
            }
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}
