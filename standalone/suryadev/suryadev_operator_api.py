"""Local UI API handlers for KRISHNA candidate and SURYADEV storage settings.

Invoked only by the loopback dashboard after same-origin CSRF checks.
"""
from __future__ import annotations

import os
from pathlib import Path
import time

from suryadev_settings import read_settings, write_settings, save_core, diagnose_core
from suryadev_storage import inspect_storage, migrate_storage
from suryadev_cleanup import cleanup_completed
from suryadev_liveops import _safe_read
from suryadev import Library


def settings_snapshot(root):
    root = Path(root).resolve()
    settings = read_settings(root)
    try:
        storage = inspect_storage(root, str(root))
    except (OSError, ValueError) as exc:
        storage = {"path": str(root), "sufficient_space": False,
                   "error": type(exc).__name__ + ": " + str(exc)[:180]}
    return {
        "server": settings["server"],
        "paired": False,
        "server_status": "candidate_not_authenticated",
        "storage": storage,
        "active_data_root": str(root),
        "pending_data_root": settings.get("pending_data_root") or None,
        "cleanup": settings["cleanup"],
        "last_cleanup": _safe_read(root, "cleanup-status.json"),
        "note": "Core health is not authenticated pairing; research evidence is never automatically deleted.",
    }


def browse_local_directory(root):
    """Native picker runs only on the laptop when explicitly pressed in UI."""
    if os.name != "nt":
        raise RuntimeError("Native directory browsing is available on desktop Windows only")
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError("Python Tk support unavailable; type the Windows folder path") from exc
    window = tkinter.Tk()
    window.withdraw()
    try:
        window.attributes("-topmost", True)
        selection = filedialog.askdirectory(
            parent=window, initialdir=str(Path(root).resolve()),
            title="Choose SURYADEV research data destination",
            mustexist=True)
        return {"selected_path": selection or None,
                "note": "Folder selected only, not migrated or activated."}
    finally:
        window.destroy()


def handle_operator_action(root, path, body):
    if not isinstance(body, dict):
        raise ValueError("JSON object required")
    if path == "/api/operator/pairing/request":
        from suryadev_pairing_bootstrap import request_pairing
        return request_pairing(root, body.get("endpoint"), body.get("cert_sha256"),
                               body.get("device_id"))
    if path == "/api/operator/pairing/activate":
        from suryadev_pairing_bootstrap import activate_pairing
        return activate_pairing(root)
    if path == "/api/operator/server/save":
        return save_core(root, body.get("ip"), body.get("port", 8766))
    if path == "/api/operator/server/diagnose":
        ip = body.get("ip")
        port = body.get("port", 8766)
        if not ip:
            server = read_settings(root)["server"]
            ip, port = server["ip"], server["port"]
        return diagnose_core(ip, port)
    if path == "/api/operator/storage/browse":
        return browse_local_directory(root)
    if path == "/api/operator/storage/check":
        return inspect_storage(root, body.get("path"))
    if path == "/api/operator/storage/migrate":
        if body.get("confirm") != "MIGRATE":
            raise ValueError("Explicit migration confirmation required")
        return migrate_storage(root, body.get("path"))
    if path == "/api/operator/cleanup/save":
        enabled = body.get("enabled")
        hours = body.get("retention_hours")
        if not isinstance(enabled, bool):
            raise ValueError("Automatic cleanup enabled must be true or false")
        if type(hours) is not int or not 0 <= hours <= 168:
            raise ValueError("Retention must be a whole number between 0 and 168 hours")
        config = read_settings(root)
        config["cleanup"] = {"enabled": enabled, "retention_hours": hours}
        write_settings(root, config)
        return {"cleanup": config["cleanup"], "message":
                "Policy saved. Only disposable staged work copies are eligible for deletion."}
    if path == "/api/operator/cleanup/run":
        if not isinstance(body.get("dry_run"), bool):
            raise ValueError("Specify whether cleanup is a dry run")
        lib = Library(root)
        try:
            return cleanup_completed(lib.db, root, dry_run=body["dry_run"])
        finally:
            lib.db.close()
    raise ValueError("Unsupported configuration action")
