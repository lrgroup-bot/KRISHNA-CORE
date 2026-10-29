"""Safe local data-location validation and non-destructive offline-style migration.

The live dashboard NEVER switches its open SQLite database in mid-request.
Migration copies and checks retained data under the single worker lock, leaves
the original untouched, and requires a manual service restart with new --data.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from contextlib import closing

from suryadev_evidence import backup_database, verify_evidence
from suryadev_lock import worker_lock
from suryadev_settings import read_settings, write_settings

MIN_FREE_BYTES = 2 * 1024 ** 3
SAFETY_BYTES = 512 * 1024 ** 2
_TRANSIENT = frozenset({
    ".worker.lock", "suryadev.sqlite3", "suryadev.sqlite3-wal",
    "suryadev.sqlite3-shm", "suryadev.sqlite3-journal",
    "worker-runtime.json", "krishna-reader-receipt.json",
})


def _inside(path, parent):
    return path == parent or parent in path.parents


def _checked_absolute(path):
    if not isinstance(path, str) or not path.strip() or len(path) > 900:
        raise ValueError("Choose a local absolute directory path")
    candidate = Path(os.path.expandvars(path.strip())).expanduser()
    if not candidate.is_absolute():
        raise ValueError("Enter an absolute path, such as E:\\SURYADEV-DATA")
    if str(candidate).startswith(("\\\\", "//")):
        raise ValueError("Network shares are not supported for active SQLite storage")
    resolved = candidate.resolve(strict=False)
    if resolved == Path(resolved.anchor):
        raise ValueError("Choose a subfolder, not the root of a drive")
    if os.name == "nt":
        protected = ("windows", "program files", "program files (x86)", "$recycle.bin",
                     "system volume information")
        parts = [p.casefold() for p in resolved.parts]
        if any(p in parts for p in protected):
            raise ValueError("System and program directories cannot store research data")
    for parent in (candidate, *candidate.parents):
        if parent.exists() and parent.is_symlink():
            raise ValueError("Symlink/reparse-point data paths are not permitted")
    return resolved


def _files(root):
    """Files beneath data root; reject symlinks to avoid copying outside it."""
    root = Path(root)
    if not root.exists():
        return
    for base, names, filenames in os.walk(root, followlinks=False):
        basepath = Path(base)
        for dirname in names:
            item = basepath / dirname
            if item.is_symlink():
                raise ValueError("Source data contains linked directory: " + dirname)
        for filename in filenames:
            item = basepath / filename
            if item.is_symlink():
                raise ValueError("Source data contains linked file: " + filename)
            if not item.is_file():
                raise ValueError("Data contains a non-regular file: " + filename)
            yield item


def size_of_data(root):
    total = 0
    count = 0
    for file in _files(root):
        if file.name not in _TRANSIENT:
            total += file.stat().st_size
            count += 1
    return total, count


def inspect_storage(source_root, requested):
    source = Path(source_root).expanduser().resolve()
    target = _checked_absolute(requested)
    if _inside(target, source) and target != source:
        raise ValueError("New data folder cannot be inside active data folder")
    if _inside(source, target) and target != source:
        raise ValueError("New data folder cannot contain the current data folder")
    install = Path(__file__).resolve().parent
    if _inside(target, install):
        raise ValueError("Choose a data folder outside the installed application directory")
    ancestor = target
    while not ancestor.exists():
        if ancestor.parent == ancestor:
            raise ValueError("Destination drive is not mounted")
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise ValueError("Destination parent is not a directory")
    disk = shutil.disk_usage(ancestor)
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".suryadev-write-check-",
                                         dir=ancestor, delete=True) as probe:
            probe.write(b"SURYDEV-WRITABLE")
            probe.flush()
        writable = True
    except OSError:
        writable = False
    current_size, files = size_of_data(source)
    required = max(MIN_FREE_BYTES, current_size + SAFETY_BYTES)
    already_active = target == source
    empty = not target.exists() or (target.is_dir() and not any(target.iterdir()))
    return {
        "path": str(target), "current_root": str(source),
        "is_active": already_active, "empty_destination": empty,
        "bytes_to_copy": current_size, "source_file_count": files,
        "free_bytes": disk.free, "total_bytes": disk.total,
        "minimum_required_bytes": required,
        "sufficient_space": disk.free >= required,
        "writable": writable,
        "ready_to_migrate": (already_active or (empty and disk.free >= required and writable)),
        "note": ("Active research data location" if already_active else
                 "Migration copies all existing data and keeps the original. "
                 "The dashboard and workers must restart using the new --data path.")
    }


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _db_counts(path):
    with closing(sqlite3.connect(path, timeout=20)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite database failed integrity check")
        return tuple(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                     for table in ("jobs", "findings", "job_provenance"))


def migrate_storage(source_root, requested):
    """Leave old location intact; require user to restart everything with new --data."""
    source = Path(source_root).expanduser().resolve()
    target = _checked_absolute(requested)
    if target == source:
        return {"active_root": str(source), "restart_required": False,
                "message": "Already using this data location."}
    # Lock prevents the mission/worker from changing the SQLite ledger mid-copy.
    with worker_lock(source):
        check = inspect_storage(source, str(target))
        if not check["ready_to_migrate"]:
            raise ValueError("Destination must be empty and have sufficient available space")
        with closing(sqlite3.connect(source / "suryadev.sqlite3", timeout=20)) as db:
            running = db.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
            if running:
                raise RuntimeError("Cannot migrate while assignments are marked running")
        old_validation = verify_evidence(source)
        if old_validation["corrupt"]:
            raise RuntimeError("Original evidence failed SHA-256 checks; migration stopped")
        source_rows = _db_counts(source / "suryadev.sqlite3")
        target.mkdir(parents=True, exist_ok=True)
        # Always back up the active SQLite database using SQLite's online backup
        # rather than copying WAL/SHM or a potentially open database directly.
        backup_database(source, target / "suryadev.sqlite3")
        copied_files = 1
        for item in _files(source):
            if item.name in _TRANSIENT:
                continue
            relative = item.relative_to(source)
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
            if _sha256(item) != _sha256(dest):
                raise RuntimeError("Migration checksum failed for " + str(relative))
            copied_files += 1
        if _db_counts(target / "suryadev.sqlite3") != source_rows:
            raise RuntimeError("Database changed during migration; restart from a new empty folder")
        dest_validation = verify_evidence(target)
        if dest_validation["corrupt"] or dest_validation["checked"] != old_validation["checked"]:
            raise RuntimeError("Evidence verification failed at destination")
        new_settings = read_settings(source)
        new_settings["pending_data_root"] = ""
        write_settings(target, new_settings)
        old_settings = read_settings(source)
        old_settings["pending_data_root"] = str(target)
        write_settings(source, old_settings)
        return {
            "active_root": str(source), "copied_to": str(target),
            "restart_required": True, "copied_files": copied_files,
            "evidence_verified": dest_validation["checked"],
            "message": ("Verified copy completed. Original data remains unchanged. "
                        "Stop the dashboard and worker, then restart both with --data "
                        "pointing to the new folder. Nothing is deleted automatically.")
        }
