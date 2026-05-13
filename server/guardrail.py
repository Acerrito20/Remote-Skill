"""Banned-input guardrail.

Patches pywinauto.BaseWrapper at server startup so any focus-stealing method
raises immediately. Must be called before any tool is registered.
"""

BANNED_METHODS = [
    "click_input",
    "double_click_input",
    "right_click_input",
    "move_mouse_input",
    "drag_mouse_input",
    "press_mouse_input",
    "release_mouse_input",
    "type_keys",
    "set_focus",
]


def install() -> None:
    """Patch BaseWrapper. Safe to call multiple times (idempotent)."""
    try:
        from pywinauto.base_wrapper import BaseWrapper
    except ImportError:
        # pywinauto not available (non-Windows env). Skip silently.
        return

    for name in BANNED_METHODS:
        if not getattr(BaseWrapper, name, None):
            continue
        if getattr(getattr(BaseWrapper, name), "_cdg_banned", False):
            continue

        def _refuse(*args, _n=name, **kwargs):
            raise RuntimeError(
                f"'{_n}' is banned in background mode. "
                "Use the equivalent UIA pattern (invoke, set_text, …) or "
                "PostMessage / WM_CHAR instead."
            )

        _refuse._cdg_banned = True
        setattr(BaseWrapper, name, _refuse)
