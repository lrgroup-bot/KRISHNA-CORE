from __future__ import annotations

"""Portable Windows controller entrypoint for CHANDRADEV live final QC."""

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import time


AGENT = "CHANDRADEV"
VERSION = "chandradev-worker-v1"


def probe():
    return {
        "agent": AGENT,
        "version": VERSION,
        "modules": {
            "cv2": {
                "available": importlib.util.find_spec("cv2") is not None,
                "purpose": "live camera frame capture/analysis adapter",
            },
            "mss": {
                "available": importlib.util.find_spec("mss") is not None,
                "purpose": "optional direct screen corroboration",
            },
        },
        "tools": {
            "ffmpeg": {
                "available": bool(shutil.which("ffmpeg")),
                "path": shutil.which("ffmpeg"),
                "purpose": "camera/video evidence extraction",
            }
        },
        "policy": {
            "raw_camera_media_stays_local": True,
            "final_packet_contains_findings_only": True,
            "peer_qc": "BRAHMA",
            "disagreement": "DEBATE_REQUIRED",
            "authentication_handoff": "owner_permission_required_per_checkpoint",
            "captcha_liveness": "owner-approved_human_handoff_only",
        },
    }


def validate_qc_packet(path):
    path = Path(path).resolve()
    row = json.loads(path.read_text(encoding="utf-8"))
    required = {"project", "deterministic_passed", "suryadev_review", "brahma_review"}
    missing = sorted(x for x in required if x not in row)
    if missing:
        raise ValueError("QC packet missing fields: " + ", ".join(missing))
    return row


def process_packet(path, root):
    row = validate_qc_packet(path)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    packet_id = "CHANDRA-" + str(int(time.time() * 1000))
    report = {
        "schema": "krishna.chandradev.worker-report.v1",
        "agent": AGENT,
        "version": VERSION,
        "packet_id": packet_id,
        "project": row.get("project"),
        "status": "READY_FOR_CORE_QC",
        "capability_probe": probe(),
        "deterministic_passed": bool(row.get("deterministic_passed")),
        "suryadev_review": row.get("suryadev_review"),
        "brahma_review": row.get("brahma_review"),
        "camera_observation": row.get("camera_observation") or {},
        "test_summary": row.get("test_summary") or "",
        "created_at": time.time(),
        "raw_media_included": False,
        "next_action": "Send this distilled packet to KRISHNA ChandradevQC for independent final decision/debate.",
    }
    out = root / f"{packet_id}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="KRISHNA CHANDRADEV external live-QC worker")
    parser.add_argument("--root", default=str(Path.cwd() / "chandradev-workspace"))
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--packet")
    args = parser.parse_args(argv)

    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False, indent=2))
        return 0
    if args.packet:
        print(json.dumps(process_packet(args.packet, args.root), ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
