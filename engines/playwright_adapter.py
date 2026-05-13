"""Playwright adapter — Electron / Chromium apps over CDP.

Use for apps whose UIA tree is a flat blob (Slack, VS Code, Notion, Teams).
Start the target app with --remote-debugging-port=<port> before calling connect().
"""

from __future__ import annotations


def connect(cdp_url: str = "http://localhost:9222"):
    """Return (playwright_instance, browser, first_page)."""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(cdp_url)
    contexts = browser.contexts
    if not contexts:
        raise RuntimeError("No browser contexts found — is the app open?")
    pages = contexts[0].pages
    page = pages[0] if pages else contexts[0].new_page()
    return pw, browser, page


def disconnect(pw) -> None:
    try:
        pw.stop()
    except Exception:
        pass
