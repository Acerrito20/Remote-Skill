"""Tests for browser skill tools (Playwright CDP bridge)."""

import sys
from unittest.mock import MagicMock, patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _reg():
    tools = {}
    class MCP:
        def tool(self):
            def d(fn): tools[fn.__name__] = fn; return fn
            return d
    from skills.browser import register
    register(MCP())
    return tools


def _mock_pw_stack(pages=None):
    """Build a minimal playwright sync_api mock.

    Returns (mock_sync_playwright_fn, mock_browser, mock_page_list).
    """
    mock_page = MagicMock()
    mock_page.url = "about:blank"
    mock_page.title.return_value = "Blank"
    page_list = pages if pages is not None else [mock_page]

    mock_ctx = MagicMock()
    mock_ctx.pages = page_list

    mock_browser = MagicMock()
    mock_browser.contexts = [mock_ctx]

    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium.connect_over_cdp.return_value = mock_browser

    mock_sync_pw = MagicMock()
    mock_sync_pw.return_value.__enter__ = MagicMock(return_value=mock_pw_instance)
    mock_sync_pw.return_value.__exit__ = MagicMock(return_value=False)

    # sync_playwright() returns a context manager; .start() returns the instance
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.start.return_value = mock_pw_instance

    mock_sync_pw.return_value = mock_ctx_mgr

    return mock_sync_pw, mock_browser, page_list


@pytest.fixture(autouse=True)
def clear_browser_state():
    """Isolate module-level _PAGES and _BROWSERS between tests."""
    from skills import browser as br
    br._PAGES.clear()
    br._BROWSERS.clear()
    yield
    br._PAGES.clear()
    br._BROWSERS.clear()


# ── browser_open ──────────────────────────────────────────────────────────────

def test_browser_open_returns_handles():
    tools = _reg()
    mock_sync_pw, mock_browser, pages = _mock_pw_stack()
    mock_playwright_module = MagicMock()
    mock_playwright_module.sync_api.sync_playwright = mock_sync_pw
    with patch.dict(sys.modules, {
        "playwright": mock_playwright_module,
        "playwright.sync_api": mock_playwright_module.sync_api,
    }):
        result = tools["browser_open"]("http://localhost:9222")
    assert "browser_handle" in result
    assert isinstance(result["pages"], list)


def test_browser_open_error():
    tools = _reg()
    mock_sync_pw = MagicMock()
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.start.return_value.chromium.connect_over_cdp.side_effect = Exception("refused")
    mock_sync_pw.return_value = mock_ctx_mgr
    mock_playwright_module = MagicMock()
    mock_playwright_module.sync_api.sync_playwright = mock_sync_pw
    with patch.dict(sys.modules, {
        "playwright": mock_playwright_module,
        "playwright.sync_api": mock_playwright_module.sync_api,
    }):
        result = tools["browser_open"]("http://localhost:9222")
    assert "error" in result


# ── browser_navigate ──────────────────────────────────────────────────────────

def test_browser_navigate_stale_page():
    tools = _reg()
    result = tools["browser_navigate"]("pg_does_not_exist", "http://example.com")
    assert result == {"error": "stale_page_handle"}


def test_browser_navigate_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.url = "http://example.com"
    br._PAGES["pg_test"] = mock_page
    result = tools["browser_navigate"]("pg_test", "http://example.com")
    assert result["ok"] is True
    mock_page.goto.assert_called_once_with("http://example.com")


# ── browser_query ─────────────────────────────────────────────────────────────

def test_browser_query_stale():
    tools = _reg()
    result = tools["browser_query"]("pg_missing", "#btn")
    assert result == {"error": "stale_page_handle"}


def test_browser_query_element_not_found():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.query_selector.return_value = None
    br._PAGES["pg_test"] = mock_page
    result = tools["browser_query"]("pg_test", "#nonexistent")
    assert result["error"] == "element_not_found"


def test_browser_query_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_elem = MagicMock()
    mock_elem.evaluate.return_value = "BUTTON"
    mock_elem.inner_text.return_value = "Submit"
    mock_page.query_selector.return_value = mock_elem
    br._PAGES["pg_test"] = mock_page
    result = tools["browser_query"]("pg_test", "#submit")
    assert "element_handle" in result
    assert result["tag"] == "BUTTON"
    assert result["text"] == "Submit"


# ── browser_click ─────────────────────────────────────────────────────────────

def test_browser_click_stale():
    tools = _reg()
    result = tools["browser_click"]("pg_missing", "#btn")
    assert result == {"error": "stale_page_handle"}


def test_browser_click_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    br._PAGES["pg_test"] = mock_page
    result = tools["browser_click"]("pg_test", "#submit")
    assert result == {"ok": True}
    mock_page.click.assert_called_once_with("#submit")


# ── browser_fill ──────────────────────────────────────────────────────────────

def test_browser_fill_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    br._PAGES["pg_test"] = mock_page
    result = tools["browser_fill"]("pg_test", "#email", "user@example.com")
    assert result == {"ok": True}
    mock_page.fill.assert_called_once_with("#email", "user@example.com")


# ── browser_eval_js ───────────────────────────────────────────────────────────

def test_browser_eval_js_stale():
    tools = _reg()
    result = tools["browser_eval_js"]("pg_missing", "1+1")
    assert result == {"error": "stale_page_handle"}


def test_browser_eval_js_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.evaluate.return_value = 42
    br._PAGES["pg_test"] = mock_page
    result = tools["browser_eval_js"]("pg_test", "1 + 41")
    assert result == {"result": 42}


# ── browser_screenshot ────────────────────────────────────────────────────────

def test_browser_screenshot_stale():
    tools = _reg()
    result = tools["browser_screenshot"]("pg_missing")
    assert result == {"error": "stale_page_handle"}


def test_browser_screenshot_ok(tmp_path):
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    br._PAGES["pg_test"] = mock_page
    out = str(tmp_path / "screen.png")
    result = tools["browser_screenshot"]("pg_test", path=out)
    assert result["ok"] is True
    assert result["path"] == out
    mock_page.screenshot.assert_called_once_with(path=out)
