from __future__ import annotations

"""Portable SURYDEV external learning/evidence worker.

This process is intentionally a small control-plane worker. Capture, browser
observation, speech-to-text, and visual-evidence selection are performed by a free
sidecar adapter on the external node. SURYDEV does not become a second BRAHMAGYAN:
it returns bounded evidence packets to the existing BRAHMA/Rishi learning path.

A job is not complete merely because an adapter exited with code 0. The adapter must
produce a valid learning-bundle.json, the bundle must be accepted by the server, and
only a matching server acknowledgement permits local transient-data cleanup.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


AGENT = "SURYDEV"
VERSION = "suryadev-worker-v2"
BUNDLE_SCHEMA = "krishna.suryadev.learning-bundle.v1"
REPORT_SCHEMA = "krishna.suryadev.worker-report.v2"
STATE_SCHEMA = "krishna.suryadev.worker-state.v1"
TRANSIENT_DIRS = ("raw", "audio", "video", "frames", "transcript", "cache", "tmp")
OPTIONAL_MODULES = {
    "mss": "screen capture",
    "cv2": "camera/frame processing",
    "pyaudiowpatch": "Windows system-audio loopback",
    "faster_whisper": "speech-to-text",
    "scenedetect": "scene/keyframe detection",
    "playwright": "isolated browser/video observation",
}
OPTIONAL_TOOLS = {
    "ffmpeg": "media extraction",
    "ffprobe": "media inspection",
    "yt-dlp": "authorized subtitle/media metadata retrieval",
}


def _sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _state_path(root):
    return Path(root).resolve() / "worker-state.json"


def _load_state(root):
    path = _state_path(root)
    if not path.is_file():
        return {"schema": STATE_SCHEMA, "jobs": {}, "updated_at": time.time()}
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"SURYDEV durable state unreadable: {type(exc).__name__}: {exc}") from exc
    if not isinstance(row, dict) or not isinstance(row.get("jobs"), dict):
        raise RuntimeError("SURYDEV durable state has an invalid schema")
    row["schema"] = STATE_SCHEMA
    return row


def _save_state(root, state):
    state = dict(state or {})
    state["schema"] = STATE_SCHEMA
    state["updated_at"] = time.time()
    _atomic_json(_state_path(root), state)


def probe():
    modules = {
        name: {"available": importlib.util.find_spec(name) is not None, "purpose": purpose}
        for name, purpose in OPTIONAL_MODULES.items()
    }
    tools = {
        name: {"available": bool(shutil.which(name)), "path": shutil.which(name), "purpose": purpose}
        for name, purpose in OPTIONAL_TOOLS.items()
    }
    return {
        "agent": AGENT,
        "version": VERSION,
        "modules": modules,
        "tools": tools,
        "capabilities": {
            "screen_capture": modules["mss"]["available"],
            "camera_frames": modules["cv2"]["available"],
            "system_audio": modules["pyaudiowpatch"]["available"],
            "speech_to_text": modules["faster_whisper"]["available"],
            "scene_detection": modules["scenedetect"]["available"],
            "browser": modules["playwright"]["available"],
            "media_extract": tools["ffmpeg"]["available"],
            "durable_idempotency": True,
            "server_ack_cleanup": True,
            "selected_visual_evidence": True,
        },
        "policy": {
            "raw_media_stays_local": True,
            "full_transcript_is_transient": True,
            "return_distilled_findings_only": True,
            "delete_transient_only_after_matching_server_ack": True,
            "authentication_handoff": "owner_permission_required_per_checkpoint",
            "auth_permission_scope": "one_time_job_origin_method",
            "captcha_liveness": "owner-approved-human-handoff-only",
        },
    }


def _safe_job_id(value):
    value = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_")
    if not value:
        raise ValueError("job_id missing or invalid")
    return value[:160]


def _adapter_command():
    adapter = str(os.getenv("SURYADEV_JOB_ADAPTER") or "").strip()
    if not adapter:
        return []
    adapter_path = Path(adapter)
    python = str(os.getenv("SURYADEV_ADAPTER_PYTHON") or "").strip()
    if adapter_path.suffix.lower() == ".py":
        if not python:
            python = shutil.which("python") or shutil.which("python3") or ""
        if not python:
            raise RuntimeError("SURYADEV_ADAPTER_PYTHON is required for a Python learning adapter")
        return [python, str(adapter_path)]
    return [adapter]


def _run_adapter(job, job_path, workspace):
    argv = _adapter_command()
    if not argv:
        return None
    constraints = dict(job.get("constraints") or {})
    requested = int(constraints.get("worker_timeout_seconds") or constraints.get("duration_seconds") or 3600)
    # Supports a six-hour learning shift plus a small end-of-video grace period.
    timeout = max(60, min(requested + 600, 6 * 3600 + 15 * 60))
    cmd = [*argv, str(job_path), str(workspace)]
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=False, timeout=timeout)
    return {
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-12000:],
        "stderr": (proc.stderr or "")[-12000:],
        "command": cmd[:2],
    }


def _validate_bundle(bundle_path, job):
    path = Path(bundle_path)
    if not path.is_file():
        return {"valid": False, "reason": "learning-bundle.json missing"}
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"valid": False, "reason": f"learning bundle JSON invalid: {type(exc).__name__}"}
    if not isinstance(row, dict) or row.get("schema") != BUNDLE_SCHEMA:
        return {"valid": False, "reason": "unsupported learning bundle schema"}
    if str(row.get("job_id") or "") != str(job.get("job_id") or ""):
        return {"valid": False, "reason": "learning bundle job_id mismatch"}
    if row.get("raw_media_included") is not False:
        return {"valid": False, "reason": "raw media may not be embedded in learning bundle"}
    chunks = row.get("learning_chunks") or []
    visuals = row.get("visual_evidence") or []
    if not isinstance(chunks, list) or not isinstance(visuals, list):
        return {"valid": False, "reason": "learning_chunks and visual_evidence must be lists"}
    if not chunks and not visuals:
        return {"valid": False, "reason": "learning bundle contains no learning/evidence"}
    if len(chunks) > 120 or len(visuals) > 120:
        return {"valid": False, "reason": "learning bundle exceeds bounded evidence limits"}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            return {"valid": False, "reason": "learning chunk must be an object"}
        text = str(chunk.get("text") or "").strip()
        if not text:
            return {"valid": False, "reason": "learning chunk text is required"}
        if len(text) > 8000:
            return {"valid": False, "reason": "learning chunk exceeds 8000 characters"}
    for visual in visuals:
        if not isinstance(visual, dict):
            return {"valid": False, "reason": "visual evidence must be an object"}
        if visual.get("bytes") is not None or visual.get("base64") is not None:
            return {"valid": False, "reason": "visual bytes/base64 are forbidden in learning bundle"}
        sha = str(visual.get("sha256") or "")
        if sha and (len(sha) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in sha)):
            return {"valid": False, "reason": "visual evidence sha256 is invalid"}
    return {
        "valid": True,
        "bundle": row,
        "bundle_sha256": _sha256_file(path),
        "chunk_count": len(chunks),
        "visual_count": len(visuals),
    }


def process_job(job_path, root):
    job_path = Path(job_path).resolve()
    raw_job = job_path.read_bytes()
    job = json.loads(raw_job.decode("utf-8"))
    if job.get("schema") != "krishna.suryadev.job.v1":
        raise ValueError("unsupported SURYDEV job schema")
    job_id = _safe_job_id(job.get("job_id"))
    root = Path(root).resolve()
    work = root / "jobs" / job_id
    work.mkdir(parents=True, exist_ok=True)
    job_sha = _sha256_bytes(raw_job)

    state = _load_state(root)
    prior = dict(state["jobs"].get(job_id) or {})
    if prior.get("job_sha256") == job_sha and prior.get("status") in {
        "AWAITING_SERVER_ACK", "ACKNOWLEDGED_CLEANED"
    }:
        report_path = Path(prior.get("report_path") or work / "worker-report.json")
        if report_path.is_file():
            out = json.loads(report_path.read_text(encoding="utf-8"))
            out["reused_durable_result"] = True
            return out

    capability = probe()
    adapter_result = _run_adapter(job, job_path, work)
    bundle_check = _validate_bundle(work / "learning-bundle.json", job)

    if adapter_result is None:
        status = "ADAPTER_REQUIRED"
    elif adapter_result.get("returncode") != 0:
        status = "FAILED"
    elif not bundle_check.get("valid"):
        status = "EVIDENCE_REQUIRED"
    else:
        status = "AWAITING_SERVER_ACK"

    report = {
        "schema": REPORT_SCHEMA,
        "agent": AGENT,
        "version": VERSION,
        "job_id": job_id,
        "job_sha256": job_sha,
        "kind": job.get("kind"),
        "project": job.get("project"),
        "target": job.get("target"),
        "status": status,
        "capability_probe": capability,
        "adapter_result": adapter_result,
        "bundle_valid": bool(bundle_check.get("valid")),
        "bundle_validation": {k: v for k, v in bundle_check.items() if k != "bundle"},
        "bundle_sha256": bundle_check.get("bundle_sha256"),
        "workspace": str(work),
        "created_at": time.time(),
        "raw_media_included": False,
        "ready_for_upload": status == "AWAITING_SERVER_ACK",
        "cleanup_pending": status == "AWAITING_SERVER_ACK",
        "completion_rule": "server ACK with matching bundle SHA-256 is required before local transient cleanup",
        "next_action": (
            "Upload learning-bundle.json to the paired KRISHNA/SURYDEV intake and wait for matching ACK"
            if status == "AWAITING_SERVER_ACK"
            else "Configure/fix the free learning adapter and produce a valid bounded learning-bundle.json"
        ),
        "authentication_checkpoint_rule": (
            "On login/password/MFA/passkey/CAPTCHA/liveness: pause, emit an owner-permission request, "
            "and continue only after a one-time scoped approval is received. Human performs authentication."
        ),
    }
    out = work / "worker-report.json"
    _atomic_json(out, report)
    state["jobs"][job_id] = {
        "job_sha256": job_sha,
        "status": status,
        "report_path": str(out),
        "bundle_sha256": bundle_check.get("bundle_sha256"),
        "updated_at": time.time(),
    }
    _save_state(root, state)
    return report


def acknowledge(root, job_id, receipt_id, bundle_sha256):
    root = Path(root).resolve()
    job_id = _safe_job_id(job_id)
    state = _load_state(root)
    row = dict(state["jobs"].get(job_id) or {})
    if not row:
        raise KeyError(job_id)
    if row.get("status") == "ACKNOWLEDGED_CLEANED":
        return {"ok": True, "job_id": job_id, "already_cleaned": True, "receipt_id": row.get("receipt_id")}
    if row.get("status") != "AWAITING_SERVER_ACK":
        raise RuntimeError(f"job is not waiting for server ACK: {row.get('status')}")
    expected = str(row.get("bundle_sha256") or "")
    supplied = str(bundle_sha256 or "").lower()
    if not expected or supplied != expected.lower():
        raise ValueError("server ACK bundle SHA-256 does not match local bundle")

    work = root / "jobs" / job_id
    removed = []
    for name in TRANSIENT_DIRS:
        target = work / name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed.append(name)
    bundle = work / "learning-bundle.json"
    if bundle.exists():
        bundle.unlink()
        removed.append("learning-bundle.json")

    receipt = {
        "schema": "krishna.suryadev.cleanup-receipt.v1",
        "job_id": job_id,
        "receipt_id": str(receipt_id or "").strip()[:200],
        "bundle_sha256": expected,
        "removed": removed,
        "cleaned_at": time.time(),
        "rule": "transient learning data removed only after matching server ACK",
    }
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    receipt_path = receipts / f"{job_id}.json"
    _atomic_json(receipt_path, receipt)

    row.update({
        "status": "ACKNOWLEDGED_CLEANED",
        "receipt_id": receipt["receipt_id"],
        "receipt_path": str(receipt_path),
        "cleaned_at": receipt["cleaned_at"],
        "updated_at": time.time(),
    })
    state["jobs"][job_id] = row
    _save_state(root, state)
    return {"ok": True, **receipt}


def status(root):
    state = _load_state(root)
    counts = {}
    for row in state["jobs"].values():
        key = str(row.get("status") or "UNKNOWN")
        counts[key] = int(counts.get(key) or 0) + 1
    return {
        "agent": AGENT,
        "version": VERSION,
        "state_schema": STATE_SCHEMA,
        "job_count": len(state["jobs"]),
        "status_counts": counts,
        "probe": probe(),
    }


def watch(inbox, root, poll=2.0):
    inbox = Path(inbox).resolve()
    inbox.mkdir(parents=True, exist_ok=True)
    while True:
        state = _load_state(root)
        for path in sorted(inbox.glob("*.json")):
            try:
                raw = path.read_bytes()
                job = json.loads(raw.decode("utf-8"))
                job_id = _safe_job_id(job.get("job_id"))
                job_sha = _sha256_bytes(raw)
                known = dict(state["jobs"].get(job_id) or {})
                if known.get("job_sha256") == job_sha and known.get("status") in {
                    "AWAITING_SERVER_ACK", "ACKNOWLEDGED_CLEANED"
                }:
                    continue
                report = process_job(path, root)
                print(json.dumps(report, ensure_ascii=False), flush=True)
            except Exception as exc:
                print(json.dumps({
                    "agent": AGENT,
                    "status": "FAILED",
                    "file": str(path),
                    "error": f"{type(exc).__name__}: {exc}",
                }, ensure_ascii=False), flush=True)
        time.sleep(max(0.5, float(poll)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="KRISHNA SURYDEV external Eye+Ear learning worker")
    parser.add_argument("--root", default=str(Path.cwd() / "suryadev-workspace"))
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--job")
    parser.add_argument("--watch")
    parser.add_argument("--poll", type=float, default=2.0)
    parser.add_argument("--ack")
    parser.add_argument("--receipt-id", default="")
    parser.add_argument("--bundle-sha256", default="")
    args = parser.parse_args(argv)

    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False, indent=2))
        return 0
    if args.status:
        print(json.dumps(status(args.root), ensure_ascii=False, indent=2))
        return 0
    if args.ack:
        print(json.dumps(
            acknowledge(args.root, args.ack, args.receipt_id, args.bundle_sha256),
            ensure_ascii=False, indent=2,
        ))
        return 0
    if args.job:
        print(json.dumps(process_job(args.job, args.root), ensure_ascii=False, indent=2))
        return 0
    if args.watch:
        watch(args.watch, args.root, args.poll)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
