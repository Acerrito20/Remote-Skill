import json
import tempfile
from pathlib import Path

from core.audit import AuditLog


def test_record_and_read(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.record("invoke", {"element_handle": "el_abc"}, {"ok": True}, 12.5, "test-session")
    entries = log.read_all()
    assert len(entries) == 1
    e = entries[0]
    assert e["tool"] == "invoke"
    assert e["result"] == {"ok": True}
    assert e["duration_ms"] == 12.5
    assert e["session_id"] == "test-session"
    assert "ts" in e


def test_multiple_records(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    for i in range(10):
        log.record(f"tool_{i}", {}, {"ok": True}, float(i), "s")
    entries = log.read_all()
    assert len(entries) == 10
    assert entries[0]["tool"] == "tool_0"
    assert entries[9]["tool"] == "tool_9"


def test_empty_log_returns_empty_list(tmp_path):
    log = AuditLog(tmp_path / "nonexistent.jsonl")
    assert log.read_all() == []


def test_invalid_json_lines_skipped(tmp_path):
    p = tmp_path / "audit.jsonl"
    p.write_text('{"tool": "ok"}\n{bad json}\n{"tool": "also_ok"}\n')
    log = AuditLog(p)
    entries = log.read_all()
    assert len(entries) == 2
    assert entries[0]["tool"] == "ok"
    assert entries[1]["tool"] == "also_ok"


def test_creates_parent_dirs(tmp_path):
    log = AuditLog(tmp_path / "deep" / "nested" / "audit.jsonl")
    log.record("test", {}, {}, 0.0)
    assert (tmp_path / "deep" / "nested" / "audit.jsonl").exists()
