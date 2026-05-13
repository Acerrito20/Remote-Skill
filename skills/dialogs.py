"""Dialog / nuisance handling — auto-dismiss modal popups.

A background watcher thread subscribes to UIA StructureChanged events and
matches new windows against registered rules, firing the dismiss action before
the dialog can steal focus from the user's real session.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Any

from core.com_threading import com_thread
from core.handle_cache import HANDLES

# Rule registry: list of {match: {title_re, class_name}, action, target}
_RULES: list[dict[str, Any]] = []
_RULES_LOCK = threading.Lock()
_WATCHER_THREAD: threading.Thread | None = None
_WATCHER_STOP = threading.Event()


def _match_window(win, rule: dict) -> bool:
    match = rule.get("match", {})
    if "title_re" in match:
        if not re.search(match["title_re"], win.window_text()):
            return False
    if "class_name" in match:
        if win.class_name() != match["class_name"]:
            return False
    return True


def _apply_rule(win, rule: dict) -> None:
    action = rule.get("action", "")
    target = rule.get("target", {})
    try:
        if action == "click_button" or action == "click":
            title = target if isinstance(target, str) else target.get("title", "")
            btn = win.child_window(title=title, control_type="Button")
            btn.invoke()
        elif action == "close":
            win.close()
    except Exception:
        pass


def _watcher_loop() -> None:
    """Background thread: poll for new top-level windows matching registered rules."""
    try:
        import pythoncom
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
    except Exception:
        pass

    try:
        from pywinauto import Desktop
    except ImportError:
        return

    seen: set[int] = set()
    while not _WATCHER_STOP.is_set():
        try:
            desk = Desktop(backend="uia")
            for win in desk.windows():
                try:
                    hwnd = win.handle
                    if hwnd in seen:
                        continue
                    seen.add(hwnd)
                    with _RULES_LOCK:
                        for rule in _RULES:
                            if _match_window(win, rule):
                                _apply_rule(win, rule)
                                break
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(0.5)


def _ensure_watcher() -> None:
    global _WATCHER_THREAD
    if _WATCHER_THREAD is None or not _WATCHER_THREAD.is_alive():
        _WATCHER_STOP.clear()
        _WATCHER_THREAD = threading.Thread(target=_watcher_loop, daemon=True)
        _WATCHER_THREAD.start()


def register(mcp) -> None:

    @mcp.tool()
    @com_thread
    def dismiss_dialog(
        title_re: str = "",
        button_title: str = "OK",
    ) -> dict:
        """One-shot dismiss of a dialog matching title_re by clicking button_title."""
        try:
            from pywinauto import Desktop
            desk = Desktop(backend="uia")
            for win in desk.windows():
                try:
                    if title_re and not re.search(title_re, win.window_text()):
                        continue
                    btn = win.child_window(title=button_title, control_type="Button")
                    btn.invoke()
                    return {"ok": True, "dismissed": win.window_text()}
                except Exception:
                    pass
            return {"error": "no_matching_dialog"}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def register_dialog_rule(
        title_re: str,
        button_title: str,
        class_name: str = "#32770",
    ) -> dict:
        """Register an auto-dismiss rule. The background watcher applies it continuously.

        Args:
            title_re: Regex matched against dialog title.
            button_title: The button to click when matched.
            class_name: Window class — '#32770' is the standard dialog class.
        """
        rule = {
            "match": {"title_re": title_re, "class_name": class_name},
            "action": "click_button",
            "target": button_title,
        }
        with _RULES_LOCK:
            _RULES.append(rule)
        _ensure_watcher()
        return {"ok": True, "rules_registered": len(_RULES)}

    @mcp.tool()
    @com_thread
    def list_modal_dialogs() -> list[dict]:
        """Return all currently open top-level windows that look like dialogs."""
        try:
            from pywinauto import Desktop
            desk = Desktop(backend="uia")
            result = []
            for win in desk.windows():
                try:
                    if win.class_name() in ("#32770", "FNWND310", "MsoCommandBar"):
                        result.append({
                            "handle": HANDLES.register(win),
                            "title": win.window_text(),
                            "class_name": win.class_name(),
                            "hwnd": win.handle,
                        })
                except Exception:
                    pass
            return result
        except Exception as exc:
            return [{"error": str(exc)}]

    @mcp.tool()
    def screenshot_window(window_handle: str, path: str = "") -> dict:
        """Capture a window to a PNG. For error diagnostics only — not for normal operation."""
        win = HANDLES.get(window_handle)
        if win is None:
            return {"error": "stale_handle"}
        try:
            import tempfile
            from pathlib import Path
            out = path or str(Path(tempfile.mktemp(suffix=".png")))
            win.capture_as_image().save(out)
            return {"ok": True, "path": out}
        except Exception as exc:
            return {"error": str(exc)}
