from __future__ import annotations

from pathlib import Path
import json
import re
import time


class HawkeyeDiagnosticRuntime:
    """Evidence-gated live diagnostics with a normalized camera-overlay contract."""

    SPECIALIST_ID = "diagnostic"
    SPECIALIST_NAME = "HAWKEYE DIAGNOSTIC"
    TEMPORARY_WORKERS = (
        "AcousticDiagnosticWorker",
        "VehicleDiagnosticWorker",
        "ElectronicsDiagnosticWorker",
    )
    EVIDENCE_STATES = {"MEASURED", "OBSERVED", "INFERRED", "PREDICTED", "UNKNOWN"}
    _TRIGGERS = (
        "circuit", "pcb", "board", "motherboard", "electronic", "wiring", "relay",
        "fuse", "connector", "schematic", "signal flow", "power flow", "voltage",
        "vehicle", "car", "truck", "bus", "bike", "motorcycle", "obd", "can",
        "j1939", "ecu", "diagnos", "bearing", "motor", "pump", "sound fault",
    )
    _HAZARDS = ("mains", "high voltage", "high-voltage", "hv battery", "traction battery", "400v", "800v", "230v", "415v")

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def should_activate(cls, goal: str) -> bool:
        text = str(goal or "").lower()
        return bool(text.strip()) and any(term in text for term in cls._TRIGGERS)

    @staticmethod
    def _safe_id(value):
        out = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_")
        if not out:
            raise ValueError("invalid diagnostic session_id")
        return out

    @staticmethod
    def _text(value, limit):
        return str(value or "").strip()[:limit]

    @staticmethod
    def _clamp(value, default=0.0):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return float(default)

    @classmethod
    def _bbox(cls, value):
        if isinstance(value, dict):
            value = [value.get("x"), value.get("y"), value.get("w", value.get("width")), value.get("h", value.get("height"))]
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            return None
        try:
            x, y, w, h = [float(v) for v in value]
        except (TypeError, ValueError):
            return None
        x, y = cls._clamp(x), cls._clamp(y)
        w, h = max(0.0, min(1.0 - x, w)), max(0.0, min(1.0 - y, h))
        if w <= 0.001 or h <= 0.001:
            return None
        return [round(x, 5), round(y, 5), round(w, 5), round(h, 5)]

    @staticmethod
    def _json_object(text):
        raw = str(text or "").strip()
        candidates = [raw]
        fence = chr(96) * 3
        if fence in raw:
            for part in raw.split(fence):
                part = part.strip()
                if part.lower().startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{") and part.endswith("}"):
                    candidates.append(part)
        if "{" in raw and "}" in raw:
            candidates.append(raw[raw.find("{"):raw.rfind("}") + 1])
        for candidate in candidates:
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        return {}

    def vision_prompt(self, *, goal="", sensor_context=None):
        sensors = dict(sensor_context or {})
        return (
            "You are HAWKEYE DIAGNOSTIC, KRISHNA's electronics, vehicle and machine diagnostic specialist. "
            "Use only visible evidence plus explicit sensor/reference context. For electronics, identify visible components, "
            "connectors and test points and infer only a PRELIMINARY power/signal-flow graph. Camera imagery alone is not an exact "
            "schematic. If a verified schematic, boardview or netlist is supplied, align visible parts to it. Never invent hidden "
            "traces, voltages, pin functions or component values. Never issue vehicle-bus control/programming commands. Warn for "
            "mains or traction-battery hazards. Return STRICT JSON only with: device_type, analysis, confidence (0..1), "
            "evidence_state, components [{id,label,kind,bbox:[x,y,w,h],confidence}], flows [{from,to,label,evidence_state,confidence}], "
            "test_points [{component_id,label,reason,bbox}], warnings, needs_reference, reference_type. Bboxes are normalized 0..1 "
            "in the original image. Empty arrays are better than guesses. "
            f"User goal: {self._text(goal, 1200)}. Sensor/reference context: {json.dumps(sensors, ensure_ascii=False)[:5000]}."
        )

    def normalize(self, model_text, *, goal="", sensor_context=None):
        obj = self._json_object(model_text)
        sensors = dict(sensor_context or {})
        reference_verified = bool(
            sensors.get("reference_verified") or sensors.get("schematic_verified")
            or sensors.get("boardview_verified") or sensors.get("netlist_verified")
        )

        components, ids = [], set()
        for i, row in enumerate(obj.get("components") or []):
            if not isinstance(row, dict):
                continue
            box = self._bbox(row.get("bbox"))
            if not box:
                continue
            cid = re.sub(r"[^A-Za-z0-9_-]", "_", self._text(row.get("id"), 48)) or f"c{i + 1}"
            if cid in ids:
                cid = f"{cid}_{i + 1}"
            ids.add(cid)
            components.append({"id": cid, "label": self._text(row.get("label"), 120) or cid,
                               "kind": self._text(row.get("kind"), 80) or "unknown", "bbox": box,
                               "confidence": self._clamp(row.get("confidence"))})
            if len(components) >= 48:
                break

        flows = []
        for row in obj.get("flows") or []:
            if not isinstance(row, dict):
                continue
            source, target = self._text(row.get("from"), 48), self._text(row.get("to"), 48)
            if source not in ids or target not in ids or source == target:
                continue
            state = self._text(row.get("evidence_state"), 20).upper()
            if state not in self.EVIDENCE_STATES:
                state = "INFERRED"
            if not reference_verified and state == "MEASURED":
                state = "INFERRED"
            flows.append({"from": source, "to": target, "label": self._text(row.get("label"), 80) or "unknown",
                          "evidence_state": state, "confidence": self._clamp(row.get("confidence"))})
            if len(flows) >= 64:
                break

        test_points = []
        for row in obj.get("test_points") or []:
            if not isinstance(row, dict):
                continue
            cid = self._text(row.get("component_id"), 48)
            if cid and cid not in ids:
                continue
            test_points.append({"component_id": cid, "label": self._text(row.get("label"), 80) or "TEST",
                                "reason": self._text(row.get("reason"), 240), "bbox": self._bbox(row.get("bbox"))})
            if len(test_points) >= 32:
                break

        evidence = self._text(obj.get("evidence_state"), 20).upper()
        if evidence not in self.EVIDENCE_STATES:
            evidence = "UNKNOWN"
        warnings = [self._text(x, 260) for x in (obj.get("warnings") or []) if self._text(x, 260)]
        combined = (self._text(goal, 1600) + " " + self._text(obj.get("analysis"), 4000)).lower()
        if any(term in combined for term in self._HAZARDS):
            warning = "Possible hazardous voltage: de-energize, isolate and verify absence of voltage before physical probing."
            if warning not in warnings:
                warnings.insert(0, warning)

        diagram_mode = "reference-aligned" if reference_verified else "visual-inference"
        accuracy_note = (
            "Aligned to supplied verified reference data; physical measurements are still required for fault confirmation."
            if reference_verified else
            "Camera-only flow is a preliminary visual inference, not a verified schematic or hidden-net map."
        )
        needs_reference = bool(obj.get("needs_reference", not reference_verified))
        if not reference_verified:
            needs_reference = True

        result = {
            "specialist": self.SPECIALIST_NAME, "diagnostic": True,
            "device_type": self._text(obj.get("device_type"), 160) or "unknown",
            "analysis": self._text(obj.get("analysis"), 5000) or self._text(model_text, 5000) or "No supported conclusion.",
            "confidence": self._clamp(obj.get("confidence")), "evidence_state": evidence,
            "diagram_mode": diagram_mode, "accuracy_note": accuracy_note,
            "needs_reference": needs_reference,
            "reference_type": self._text(obj.get("reference_type"), 40).lower() or "none",
            "components": components, "flows": flows, "test_points": test_points, "warnings": warnings[:12],
            "safety": {"auto_transmit_vehicle_bus": False, "auto_program_ecu": False, "energized_high_voltage_probe": False},
        }
        result["overlay"] = {
            "schema": "hawkeye.diagnostic-overlay.v1", "coordinate_space": "normalized-original-frame",
            "components": components, "flows": flows, "test_points": test_points,
            "diagram_mode": diagram_mode, "accuracy_note": accuracy_note,
        }
        if not obj:
            result.update({"confidence": 0.0, "evidence_state": "UNKNOWN", "components": [], "flows": [], "test_points": []})
            result["overlay"].update({"components": [], "flows": [], "test_points": []})
        return result

    def record_model_result(self, session_id, model_text, *, goal="", sensor_context=None, model=""):
        result = self.normalize(model_text, goal=goal, sensor_context=sensor_context)
        path = self.state_dir / (self._safe_id(session_id) + ".json")
        try:
            state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            state = {}
        now = time.time()
        state.update({"session_id": self._safe_id(session_id), "specialist": self.SPECIALIST_NAME,
                      "lightweight_permanent_role": True, "temporary_workers": list(self.TEMPORARY_WORKERS),
                      "last_result": result, "last_model": self._text(model, 160), "updated_at": now})
        state.setdefault("created_at", now)
        state["frame_count"] = int(state.get("frame_count") or 0) + 1
        path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        result["frame_count"] = state["frame_count"]
        return result

    def get_session(self, session_id):
        path = self.state_dir / (self._safe_id(session_id) + ".json")
        if not path.exists():
            raise KeyError(session_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def status(self):
        return {
            "specialist": self.SPECIALIST_NAME, "specialist_id": self.SPECIALIST_ID,
            "lightweight_permanent_role": True, "activation": "on-demand diagnosis",
            "temporary_workers": list(self.TEMPORARY_WORKERS), "live_overlay": True,
            "overlay_schema": "hawkeye.diagnostic-overlay.v1", "camera_only_diagram_mode": "visual-inference",
            "reference_alignment": ["schematic", "boardview", "netlist", "service-manual"],
            "main_loop_blocking": False, "session_count": len(list(self.state_dir.glob("*.json"))), "ready": True,
        }
