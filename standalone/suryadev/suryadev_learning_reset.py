"""Archive-and-reset the entire standalone SURYADEV learning workspace.

Deliberately destructive to the ACTIVE workspace, but preserves the prior bytes
as a same-volume dated archive. Never called during ordinary app startup.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket

from suryadev_lock import worker_lock

CONFIRMATION = "CLEAR-ALL-SURYADEV-LEARNING"
MARKER = "suryadev.fresh-workspace.v1"
LIVE_PORTS = (8872, 8772, 8769)


def _assert_stopped(data: Path) -> None:
    # The dashboard does not hold the worker lock. Verify both.
    for port in LIVE_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(
                    "A local dashboard is listening on port %d; close SURYADEV first" % port)
    with worker_lock(data):
        pass
    # Fail closed when psutil sees any SURYADEV process still using this root.
    try:
        import psutil
    except ImportError:
        return
    needle = os.path.normcase(str(data))
    current_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            if proc.info["pid"] == current_pid:
                continue
            argv = proc.info.get("cmdline") or []
            command = os.path.normcase(" ".join(argv))
            if needle in command and (
                "suryadev" in command or "surydev" in command):
                raise RuntimeError(
                    "An existing SURYADEV process still uses this data directory; "
                    "stop PID %d first" % proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            # Existing worker lock and port protection still apply.
            continue


def archive_and_reset(data: Path, *, confirm: str, inspect_ports: bool = True) -> dict:
    if confirm != CONFIRMATION:
        raise ValueError("Explicit --confirm %s is required" % CONFIRMATION)
    data = Path(data).expanduser().absolute()
    if data.is_symlink() or not data.is_dir():
        raise ValueError("Existing non-symlink SURYADEV data directory required")
    if data.name in (".", "..") or data.parent == data:
        raise ValueError("Unsafe data directory")
    marker = data / "fresh-workspace.json"
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 4096:
        raise ValueError("Refusing reset of an unmarked or unsafe data directory")
    try:
        previous = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError("Malformed fresh-workspace marker") from exc
    if previous.get("schema") != MARKER:
        raise ValueError("Refusing reset of an unrecognized data directory")
    if inspect_ports:
        _assert_stopped(data)
    else:
        # Test-only control; still enforce exclusive single worker lock.
        with worker_lock(data):
            pass

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    archive = data.with_name(data.name + "-learning-archive-" +
                             stamp + "-" + secrets.token_hex(3))
    # Same-parent rename is atomic on the same volume. No automatic deletion.
    data.rename(archive)
    try:
        data.mkdir()
        fresh = {
            "schema": MARKER,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active_task_limit": 3,
            "auto_start": True,
            "node_profile": "fleet_adaptive",
            "mission_rest_policy": "continuous",
            "trial_model": "qwen3.5:2b",
            "note": "Fresh EMPTY workspace. Archived records were not imported.",
        }
        (data / "fresh-workspace.json").write_text(
            json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        # Never silently lose the archived learning if creating the new root fails.
        if data.is_dir() and not any(data.iterdir()):
            data.rmdir()
        if not data.exists():
            archive.rename(data)
        raise
    return {
        "ok": True,
        "active_learning_reset": True,
        "new_data_root": str(data),
        "archive": str(archive),
        "archived_learning_deleted": False,
        "old_book_progress_carried_over": False,
        "old_video_attempts_carried_over": False,
        "approvals_carried_over": False,
        "requires_new_approved_sources": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Archive-and-reset SURYADEV study history")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--confirm", default="")
    args = parser.parse_args(argv)
    try:
        result = archive_and_reset(args.data, confirm=args.confirm)
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, "RESET REFUSED: %s: %s\n" %
                    (type(exc).__name__, str(exc)))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
