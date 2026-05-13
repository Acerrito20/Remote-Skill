"""Playwright adapter — Electron / Chromium apps over CDP.

Use for apps whose UIA tree is a flat blob (Slack, VS Code, Notion, Teams).
Start the target app with --remote-debugging-port=<port> before calling connect().

Uses the async Playwright API because callers run inside FastMCP's asyncio event
loop. The sync API refuses to run when the event loop is already going.
"""

from __future__ import annotations


async def connect(cdp_url: str = "http://localhost:9222"):
    """Return (playwright_instance, browser, first_page). Async."""
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(cdp_url)
    contexts = browser.contexts
    if not contexts:
        raise RuntimeError("No browser contexts found — is the app open?")
    pages = contexts[0].pages
    page = pages[0] if pages else await contexts[0].new_page()
    return pw, browser, page


async def disconnect(pw) -> None:
    try:
        await pw.stop()
    except Exception:
        pass
