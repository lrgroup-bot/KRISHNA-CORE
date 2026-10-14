"""Append-only JSONL audit helper; caller must control filesystem permissions."""
import json
from datetime import datetime, timezone
from pathlib import Path

def append_event(path: str, *, project: str, actor: str, action: str, allowed: bool) -> None:
    if not project or not actor or not action:
        raise ValueError("Audit event requires project, actor and action")
    record = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "project": project, "actor": actor, "action": action, "allowed": bool(allowed)}
    target = Path(path)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
