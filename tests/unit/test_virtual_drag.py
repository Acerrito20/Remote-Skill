"""Unit tests for virtual_drag and drag_screen.

All Windows APIs (win32gui, win32api, win32con, ctypes.windll) are mocked so
these tests run on Linux/macOS without any Windows environment.
"""

from unittest.mock import MagicMock, call, patch


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_mcp():
    """Return a minimal MCP mock whose @tool() decorator is a passthrough."""
    mcp = MagicMock()
    mcp.tool.return_value = lambda fn: fn
    return mcp


def _make_win_handle(hwnd=1001):
    """Return a fake pywinauto wrapper with a .handle attribute."""
    win = MagicMock()
    win.handle = hwnd
    return win


# ── _sendinput_drag ────────────────────────────────────────────────────────────

def test_sendinput_drag_calls_sendinput_correct_count():
    """_sendinput_drag should call user32.SendInput once per event:
    move-to-start, mouse-down, N move steps, mouse-up = steps+3 total.
    """
    import importlib
    import skills.actions as sa

    mock_user32 = MagicMock()
    mock_user32.GetSystemMetrics.side_effect = lambda n: 1920 if n == 0 else 1080

    with patch("ctypes.windll") as mock_windll, \
         patch("time.sleep"):
        mock_windll.user32 = mock_user32
        sa._sendinput_drag((100, 200), (400, 600), duration_ms=100, steps=5)

    # move(start) + down + 5×move + up = 8 calls
    assert mock_user32.SendInput.call_count == 8


def test_sendinput_drag_first_event_is_move():
    """First SendInput call should be a MOVE (flag 0x0001) to position cursor."""
    import skills.actions as sa

    MOVE = 0x0001
    ABS = 0x8000

    mock_user32 = MagicMock()
    mock_user32.GetSystemMetrics.side_effect = lambda n: 1920 if n == 0 else 1080

    captured = []

    def fake_send(n, ptr, size):
        import ctypes
        inp = ctypes.cast(ptr, ctypes.POINTER(sa._INPUT)).contents
        captured.append(inp.mi.dwFlags)

    mock_user32.SendInput.side_effect = fake_send

    with patch("ctypes.windll") as mock_windll, patch("time.sleep"):
        mock_windll.user32 = mock_user32
        sa._sendinput_drag((0, 0), (100, 100), duration_ms=50, steps=3)

    assert captured[0] == MOVE | ABS      # first event: move to start
    assert captured[1] == 0x0002 | ABS    # second event: button down


# ── virtual_drag ──────────────────────────────────────────────────────────────

def test_virtual_drag_returns_stale_handle_when_missing():
    from skills.actions import register

    mcp = _make_mcp()
    register(mcp)

    with patch("core.handle_cache.HANDLES") as mock_handles:
        mock_handles.get.return_value = None
        result = mcp.tool.return_value.__wrapped__ if hasattr(
            mcp.tool.return_value, "__wrapped__"
        ) else None

    # Exercise through register's closure directly
    from core.handle_cache import HANDLES
    original_get = HANDLES.get
    try:
        HANDLES.get = lambda h: None
        mcp2 = _make_mcp()
        tools = {}

        def capturing_tool():
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn
            return decorator

        mcp2.tool = capturing_tool
        register(mcp2)
        result = tools["virtual_drag"]("bad_handle", 0, 0, 100, 100)
        assert result == {"error": "stale_handle"}
    finally:
        HANDLES.get = original_get


