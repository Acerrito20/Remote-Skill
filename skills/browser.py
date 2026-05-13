"""Browser-fallback skills — Playwright bridge for Electron / Chromium apps.

When the target app is an Electron app (Slack, VS Code, Discord, Notion, Teams),
the UIA tree is a useless flat blob. Route to Playwright over CDP instead.

Start the Electron app with remote debugging enabled:
    slack.exe --remote-debugging-port=9222

The per-app engine config (config/app_overrides/*.toml) maps executable names
to this bridge automatically.
"""

from __future__ import annotations

import uuid
from typing import Any

_PAGES: dict[str, Any] = {}    # page_handle -> Playwright page
_BROWSERS: dict[str, Any] = {} # browser_handle -> Playwright browser


def register(mcp) -> None:

    @mcp.tool()
    def browser_open(cdp_url: str = "http://localhost:9222") -> dict:
        """Connect to an existing Chromium/Electron app over CDP.

        The app must have been started with --remote-debugging-port=<port>.
        Returns a browser_handle for subsequent browser_* tools.
        """
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.connect_over_cdp(cdp_url)
            handle = f"br_{uuid.uuid4().hex[:8]}"
            _BROWSERS[handle] = (pw, browser)
            pages = []
            for ctx in browser.contexts:
                for page in ctx.pages:
                    ph = f"pg_{uuid.uuid4().hex[:8]}"
                    _PAGES[ph] = page
                    pages.append({"page_handle": ph, "url": page.url, "title": page.title()})
            return {"browser_handle": handle, "pages": pages}
        except Exception as exc:
            return {"error": str(exc), "type": type(exc).__name__}

    @mcp.tool()
    def browser_navigate(page_handle: str, url: str) -> dict:
        """Navigate a page to a URL."""
        page = _PAGES.get(page_handle)
        if page is None:
            return {"error": "stale_page_handle"}
        try:
            page.goto(url)
            return {"ok": True, "url": page.url}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def browser_query(page_handle: str, selector: str) -> dict:
        """Locate an element by CSS or XPath selector. Returns an element handle."""
        page = _PAGES.get(page_handle)
        if page is None:
            return {"error": "stale_page_handle"}
        try:
            elem = page.query_selector(selector)
            if elem is None:
                return {"error": "element_not_found", "selector": selector}
            eh = f"pg_el_{uuid.uuid4().hex[:8]}"
            _PAGES[eh] = elem  # reuse dict for elem refs
            return {
                "element_handle": eh,
                "tag": elem.evaluate("el => el.tagName"),
                "text": elem.inner_text()[:200],
            }
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def browser_click(page_handle: str, selector: str) -> dict:
        """Click an element by CSS/XPath selector via CDP (background-safe)."""
        page = _PAGES.get(page_handle)
        if page is None:
            return {"error": "stale_page_handle"}
        try:
            page.click(selector)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def browser_fill(page_handle: str, selector: str, value: str) -> dict:
        """Fill an input field by CSS/XPath selector."""
        page = _PAGES.get(page_handle)
        if page is None:
            return {"error": "stale_page_handle"}
        try:
            page.fill(selector, value)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def browser_eval_js(page_handle: str, expression: str) -> dict:
        """Execute JavaScript in the page context and return the result."""
        page = _PAGES.get(page_handle)
        if page is None:
            return {"error": "stale_page_handle"}
        try:
            result = page.evaluate(expression)
            return {"result": result}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def browser_screenshot(page_handle: str, path: str = "") -> dict:
        """Capture the page or an element as PNG. For diagnostics only."""
        page = _PAGES.get(page_handle)
        if page is None:
            return {"error": "stale_page_handle"}
        try:
            import tempfile
            from pathlib import Path
            out = path or str(Path(tempfile.mktemp(suffix=".png")))
            page.screenshot(path=out)
            return {"ok": True, "path": out}
        except Exception as exc:
            return {"error": str(exc)}
