from __future__ import annotations

from pathlib import Path
import json
import re
import threading
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
        "vehicle", "car", "truck", "bus", "bike", "motorcycle", "obd", "can bus", "can-fd",
        "j1939", "ecu", "diagnose", "diagnosis", "diagnostic", "bearing", "motor", "pump", "sound fault",
    )
    _HAZARDS = ("mains", "high voltage", "high-voltage", "hv battery", "traction battery", "400v", "800v", "230v", "415v")

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.reference_registry = None
        self.worker_runtime = None
        self.governor = None
        self._worker_lock = threading.RLock()
        self._worker_active = False
        self._worker_last = {}
        self._worker_status = {}

    def bind_reference_registry(self, registry):
        self.reference_registry = registry
        return self.status()

    def bind_worker_runtime(self, worker_runtime, governor):
        self.worker_runtime = worker_runtime
        self.governor = governor
        return self.status()

    @classmethod
    def should_activate(cls, goal: str) -> bool:
        text = str(goal or "").lower().strip()
        return bool(text) and any(re.search(r"(?<![a-z0-9_])" + re.escape(term) + r"(?![a-z0-9_])", text) for term in cls._TRIGGERS)

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
        reference_id=self._text(sensors.get("reference_id"),120)
        anchors=sensors.get("reference_anchors") or []
        if reference_id and self.reference_registry is not None and isinstance(anchors,list) and len(anchors)>=3:
            try:
                aligned=self.reference_registry.overlay(reference_id,anchors)
                result["overlay"]=aligned
                result["components"]=aligned["components"]
                result["flows"]=aligned["flows"]
                result["test_points"]=aligned.get("test_points") or []
                result["diagram_mode"]="reference-aligned"
                result["accuracy_note"]=aligned["accuracy_note"]
                result["needs_reference"]=False
                result["reference_type"]=aligned.get("reference_kind") or result["reference_type"]
                result["reference_id"]=reference_id
                result["registration_rms"]=aligned.get("registration_rms")
            except Exception as exc:
                result.setdefault("warnings",[]).append("Reference alignment unavailable: "+str(exc)[:180])
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

    @staticmethod
    def _worker_specialty(goal, modality):
        text=str(goal or "").lower()
        if modality=="audio" or any(x in text for x in ("sound","noise","vibration","bearing")):return "AcousticDiagnosticWorker"
        if any(x in text for x in ("vehicle","truck","car","bus","bike","motorcycle","obd","can bus","j1939","ecu","engine")):return "VehicleDiagnosticWorker"
        if any(x in text for x in ("circuit","pcb","board","motherboard","electronic","wiring","relay","fuse","connector","voltage")):return "ElectronicsDiagnosticWorker"
        return None

    def maybe_dispatch_worker(self, session_id, result, *, goal="", modality="image", evidence=None):
        specialty=self._worker_specialty(goal,modality)
        if not specialty or self.worker_runtime is None or self.governor is None:return {"status":"not_needed"}
        now=time.time();key=self._safe_id(session_id)+":"+specialty
        confidence=float((result or {}).get("confidence") or 0.0);warnings=(result or {}).get("warnings") or []
        if modality=="image" and confidence>=0.85 and not warnings and not (result or {}).get("needs_reference",False):return {"status":"not_needed","reason":"high_confidence_no_escalation"}
        with self._worker_lock:
            if self._worker_active:return {"status":"busy","specialty":specialty}
            if now-float(self._worker_last.get(key) or 0)<60:return {"status":"cooldown","specialty":specialty}
            self._worker_active=True;self._worker_last[key]=now;self._worker_status[key]={"status":"queued","specialty":specialty,"at":now}
        task={
            "goal":str(goal or "")[:1000],"modality":str(modality or "image"),
            "analysis":str((result or {}).get("analysis") or "")[:5000],
            "confidence":confidence,"evidence_state":str((result or {}).get("evidence_state") or "UNKNOWN"),
            "warnings":warnings[:8],"needs_reference":bool((result or {}).get("needs_reference",False)),
            "pc_evidence":dict(evidence or {}),
        }
        def run():
            try:
                request={
                    "status":"approved","approved_by":"KRISHNA","requested_count":1,"manager":"HAWKEYE DIAGNOSTIC","role":specialty,
                    "assignments":[{"specialty":specialty,"task":"Review the bounded diagnostic evidence summary, identify the most supported fault hypotheses, and specify the next safest measurement/test. Do not invent measurements."}],
                    "retention_policy":"findings_and_provenance_only","allow_sub_shishyas":False,
                }
                with self.governor.job(timeout=0):
                    receipt=self.worker_runtime.execute("KRISHNA",request,json.dumps(task,ensure_ascii=False),"local_only")
                state={"status":"completed","specialty":specialty,"at":time.time(),"destroyed":bool(receipt.get("destroyed")),"worker_count":len(receipt.get("workers") or [])}
            except Exception as exc:
                state={"status":"deferred","specialty":specialty,"at":time.time(),"error":f"{type(exc).__name__}: {exc}"[:300]}
            with self._worker_lock:
                self._worker_status[key]=state;self._worker_active=False
        threading.Thread(target=run,name="hawkeye-diagnostic-worker",daemon=True).start()
        return {"status":"queued","specialty":specialty,"cooldown_seconds":60}

    def worker_status(self):
        with self._worker_lock:return {"active":self._worker_active,"recent":dict(self._worker_status)}

    def status(self):
        return {
            "specialist": self.SPECIALIST_NAME, "specialist_id": self.SPECIALIST_ID,
            "lightweight_permanent_role": True, "activation": "on-demand diagnosis",
            "temporary_workers": list(self.TEMPORARY_WORKERS), "live_overlay": True,
            "overlay_schema": "hawkeye.diagnostic-overlay.v1", "camera_only_diagram_mode": "visual-inference",
            "reference_alignment": ["schematic", "boardview", "netlist", "service-manual"],
            "main_loop_blocking": False, "session_count": len(list(self.state_dir.glob("*.json"))),
            "reference_registry_bound": self.reference_registry is not None,
            "worker_runtime_bound": self.worker_runtime is not None,
            "worker_dispatch": self.worker_status(), "ready": True,
        }