def test_virtual_drag_tier2_postmessage(tmp_path):
    """When UIA DragPattern is absent, falls back to PostMessage sequence."""
    from skills.actions import register
    from core.handle_cache import HANDLES

    win = _make_win_handle(hwnd=2002)
    # Make iface_drag raise so tier 1 is skipped
    type(win).iface_drag = property(lambda self: (_ for _ in ()).throw(Exception("no drag")))

    handle_key = "el_test001"
    original_get = HANDLES.get
    try:
        HANDLES.get = lambda h: win if h == handle_key else None

        tools: dict = {}

        def capturing_tool():
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn
            return decorator

        mcp = MagicMock()
        mcp.tool = capturing_tool
        register(mcp)

        mock_win32gui = MagicMock()
        mock_win32con = MagicMock()
        mock_win32con.WM_LBUTTONDOWN = 0x0201
        mock_win32con.WM_MOUSEMOVE = 0x0200
        mock_win32con.WM_LBUTTONUP = 0x0202
        mock_win32con.MK_LBUTTON = 0x0001
        mock_win32api = MagicMock()
        mock_win32api.MAKELONG.side_effect = lambda x, y: (y << 16) | (x & 0xFFFF)

        with patch.dict("sys.modules", {
            "win32gui": mock_win32gui,
            "win32con": mock_win32con,
            "win32api": mock_win32api,
        }), patch("time.sleep"):
            result = tools["virtual_drag"](handle_key, 0, 0, 100, 50, 200, 4)

        assert result["ok"] is True
        assert result["method"] == "postmessage_sequence"
        # down + 4 moves + up = 6 PostMessage calls
        assert mock_win32gui.PostMessage.call_count == 6
    finally:
        HANDLES.get = original_get


def test_virtual_drag_tier3_sendinput_fallback():
    """Falls through to session-scoped SendInput when PostMessage also fails."""
    from skills.actions import register
    from core.handle_cache import HANDLES

    win = _make_win_handle(hwnd=3003)
    type(win).iface_drag = property(lambda self: (_ for _ in ()).throw(Exception("no drag")))

    handle_key = "el_test002"
    original_get = HANDLES.get
    try:
        HANDLES.get = lambda h: win if h == handle_key else None

        tools: dict = {}

        def capturing_tool():
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn
            return decorator

        mcp = MagicMock()
        mcp.tool = capturing_tool
        register(mcp)

        # Make win32gui.PostMessage raise to force tier 3
        mock_win32gui = MagicMock()
        mock_win32gui.PostMessage.side_effect = OSError("fail")
        mock_win32gui.ClientToScreen.return_value = (50, 100)
        mock_win32con = MagicMock()
        mock_win32con.WM_LBUTTONDOWN = 0x0201
        mock_win32con.WM_MOUSEMOVE = 0x0200
        mock_win32con.WM_LBUTTONUP = 0x0202
        mock_win32con.MK_LBUTTON = 0x0001
        mock_win32api = MagicMock()
        mock_win32api.MAKELONG.side_effect = lambda x, y: (y << 16) | (x & 0xFFFF)

        mock_user32 = MagicMock()
        mock_user32.GetSystemMetrics.side_effect = lambda n: 1920 if n == 0 else 1080

        with patch.dict("sys.modules", {
            "win32gui": mock_win32gui,
            "win32con": mock_win32con,
            "win32api": mock_win32api,
        }), patch("ctypes.windll") as mock_windll, patch("time.sleep"):
            mock_windll.user32 = mock_user32
            result = tools["virtual_drag"](handle_key, 0, 0, 100, 50, 100, 4)

        assert result["ok"] is True
        assert result["method"] == "sendinput_session"
    finally:
        HANDLES.get = original_get


# ── drag_screen ───────────────────────────────────────────────────────────────

def test_drag_screen_returns_ok_with_coordinates():
    from skills.actions import register

    tools: dict = {}

    def capturing_tool():
        def decorator(fn):
            tools[fn.__name__] = fn
            return fn
        return decorator

    mcp = MagicMock()
    mcp.tool = capturing_tool
    register(mcp)

    mock_user32 = MagicMock()
    mock_user32.GetSystemMetrics.side_effect = lambda n: 1920 if n == 0 else 1080

    with patch("ctypes.windll") as mock_windll, patch("time.sleep"):
        mock_windll.user32 = mock_user32
        result = tools["drag_screen"](10, 20, 300, 400, 200, 5)

    assert result["ok"] is True
    assert result["method"] == "sendinput_session"
    assert result["screen_start"] == [10, 20]
    assert result["screen_end"] == [300, 400]


def test_drag_screen_returns_error_on_exception():
    from skills.actions import register

    tools: dict = {}

    def capturing_tool():
        def decorator(fn):
            tools[fn.__name__] = fn
            return fn
        return decorator

    mcp = MagicMock()
    mcp.tool = capturing_tool
    register(mcp)

    with patch("ctypes.windll") as mock_windll:
        mock_windll.user32.GetSystemMetrics.side_effect = OSError("no display")
        result = tools["drag_screen"](0, 0, 100, 100)

    assert "error" in result
