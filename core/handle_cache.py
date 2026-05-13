"""Element handle cache.

Maps opaque handle strings to live pywinauto/UIA wrappers.
Handles are UUIDs; COM pointers never cross the MCP boundary.
Entries expire after `ttl` seconds (default 5 minutes).
"""

import threading
import time
import uuid


class HandleCache:
    def __init__(self, ttl: float = 300.0):
        self._d: dict[str, tuple[object, float]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl

    def register(self, obj: object) -> str:
        handle = f"el_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._d[handle] = (obj, time.monotonic())
        return handle

    def get(self, handle: str) -> object | None:
        with self._lock:
            entry = self._d.get(handle)
            if entry is None:
                return None
            obj, ts = entry
            if time.monotonic() - ts > self._ttl:
                del self._d[handle]
                return None
            # Refresh TTL on access.
            self._d[handle] = (obj, time.monotonic())
            return obj

    def remove(self, handle: str) -> None:
        with self._lock:
            self._d.pop(handle, None)

    def purge_expired(self) -> int:
        now = time.monotonic()
        with self._lock:
            expired = [h for h, (_, ts) in self._d.items() if now - ts > self._ttl]
            for h in expired:
                del self._d[h]
        return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._d.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._d)


HANDLES = HandleCache()
