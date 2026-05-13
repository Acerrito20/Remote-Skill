"""WinAppDriver adapter — WebDriver protocol for Windows apps.

Use when:
  - The team already has WebDriver/Selenium test infrastructure to reuse.
  - The app has good Accessibility IDs but pywinauto is misbehaving.

Note: WinAppDriver is slower than pywinauto for fast-loop automation.
      Prefer pywinauto unless you have a specific reason to use this.

Requirements:
  - WinAppDriver MSI: https://github.com/microsoft/WinAppDriver/releases
  - Python packages: uv pip install Appium-Python-Client
  - Start WinAppDriver.exe on port 4723 before calling connect().
"""

from __future__ import annotations

import os

_WINAPPDRIVER_URL = os.environ.get("WINAPPDRIVER_URL", "http://localhost:4723")


def connect(app_path: str, extra_caps: dict | None = None):
    """Launch an app under WinAppDriver and return the driver.

    Args:
        app_path: Full path to the executable, or 'Root' for the desktop root.
        extra_caps: Additional Appium desired capabilities to merge in.

    Returns:
        appium.webdriver.Remote driver instance.
    """
    try:
        from appium import webdriver
    except ImportError as exc:
        raise ImportError(
            "Appium-Python-Client not installed. Run: uv pip install Appium-Python-Client"
        ) from exc

    caps = {
        "app": app_path,
        "platformName": "Windows",
        "deviceName": "WindowsPC",
    }
    if extra_caps:
        caps.update(extra_caps)
    return webdriver.Remote(_WINAPPDRIVER_URL, caps)


def connect_to_desktop():
    """Connect to the Windows desktop root (useful for finding already-open windows)."""
    return connect("Root")


def find_and_click(driver, name: str) -> None:
    """Find an element by name and click it (background-safe via WebDriver)."""
    elem = driver.find_element_by_name(name)
    elem.click()


def find_and_type(driver, name: str, text: str) -> None:
    """Find an element by name and send keys to it."""
    elem = driver.find_element_by_name(name)
    elem.send_keys(text)
