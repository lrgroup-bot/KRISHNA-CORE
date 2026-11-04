from __future__ import annotations

"""HAWKEYE Active Vision server-side escalation policy.

The mobile fast path remains deterministic and local. This runtime only decides
what to do after the phone has already attempted target selection, autofocus/
zoom/light recovery, target-crop OCR/barcode reads, and multi-frame consensus.
It never makes the live scanner wait for a heavyweight model. Every proposed recovery or escalation requires explicit owner approval before execution.
"""

from pathlib import Path
import json
import time


class HawkeyeActiveVisionRuntime:
    VERSION = "hawkeye-active-vision-v1"
    TARGET_PRIORITY = ("pointed-object", "explicit-lock", "best-auto-target")
    MOBILE_RECOVERY = (
        "continuous-focus",
        "target-zoom",
        "exposure-compensation",
        "torch-when-supported",
        "target-crop-ocr",
        "potential-barcode-rescan",
        "multiframe-consensus",
    )
    OPTIONAL_ENGINES = {
        "pp_ocr_v6": {
            "role": "hard-label-ocr",
            "placement": "mobile-or-pc",
            "license_expectation": "open-source-model/runtime; verify exact artifact",
            "required": False,
        },
        "mobile_sam": {
            "role": "point-or-box-prompt-segmentation",
            "placement": "mobile",
            "license_expectation": "Apache-2.0 project; verify exact model artifact",
            "required": False,
        },
        "depth_3d_pointing": {
            "role": "depth-assisted pointed-object disambiguation",
            "placement": "mobile",
            "license_expectation": "platform capability",
            "required": False,
        },
        "florence2": {
            "role": "region-grounded-semantic-reading",
            "placement": "pc",
            "license_expectation": "verify installed model license",
            "required": False,
        },
        "grounding_dino": {
            "role": "open-set-object-grounding",
            "placement": "pc",
            "license_expectation": "verify installed model license",
            "required": False,
        },
    }

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.state_dir / "active-vision.jsonl"

    @staticmethod
    def _clamp(value, default=0.0):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _details(value):
        if not isinstance(value, dict):
            return {}
        allowed = ("name", "model", "serial", "input", "output", "power", "voltage", "current", "barcode")
        return {k: str(value.get(k) or "")[:240] for k in allowed if str(value.get(k) or "").strip()}

    def normalize_mobile_packet(self, packet):
        packet = dict(packet or {})
        target = packet.get("target") if isinstance(packet.get("target"), dict) else {}
        quality = packet.get("quality") if isinstance(packet.get("quality"), dict) else {}
        read = packet.get("read") if isinstance(packet.get("read"), dict) else {}
        source = str(target.get("source") or "").upper()
        if source not in {"POINTED", "LOCKED", "AUTO", ""}:
            source = ""
        state = str(read.get("state") or "SEARCH").upper()
        if state not in {"SEARCH", "READING", "RECOVER", "COMPLETE"}:
            state = "SEARCH"
        row = {
            "schema": "hawkeye.active-vision.packet.v1",
            "session_id": str(packet.get("session_id") or "")[:160],
            "target": {
                "key": str(target.get("key") or "")[:200],
                "source": source,
                "tracking_id": target.get("tracking_id"),
                "label": str(target.get("label") or "")[:160],
                "bbox": target.get("bbox") if isinstance(target.get("bbox"), list) else None,
            },
            "read": {
                "state": state,
                "complete": bool(read.get("complete")),
                "confidence": self._clamp(read.get("confidence")),
                "samples": max(0, min(int(read.get("samples") or 0), 1000)),
                "details": self._details(read.get("details")),
                "text": str(read.get("text") or "")[:4000],
                "barcodes": [str(x)[:512] for x in (read.get("barcodes") or [])[:16]],
            },
            "quality": {
                "score": self._clamp(quality.get("score")),
                "brightness": max(0.0, min(255.0, float(quality.get("brightness") or 0.0))),
                "detail": self._clamp(quality.get("detail")),
                "low_light": bool(quality.get("lowLight") or quality.get("low_light")),
            },
            "mobile_recovery_attempts": max(0, min(int(packet.get("mobile_recovery_attempts") or 0), 100)),
            "depth_available": bool(packet.get("depth_available")),
            "pointing_available": bool(packet.get("pointing_available")),
            "electronics_mode": bool(packet.get("electronics_mode")),
            "at": time.time(),
        }
        return row

    def escalation_plan(self, packet, *, installed_engines=None):
        row = self.normalize_mobile_packet(packet)
        installed = {str(x).strip().lower() for x in (installed_engines or []) if str(x).strip()}
        read = row["read"]
        if read["complete"]:
            return {
                "status": "complete",
                "route": "none",
                "reason": "mobile multi-frame consensus reached read-complete",
                "packet": row,
            }

        attempts = row["mobile_recovery_attempts"]
        if attempts < 4:
            return {
                "status": "propose",
                "route": "mobile-active-vision",
                "owner_approval_required": True,
                "actions": list(self.MOBILE_RECOVERY),
                "reason": "deterministic mobile recovery has priority over heavyweight inference",
                "packet": row,
            }

        text_len = len("".join(ch for ch in read["text"] if ch.isalnum()))
        if text_len < 8 and "pp_ocr_v6" in installed:
            return {
                "status": "propose",
                "route": "pp_ocr_v6",
                "owner_approval_required": True,
                "reason": "mobile OCR remained insufficient after bounded automatic recovery",
                "packet": row,
            }

        if row["pointing_available"] and "mobile_sam" in installed:
            return {
                "status": "propose",
                "route": "mobile_sam",
                "owner_approval_required": True,
                "reason": "pointed target is ambiguous; point-prompt segmentation is available",
                "packet": row,
            }

        if row["depth_available"]:
            return {
                "status": "propose",
                "route": "depth_3d_pointing",
                "owner_approval_required": True,
                "reason": "depth-assisted target disambiguation is available on this device/session",
                "packet": row,
            }

        if row["electronics_mode"] and "grounding_dino" in installed:
            return {
                "status": "propose",
                "route": "grounding_dino",
                "owner_approval_required": True,
                "reason": "open-set electronics/component grounding requested after mobile read exhaustion",
                "packet": row,
            }

        if "florence2" in installed:
            return {
                "status": "propose",
                "route": "florence2",
                "owner_approval_required": True,
                "reason": "region-grounded semantic reading is available on KRISHNA PC",
                "packet": row,
            }

        return {
            "status": "propose",
            "route": "existing-hawkeye-vision",
            "owner_approval_required": True,
            "reason": "optional specialist models are not installed; use existing local/free-only Hawkeye vision without blocking the camera loop",
            "packet": row,
        }

    def record(self, packet, plan):
        row = {
            "packet": self.normalize_mobile_packet(packet),
            "plan": dict(plan or {}),
            "recorded_at": time.time(),
        }
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        return row

    def status(self):
        return {
            "version": self.VERSION,
            "mobile_fast_path": "deterministic-local",
            "target_priority": list(self.TARGET_PRIORITY),
            "proposed_recovery": list(self.MOBILE_RECOVERY),
            "execution_policy": "PROPOSE_ONLY_UNTIL_OWNER_APPROVAL",
            "owner_approval_required": True,
            "optional_engines": self.OPTIONAL_ENGINES,
            "movement_instruction_default": False,
            "paid_dependency_required": False,
            "ready": True,
        }
