import time

import pytest

from core.handle_cache import HandleCache


def test_register_and_get():
    cache = HandleCache(ttl=60)
    obj = object()
    handle = cache.register(obj)
    assert handle.startswith("el_")
    assert cache.get(handle) is obj


def test_stale_handle_returns_none():
    cache = HandleCache(ttl=60)
    assert cache.get("el_nonexistent") is None


def test_expired_entry_returns_none():
    cache = HandleCache(ttl=0.01)
    obj = object()
    handle = cache.register(obj)
    time.sleep(0.05)
    assert cache.get(handle) is None


def test_remove():
    cache = HandleCache()
    obj = object()
    handle = cache.register(obj)
    cache.remove(handle)
    assert cache.get(handle) is None


def test_purge_expired():
    cache = HandleCache(ttl=0.01)
    for _ in range(5):
        cache.register(object())
    time.sleep(0.05)
    purged = cache.purge_expired()
    assert purged == 5
    assert len(cache) == 0


def test_len():
    cache = HandleCache()
    assert len(cache) == 0
    cache.register(object())
    cache.register(object())
    assert len(cache) == 2


def test_access_refreshes_ttl():
    cache = HandleCache(ttl=0.1)
    obj = object()
    handle = cache.register(obj)
    time.sleep(0.07)
    # Access refreshes TTL.
    assert cache.get(handle) is obj
    time.sleep(0.07)
    # Should still be alive because TTL was refreshed.
    assert cache.get(handle) is obj


def test_clear():
    cache = HandleCache()
    for _ in range(3):
        cache.register(object())
    cache.clear()
    assert len(cache) == 0
