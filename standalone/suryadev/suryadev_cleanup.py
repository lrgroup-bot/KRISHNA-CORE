"""Evidence-gated automatic deletion of SURYADEV-owned temporary work copies.

Only files created under data_root/staging/jobs/<jobid>/ can be removed.
Database, evidence hashes, original PDFs/video/audio, imported transcripts,
models and user files are NEVER targeted by this cleanup routine.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

from suryadev_liveops import atomic_json
from suryadev_settings import read_settings

MAX_STAGE_BYTES = 2_000_000
MANIFEST = "manifest.json"
STAGED = "source.txt"


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(512 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_extracted_text(root, job_id, text):
    if not isinstance(job_id, int) or job_id <= 0:
        raise ValueError("A real queued job ID is required for staging")
    payload = text.encode("utf-8")
    if not payload or len(payload) > MAX_STAGE_BYTES:
        raise ValueError("Extracted working text is empty or exceeds staging limit")
    directory = Path(root).expanduser().resolve() / "staging" / "jobs" / str(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / STAGED
    if source.is_symlink() or (directory / MANIFEST).is_symlink():
        raise ValueError("Staging must not contain symbolic links")
    source.write_bytes(payload)
    manifest = {"job_id": job_id, "sha256": hashlib.sha256(payload).hexdigest(),
                "created_at": time.time(), "file": STAGED,
                "type": "suryadev_extracted_work_copy_v1"}
    (directory / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return manifest["sha256"]


def cleanup_completed(db, root, *, dry_run=False, now=None):
    """Delete only validated work-copy pairs after job success and evidence check."""
    root = Path(root).expanduser().resolve()
    now = time.time() if now is None else now
    policy = read_settings(root)["cleanup"]
    report = {"enabled": policy["enabled"], "dry_run": bool(dry_run),
              "checked_at": now, "deleted_jobs": 0, "deleted_bytes": 0,
              "eligible_jobs": 0, "eligible_bytes": 0, "skipped": 0, "errors": 0,
              "retained_evidence": True, "scope": "staging/jobs only"}
    if not policy["enabled"]:
        return report
    staging = root / "staging" / "jobs"
    if not staging.is_dir() or staging.is_symlink():
        return report
    retention = policy["retention_hours"] * 3600
    for directory in list(staging.iterdir()):
        if not directory.name.isascii() or not directory.name.isdecimal() or directory.is_symlink() or not directory.is_dir():
            report["skipped"] += 1
            continue
        try:
            job_id = int(directory.name)
            files = {entry.name for entry in directory.iterdir()}
            if files != {MANIFEST, STAGED}:
                report["skipped"] += 1
                continue
            manifest_path = directory / MANIFEST
            source_path = directory / STAGED
            if manifest_path.is_symlink() or source_path.is_symlink():
                report["skipped"] += 1
                continue
            if manifest_path.stat().st_size > 2048 or source_path.stat().st_size > MAX_STAGE_BYTES:
                report["skipped"] += 1
                continue
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            digest = data.get("sha256", "")
            if (data.get("job_id") != job_id or data.get("file") != STAGED or
                    data.get("type") != "suryadev_extracted_work_copy_v1" or
                    not isinstance(digest, str) or len(digest) != 64 or
                    any(c not in "0123456789abcdef" for c in digest)):
                report["skipped"] += 1
                continue
            if now - float(data.get("created_at", now)) < retention:
                report["skipped"] += 1
                continue
            if digest_file(source_path) != digest:
                report["skipped"] += 1
                continue
            status = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not status or status[0] != "done":
                report["skipped"] += 1
                continue
            finding = db.execute(
                "SELECT 1 FROM findings WHERE job_id=? AND sha256=? LIMIT 1",
                (job_id, digest)).fetchone()
            if finding is None:
                report["skipped"] += 1
                continue
            saved = root / "evidence" / digest[:2] / (digest + ".txt")
            if saved.is_symlink() or not saved.is_file() or digest_file(saved) != digest:
                report["skipped"] += 1
                continue
            report["eligible_jobs"] += 1
            report["eligible_bytes"] += source_path.stat().st_size
            if not dry_run:
                size = source_path.stat().st_size
                source_path.unlink()
                manifest_path.unlink()
                directory.rmdir()
                report["deleted_jobs"] += 1
                report["deleted_bytes"] += size
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            report["errors"] += 1
            continue
    if not dry_run:
        atomic_json(root, "cleanup-status.json", report)
    return report
