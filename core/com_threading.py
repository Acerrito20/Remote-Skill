"""COM apartment initialization per thread.

UIA uses COM, which requires CoInitialize() on every thread that calls into it.
Decorate every tool function (and background watcher threads) with @com_thread.
"""

import threading
from functools import wraps

try:
    import pythoncom
    _PYTHONCOM = True
except ImportError:
    _PYTHONCOM = False

_local = threading.local()


def com_thread(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if _PYTHONCOM and not getattr(_local, "initialized", False):
            pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
            _local.initialized = True
        return fn(*args, **kwargs)
    return wrapper


def com_thread_async(fn):
    """Async variant for coroutines."""
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        if _PYTHONCOM and not getattr(_local, "initialized", False):
            pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
            _local.initialized = True
        return await fn(*args, **kwargs)
    return wrapper
