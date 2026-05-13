"""Tests for browser skill tools (Playwright CDP bridge).

Tools are async (production code uses Playwright's async API because FastMCP
runs them inside an asyncio event loop). Pytest-asyncio is in `asyncio_mode = "auto"`
so any `async def test_*` is auto-collected as async.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

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
    """Build a minimal Playwright *async* api mock.

    Returns (mock_async_playwright_fn, mock_browser, mock_page_list).
    """
    mock_page = MagicMock()
    mock_page.url = "about:blank"
    # async methods on a page
    mock_page.title = AsyncMock(return_value="Blank")
    mock_page.goto = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.evaluate = AsyncMock()
    mock_page.query_selector = AsyncMock()
    mock_page.screenshot = AsyncMock()
    page_list = pages if pages is not None else [mock_page]

    mock_ctx = MagicMock()
    mock_ctx.pages = page_list

    mock_browser = MagicMock()
    mock_browser.contexts = [mock_ctx]

    mock_pw_instance = MagicMock()
    # connect_over_cdp is async in the async API
    mock_pw_instance.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    # async_playwright() returns an object whose .start() is awaitable and returns
    # the playwright instance.
    mock_ctx_mgr = MagicMock()
    mock_ctx_mgr.start = AsyncMock(return_value=mock_pw_instance)

    mock_async_pw = MagicMock(return_value=mock_ctx_mgr)
    return mock_async_pw, mock_browser, page_list


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

async def test_browser_open_returns_handles():
    tools = _reg()
    mock_async_pw, mock_browser, pages = _mock_pw_stack()
    mock_playwright_module = MagicMock()
    mock_playwright_module.async_api.async_playwright = mock_async_pw
    with patch.dict(sys.modules, {
        "playwright": mock_playwright_module,
        "playwright.async_api": mock_playwright_module.async_api,
    }):
        result = await tools["browser_open"]("http://localhost:9222")
    assert "browser_handle" in result
    assert isinstance(result["pages"], list)


async def test_browser_open_error():
    tools = _reg()
    mock_async_pw = MagicMock()
    mock_ctx_mgr = MagicMock()
    # .start() returns instance whose chromium.connect_over_cdp() raises
    bad_instance = MagicMock()
    bad_instance.chromium.connect_over_cdp = AsyncMock(side_effect=Exception("refused"))
    mock_ctx_mgr.start = AsyncMock(return_value=bad_instance)
    mock_async_pw.return_value = mock_ctx_mgr
    mock_playwright_module = MagicMock()
    mock_playwright_module.async_api.async_playwright = mock_async_pw
    with patch.dict(sys.modules, {
        "playwright": mock_playwright_module,
        "playwright.async_api": mock_playwright_module.async_api,
    }):
        result = await tools["browser_open"]("http://localhost:9222")
    assert "error" in result


# ── browser_navigate ──────────────────────────────────────────────────────────

async def test_browser_navigate_stale_page():
    tools = _reg()
    result = await tools["browser_navigate"]("pg_does_not_exist", "http://example.com")
    assert result == {"error": "stale_page_handle"}


async def test_browser_navigate_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.url = "http://example.com"
    mock_page.goto = AsyncMock()
    br._PAGES["pg_test"] = mock_page
    result = await tools["browser_navigate"]("pg_test", "http://example.com")
    assert result["ok"] is True
    mock_page.goto.assert_awaited_once_with("http://example.com")


# ── browser_query ─────────────────────────────────────────────────────────────

async def test_browser_query_stale():
    tools = _reg()
    result = await tools["browser_query"]("pg_missing", "#btn")
    assert result == {"error": "stale_page_handle"}


async def test_browser_query_element_not_found():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=None)
    br._PAGES["pg_test"] = mock_page
    result = await tools["browser_query"]("pg_test", "#nonexistent")
    assert result["error"] == "element_not_found"


async def test_browser_query_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_elem = MagicMock()
    mock_elem.evaluate = AsyncMock(return_value="BUTTON")
    mock_elem.inner_text = AsyncMock(return_value="Submit")
    mock_page.query_selector = AsyncMock(return_value=mock_elem)
    br._PAGES["pg_test"] = mock_page
    result = await tools["browser_query"]("pg_test", "#submit")
    assert "element_handle" in result
    assert result["tag"] == "BUTTON"
    assert result["text"] == "Submit"


# ── browser_click ─────────────────────────────────────────────────────────────

async def test_browser_click_stale():
    tools = _reg()
    result = await tools["browser_click"]("pg_missing", "#btn")
    assert result == {"error": "stale_page_handle"}


async def test_browser_click_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.click = AsyncMock()
    br._PAGES["pg_test"] = mock_page
    result = await tools["browser_click"]("pg_test", "#submit")
    assert result == {"ok": True}
    mock_page.click.assert_awaited_once_with("#submit")


# ── browser_fill ──────────────────────────────────────────────────────────────

async def test_browser_fill_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.fill = AsyncMock()
    br._PAGES["pg_test"] = mock_page
    result = await tools["browser_fill"]("pg_test", "#email", "user@example.com")
    assert result == {"ok": True}
    mock_page.fill.assert_awaited_once_with("#email", "user@example.com")


# ── browser_eval_js ───────────────────────────────────────────────────────────

async def test_browser_eval_js_stale():
    tools = _reg()
    result = await tools["browser_eval_js"]("pg_missing", "1+1")
    assert result == {"error": "stale_page_handle"}


async def test_browser_eval_js_ok():
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=42)
    br._PAGES["pg_test"] = mock_page
    result = await tools["browser_eval_js"]("pg_test", "1 + 41")
    assert result == {"result": 42}


# ── browser_screenshot ────────────────────────────────────────────────────────

async def test_browser_screenshot_stale():
    tools = _reg()
    result = await tools["browser_screenshot"]("pg_missing")
    assert result == {"error": "stale_page_handle"}


async def test_browser_screenshot_ok(tmp_path):
    from skills import browser as br
    tools = _reg()
    mock_page = MagicMock()
    mock_page.screenshot = AsyncMock()
    br._PAGES["pg_test"] = mock_page
    out = str(tmp_path / "screen.png")
    result = await tools["browser_screenshot"]("pg_test", path=out)
    assert result["ok"] is True
    assert result["path"] == out
    mock_page.screenshot.assert_awaited_once_with(path=out)
