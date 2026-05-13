"""Tesseract OCR + OpenCV adapter — last-resort pixel reading.

Use ONLY when:
  - The target is a game, Citrix window, or custom-drawn dashboard.
  - UIA returns nothing (no tree) and there is no HWND to target.
  - This runs against a virtual display in the agent session ONLY.

Never run OCR against the user's live desktop.

Requirements:
  - Tesseract binary: winget install --id UB-Mannheim.TesseractOCR
  - Python packages:  uv pip install pytesseract opencv-python pillow

Tesseract path on Windows defaults to:
  C:\\Program Files\\Tesseract-OCR\\tesseract.exe
Set TESSERACT_EXE env var to override.
"""

from __future__ import annotations

import os
from pathlib import Path

_TESSERACT_DEFAULT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_TESSERACT_EXE = os.environ.get("TESSERACT_EXE", _TESSERACT_DEFAULT)


def _configure_pytesseract():
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_EXE
        return pytesseract
    except ImportError as exc:
        raise ImportError(
            "pytesseract not installed. Run: uv pip install pytesseract pillow"
        ) from exc


def screenshot_region(hwnd: int, x: int = 0, y: int = 0, w: int = 0, h: int = 0):
    """Capture a region of an HWND as a PIL Image.

    If w/h are 0, captures the full window client area.
    Uses PrintWindow (background-safe) — never touches the visible desktop.
    """
    try:
        import ctypes
        import ctypes.wintypes

        import win32con
        import win32gui
        import win32ui
        from PIL import Image

        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        width = w or (right - left)
        height = h or (bottom - top)

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bmp)
        ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

        bmp_info = bmp.GetInfo()
        bmp_bits = bmp.GetBitmapBits(True)
        img = Image.frombuffer(
            "RGB", (bmp_info["bmWidth"], bmp_info["bmHeight"]),
            bmp_bits, "raw", "BGRX", 0, 1,
        )

        win32gui.DeleteObject(bmp.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        if x or y:
            img = img.crop((x, y, x + width, y + height))
        return img
    except Exception as exc:
        raise RuntimeError(f"screenshot_region failed: {exc}") from exc


def ocr_hwnd(hwnd: int, lang: str = "eng") -> str:
    """Run Tesseract OCR on the full client area of an HWND.

    Returns the extracted text string.
    """
    pytesseract = _configure_pytesseract()
    img = screenshot_region(hwnd)
    return pytesseract.image_to_string(img, lang=lang)


def ocr_region(hwnd: int, x: int, y: int, w: int, h: int, lang: str = "eng") -> str:
    """Run Tesseract OCR on a specific rectangle within an HWND client area."""
    pytesseract = _configure_pytesseract()
    img = screenshot_region(hwnd, x=x, y=y, w=w, h=h)
    return pytesseract.image_to_string(img, lang=lang)


def find_text_in_hwnd(hwnd: int, text: str, lang: str = "eng") -> bool:
    """Return True if `text` appears anywhere in the HWND's rendered pixels."""
    extracted = ocr_hwnd(hwnd, lang=lang)
    return text.lower() in extracted.lower()
