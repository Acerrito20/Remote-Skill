"""Retry / backoff wrapper for transient COM and UIA errors."""

import time
from functools import wraps
from typing import Callable, Type


def with_retry(
    fn: Callable | None = None,
    *,
    max_attempts: int = 3,
    base_delay: float = 0.1,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator with exponential backoff.

    Usage:
        @with_retry
        def my_fn(): ...

        @with_retry(max_attempts=5, base_delay=0.2)
        def my_fn(): ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return f(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        time.sleep(base_delay * (2 ** attempt))
            raise last_exc
        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator
