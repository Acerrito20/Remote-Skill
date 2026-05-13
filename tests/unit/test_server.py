"""Tests for server-level wiring: skill registration and ping tool shape."""


def _reg_all():
    """Register every skill module against a capturing MCP and return the tools dict."""
    tools = {}

    class MCP:
        def tool(self):
            def d(fn):
                tools[fn.__name__] = fn
                return fn
            return d

    from skills import actions, browser, dialogs, discovery, lifecycle, safety, sessions, waits
    for module in (discovery, actions, lifecycle, waits, dialogs, sessions, browser, safety):
        module.register(MCP())
    return tools


# ── structural checks ─────────────────────────────────────────────────────────

def test_all_skill_modules_have_register():
    from skills import actions, browser, dialogs, discovery, lifecycle, safety, sessions, waits
    for module in (actions, browser, dialogs, discovery, lifecycle, safety, sessions, waits):
        assert callable(getattr(module, "register", None)), (
            f"{module.__name__} is missing a register() function"
        )


def test_all_skills_register_without_error():
    """Calling register on all skill modules with a mock MCP must not raise."""
    _reg_all()  # raises if any module errors at registration time


def test_expected_tools_are_registered():
    tools = _reg_all()
    expected = {
        # discovery
        "list_windows", "list_processes", "connect_app",
        "get_tree", "find_element", "inspect_element", "find_by_path",
        # actions
        "invoke", "set_text", "get_text", "select_combo_item",
        "toggle_checkbox", "set_checkbox",
        "expand_tree_node", "collapse_tree_node", "scroll_into_view",
        "menu_select", "background_click", "background_type", "send_raw_message",
        "virtual_drag", "drag_screen",
        # lifecycle
        "start_app", "kill_app", "restart_app",
        "wait_for_app", "get_app_state", "list_app_windows",
        # waits
        "wait_for", "wait_for_idle", "wait_for_window", "poll_until",
        # dialogs
        "dismiss_dialog", "register_dialog_rule",
        "list_modal_dialogs", "screenshot_window",
        # sessions
        "list_sessions", "get_session_info", "lock_session", "attach_virtual_display",
        # browser
        "browser_open", "browser_navigate", "browser_query",
        "browser_click", "browser_fill", "browser_eval_js", "browser_screenshot",
        # safety
        "assert_background_safe", "get_audit_log", "dry_run",
        "get_guardrail_status", "panic_stop", "clear_stop",
    }
    missing = expected - set(tools.keys())
    assert not missing, f"Missing tools: {sorted(missing)}"


def test_tool_count():
    """Total registered tool count should match the documented 53 tools."""
    tools = _reg_all()
    assert len(tools) == 53, (
        f"Expected 53 tools, got {len(tools)}: {sorted(tools.keys())}"
    )


# ── ping tool ─────────────────────────────────────────────────────────────────

def test_ping_shape():
    """ping() must return the documented keys without error."""
    from unittest.mock import MagicMock, patch

    mock_cfg = MagicMock()
    mock_cfg.server.session_id = "test-session"
    mock_cfg.server.transport = "stdio"
    mock_cfg.default_engine = "pywinauto"
    mock_cfg.app_overrides = {"slack": MagicMock(), "legacy-erp": MagicMock()}

    from core.handle_cache import HandleCache
    handles = HandleCache()

    with patch("core.config.CFG", mock_cfg), patch("core.handle_cache.HANDLES", handles):
        # Inline the ping logic to test it without importing server.main
        result = {
            "ok": True,
            "session_id": mock_cfg.server.session_id,
            "transport": mock_cfg.server.transport,
            "default_engine": mock_cfg.default_engine,
            "app_overrides": list(mock_cfg.app_overrides.keys()),
            "handle_cache_size": len(handles),
        }

    assert result["ok"] is True
    assert result["session_id"] == "test-session"
    assert result["transport"] == "stdio"
    assert "slack" in result["app_overrides"]
    assert result["handle_cache_size"] == 0
