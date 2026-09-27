#!/usr/bin/env python3
from __future__ import annotations

"""Paired private-network sync client for SURYDEV external learning nodes.

The client keeps a lightweight heartbeat to the KRISHNA server, uploads only validated
learning-bundle.json files, verifies the server receipt hash, then asks the local
SURYDEV worker to purge transient data. It never uploads raw video/audio recordings.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib import request, error


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path, default=None):
    path = Path(path)
    if not path.is_file():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def _node_config(root, server=None, node_name=None):
    root = Path(root).resolve()
    path = root / "sync-node.json"
    row = _load_json(path, {})
    if not row:
        row = {
            "schema": "krishna.suryadev.sync-node.v1",
            "device_id": "suryadev-" + secrets.token_hex(10),
            "node_name": node_name or ("SURYDEV " + socket.gethostname()),
            "credential": secrets.token_urlsafe(48),
            "server": server or "",
            "created_at": time.time(),
        }
        _atomic_json(path, row)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    changed = False
    if server and row.get("server") != server:
        row["server"] = str(server).rstrip("/")
        changed = True
    if node_name and row.get("node_name") != node_name:
        row["node_name"] = node_name
        changed = True
    if changed:
        _atomic_json(path, row)
    return row


def _post(config, path, payload, authenticated=True, timeout=20):
    base = str(config.get("server") or "").rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise RuntimeError("trusted KRISHNA server URL is not configured")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = request.Request(base + path, data=raw, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if authenticated:
        req.add_header("X-Krishna-Device", str(config["device_id"]))
        req.add_header("Authorization", "Device " + str(config["credential"]))
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            return response.status, json.loads(body.decode("utf-8") or "{}")
    except error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            body = {"error": str(exc)}
        return exc.code, body


def pair(config):
    credential_hash = hashlib.sha256(str(config["credential"]).encode("utf-8")).hexdigest()
    return _post(config, "/api/mobile/pair/request", {
        "device_id": config["device_id"],
        "name": config["node_name"],
        "credential_sha256": credential_hash,
    }, authenticated=False)


def heartbeat(config, root, *, learning_state="idle", current_job_id="", last_error=""):
    state = _load_json(Path(root) / "worker-state.json", {"jobs": {}})
    active = [
        (job_id, row) for job_id, row in (state.get("jobs") or {}).items()
        if row.get("status") in {"AWAITING_SERVER_ACK", "PROCESSING"}
    ]
    if not current_job_id and active:
        current_job_id = active[0][0]
    if learning_state == "idle" and active:
        learning_state = "awaiting_server_ack" if active[0][1].get("status") == "AWAITING_SERVER_ACK" else "watching"
    payload = {
        "device_id": config["device_id"],
        "node_name": config["node_name"],
        "platform": sys.platform,
        "worker_running": True,
        "learning_state": learning_state,
        "current_job_id": current_job_id,
        "network_online": True,
        "last_error": last_error,
    }
    return _post(config, "/api/suryadev/device/heartbeat", payload, authenticated=True)


def _run_local_ack(root, job_id, receipt):
    worker = Path(__file__).resolve().parents[1] / "core" / "suryadev_worker.py"
    python = str(os.getenv("SURYADEV_WORKER_PYTHON") or sys.executable)
    cmd = [
        python, str(worker), "--root", str(Path(root).resolve()),
        "--ack", str(job_id),
        "--receipt-id", str(receipt.get("receipt_id") or ""),
        "--bundle-sha256", str(receipt.get("bundle_sha256") or ""),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "SURYDEV local ACK failed")[-2000:])
    return json.loads(proc.stdout)


def upload_pending(config, root):
    root = Path(root).resolve()
    state = _load_json(root / "worker-state.json", {"jobs": {}})
    results = []
    for job_id, row in list((state.get("jobs") or {}).items()):
        if row.get("status") != "AWAITING_SERVER_ACK":
            continue
        bundle_path = root / "jobs" / job_id / "learning-bundle.json"
        if not bundle_path.is_file():
            results.append({"job_id": job_id, "uploaded": False, "error": "learning-bundle.json missing"})
            continue
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        status, receipt = _post(config, "/api/suryadev/learning-bundle", {
            "device_id": config["device_id"],
            "bundle": bundle,
        }, authenticated=True, timeout=120)
        if not (200 <= status < 300):
            results.append({"job_id": job_id, "uploaded": False, "status": status, "error": receipt.get("error")})
            continue
        expected = str(row.get("bundle_sha256") or "").lower()
        actual = str(receipt.get("bundle_sha256") or "").lower()
        if not expected or actual != expected:
            results.append({
                "job_id": job_id, "uploaded": False,
                "error": "server ACK digest mismatch; local data retained",
                "expected": expected, "actual": actual,
            })
            continue
        if not receipt.get("cleanup_authorized"):
            results.append({"job_id": job_id, "uploaded": False, "error": "server did not authorize cleanup"})
            continue
        cleaned = _run_local_ack(root, job_id, receipt)
        results.append({
            "job_id": job_id,
            "uploaded": True,
            "receipt_id": receipt.get("receipt_id"),
            "accepted_chunks": receipt.get("accepted_chunks"),
            "selected_visuals": receipt.get("selected_visuals"),
            "cleaned": bool(cleaned.get("ok")),
        })
    return results


def run_once(config, root):
    hb_code, hb = heartbeat(config, root)
    uploads = []
    if 200 <= hb_code < 300:
        uploads = upload_pending(config, root)
    return {
        "device_id": config["device_id"],
        "node_name": config["node_name"],
        "heartbeat_status": hb_code,
        "server_link_green": bool(200 <= hb_code < 300 and hb.get("server_link_green")),
        "suryadev_working_green": bool(200 <= hb_code < 300 and hb.get("suryadev_working_green")),
        "learning_green": bool(200 <= hb_code < 300 and hb.get("learning_green")),
        "uploads": uploads,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="SURYDEV private sync/heartbeat client")
    parser.add_argument("--root", required=True)
    parser.add_argument("--server")
    parser.add_argument("--name")
    parser.add_argument("--pair", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=60.0)
    args = parser.parse_args(argv)

    config = _node_config(args.root, server=args.server, node_name=args.name)
    if args.pair:
        code, row = pair(config)
        print(json.dumps({
            "status": code,
            "device_id": config["device_id"],
            "node_name": config["node_name"],
            "pairing": row,
            "credential_hidden": True,
        }, ensure_ascii=False, indent=2))
        return 0 if 200 <= code < 300 else 1

    if args.once:
        print(json.dumps(run_once(config, args.root), ensure_ascii=False, indent=2))
        return 0

    if args.watch:
        while True:
            try:
                print(json.dumps(run_once(config, args.root), ensure_ascii=False), flush=True)
            except Exception as exc:
                print(json.dumps({
                    "device_id": config["device_id"],
                    "server_link_green": False,
                    "suryadev_working_green": False,
                    "learning_green": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }, ensure_ascii=False), flush=True)
            time.sleep(max(15.0, float(args.interval)))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
