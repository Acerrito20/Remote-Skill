"""Append-only audit log of every agent action.

Written as JSON Lines to disk. Never rotated, never deleted.
"""

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


class AuditLog:
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self,
        tool: str,
        args: dict,
        result: dict,
        duration_ms: float,
        session_id: str = "",
    ) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "args": args,
            "result": result,
            "duration_ms": round(duration_ms, 1),
            "session_id": session_id,
        }
        line = json.dumps(entry, default=str)
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        entries = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries


_DEFAULT_PATH = Path(os.environ.get("CDG_AUDIT_LOG", "logs/audit.jsonl"))
AUDIT = AuditLog(_DEFAULT_PATH)
