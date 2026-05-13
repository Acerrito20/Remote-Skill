"""Tests for the COM threading decorator.

pythoncom is Windows-only, so these tests mock it to run on any OS.
"""

import threading
from unittest.mock import MagicMock, patch


def test_com_thread_calls_through():
    """Decorated function still executes and returns its value."""
    from core.com_threading import com_thread

    @com_thread
    def fn(x):
        return x * 2

    assert fn(21) == 42


def test_com_thread_initializes_com_once(monkeypatch):
    """CoInitializeEx is called on first invocation but not on subsequent ones."""
    mock_pythoncom = MagicMock()
    mock_pythoncom.COINIT_MULTITHREADED = 0

    with patch.dict("sys.modules", {"pythoncom": mock_pythoncom}):
        # Re-import with the mock in place.
        import importlib
        import core.com_threading as ct
        importlib.reload(ct)

        calls = []

        @ct.com_thread
        def fn():
            calls.append(1)

        fn()
        fn()
        fn()

    # Called three times but CoInitializeEx should only fire once per thread.
    assert len(calls) == 3
    assert mock_pythoncom.CoInitializeEx.call_count == 1


def test_com_thread_initializes_per_thread(monkeypatch):
    """Each new thread gets its own CoInitializeEx call."""
    mock_pythoncom = MagicMock()
    mock_pythoncom.COINIT_MULTITHREADED = 0
    init_counts = []

    def fake_init(flag):
        init_counts.append(threading.current_thread().ident)

    mock_pythoncom.CoInitializeEx.side_effect = fake_init

    with patch.dict("sys.modules", {"pythoncom": mock_pythoncom}):
        import importlib
        import core.com_threading as ct
        importlib.reload(ct)

        @ct.com_thread
        def fn():
            pass

        threads = [threading.Thread(target=fn) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # One CoInitializeEx per thread.
    assert len(set(init_counts)) == 3


def test_com_thread_works_without_pythoncom():
    """If pythoncom is not installed, the decorator is a no-op (doesn't crash)."""
    import sys
    original = sys.modules.pop("pythoncom", None)
    try:
        import importlib
        import core.com_threading as ct
        importlib.reload(ct)

        @ct.com_thread
        def fn(v):
            return v + 1

        assert fn(4) == 5
    finally:
        if original is not None:
            sys.modules["pythoncom"] = original
        import importlib
        import core.com_threading as ct
        importlib.reload(ct)
