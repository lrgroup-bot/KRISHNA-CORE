"""Evidence storage and consistent SQLite backup for SURYADEV."""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time

MAX_EVIDENCE_BYTES = 2_000_000

def save_evidence(root, text, *, source, kind="web"):
    payload = text.encode("utf-8")
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise ValueError("evidence exceeds 2 MB")
    digest = hashlib.sha256(payload).hexdigest()
    folder = Path(root).expanduser().resolve() / "evidence" / digest[:2]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (digest + ".txt")
    if not target.exists():
        with tempfile.NamedTemporaryFile(mode="wb", dir=folder, delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(payload)
        try:
            tmp.replace(target)
        finally:
            tmp.unlink(missing_ok=True)
    record = {
        "sha256": digest, "source": source, "kind": kind,
        "bytes": len(payload), "stored_at": time.time(),
        "path": str(target.relative_to(Path(root).expanduser().resolve()))
    }
    return record

def backup_database(root, destination):
    root = Path(root).expanduser().resolve()
    src = root / "suryadev.sqlite3"
    if not src.exists():
        raise FileNotFoundError(src)
    target = Path(destination).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target == src:
        raise ValueError("backup destination must differ from live database")
    with closing(sqlite3.connect(src, timeout=20)) as live:
        with closing(sqlite3.connect(target)) as copy:
            live.backup(copy)
            check = copy.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise RuntimeError("backup integrity check failed: " + check)
    return {"backup": str(target), "integrity": "ok"}

def verify_evidence(root):
    folder = Path(root).expanduser().resolve() / "evidence"
    total = 0
    corrupt = []
    for file in folder.glob("*/*.txt"):
        total += 1
        if hashlib.sha256(file.read_bytes()).hexdigest() != file.stem:
            corrupt.append(str(file))
    return {"checked": total, "corrupt": corrupt}
