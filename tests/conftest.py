"""Shared pytest fixtures for integration tests.

Unit tests (tests/unit/) don't use these — they're self-contained.
Integration tests (tests/integration/) get Windows process management for free.
"""

import platform
import subprocess
import time

import pytest


def _kill_quietly(proc):
    try:
        proc.kill()
        proc.wait(timeout=5)
    except Exception:
        pass


@pytest.fixture
def notepad_pid():
    """Launch Notepad, yield its PID, kill it on teardown (even on failure)."""
    if platform.system() != "Windows":
        pytest.skip("Windows-only fixture")
    proc = subprocess.Popen(["notepad.exe"])
    time.sleep(0.8)
    yield proc.pid
    _kill_quietly(proc)


@pytest.fixture
def calc_pid():
    """Launch Calculator, yield its PID, kill it on teardown."""
    if platform.system() != "Windows":
        pytest.skip("Windows-only fixture")
    proc = subprocess.Popen(["calc.exe"])
    time.sleep(1.2)
    yield proc.pid
    _kill_quietly(proc)


@pytest.fixture
def tmp_audit_log(tmp_path):
    """A fresh AuditLog backed by a temp file."""
    from core.audit import AuditLog
    return AuditLog(tmp_path / "test-audit.jsonl")


@pytest.fixture
def fresh_handle_cache():
    """A fresh HandleCache with default TTL."""
    from core.handle_cache import HandleCache
    return HandleCache()
