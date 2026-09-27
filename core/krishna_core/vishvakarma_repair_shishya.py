from __future__ import annotations

"""Permanent Vishvakarma repair-research shishya.

This module does not diagnose by intuition alone. It converts verified repair
knowledge, Hawkeye-visible targets and real instrument readings into a bounded,
step-by-step repair session. Every real repair can be distilled back into
VishvakarmaLearning with provenance so successes and failures become reusable
knowledge.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time
import uuid

from .vishvakarma_learning import ResearchLesson


@dataclass
class RepairResearchFinding:
    source: str
    source_version: str
    license: str
    topic: str
    lesson: str
    evidence: str
    confidence: float = 0.5
    failure_pattern: str = ""


class VishvakarmaRepairShishya:
    VERSION = "vishvakarma-repair-shishya-v1"
    NAME = "Vishvakarma Repair Shishya"
    ROLE = "permanent electronics/electrical repair research and evidence-guided bench assistant"

    SAFE_QUANTITIES = {
        "voltage", "current", "resistance", "continuity", "frequency",
        "duty_cycle", "temperature", "capacitance",
    }
    HIGH_VOLTAGE_VOLTS = 60.0

    def __init__(self, root, learning):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions = self.root / "repair_sessions"
        self.sessions.mkdir(parents=True, exist_ok=True)
        self.learning = learning

    @staticmethod
    def _safe_id(value):
        out = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_")
        if not out:
            raise ValueError("invalid repair session id")
        return out

    def _path(self, session_id):
        return self.sessions / (self._safe_id(session_id) + ".json")

    def _load(self, session_id):
        path = self._path(session_id)
        if not path.exists():
            raise KeyError(session_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, state):
        state["updated_at"] = time.time()
        self._path(state["session_id"]).write_text(
            json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        return state

    def research_mission(self, topic):
        topic = str(topic or "").strip()
        if not topic:
            raise ValueError("repair research topic is required")
        return {
            "shishya": self.NAME,
            "permanent": True,
            "topic": topic,
            "research_questions": [
                f"How do experienced repair technicians isolate faults for {topic}?",
                f"What are the normal power rails, startup sequence and common failure points for {topic}?",
                f"What measurements and test points safely distinguish the common faults in {topic}?",
                f"What repairs commonly fail or create repeat faults in {topic}?",
                f"What post-repair measurements or stress tests verify a durable repair for {topic}?",
            ],
            "preferred_sources": [
                "manufacturer service manuals and datasheets",
                "schematics/boardviews/netlists with lawful provenance",
                "component datasheets and reference designs",
                "repair training material with reproducible measurements",
                "reputable repair case studies and open-source tools",
            ],
            "rules": [
                "preserve source/version/license/provenance",
                "separate observed/measured facts from inferred hypotheses",
                "record failed repair paths as well as successful ones",
                "never invent pin functions, rail voltages or component values",
                "candidate lessons require Vishvakarma/BRAHMA verification before becoming trusted guidance",
            ],
        }

    def save_research(self, finding: RepairResearchFinding):
        lesson = ResearchLesson(
            source=finding.source,
            source_version=finding.source_version,
            license=finding.license,
            topic="electronics-repair:" + str(finding.topic or "").strip(),
            lesson=finding.lesson,
            evidence=finding.evidence,
            confidence=finding.confidence,
            status="candidate",
            failure_pattern=finding.failure_pattern,
        )
        return self.learning.ingest(lesson)

    def start_session(
        self,
        *,
        device_type,
        symptom,
        model="",
        board_id="",
        reference_id="",
        reference_verified=False,
        test_points=None,
        visible_targets=None,
    ):
        if not str(device_type or "").strip() or not str(symptom or "").strip():
            raise ValueError("device_type and symptom are required")
        session_id = str(uuid.uuid4())
        state = {
            "session_id": session_id,
            "shishya": self.NAME,
            "permanent": True,
            "device_type": str(device_type).strip()[:160],
            "model": str(model or "").strip()[:160],
            "board_id": str(board_id or "").strip()[:160],
            "symptom": str(symptom).strip()[:1000],
            "reference_id": str(reference_id or "").strip()[:160] or None,
            "reference_verified": bool(reference_verified),
            "test_points": list(test_points or [])[:128],
            "visible_targets": list(visible_targets or [])[:128],
            "measurements": [],
            "observations": [],
            "actions": [],
            "outcome": None,
            "created_at": time.time(),
            "updated_at": time.time(),
            "safety": {
                "controls_instrument": False,
                "energizes_circuit": False,
                "high_voltage_live_probe_authorized": False,
                "replace_component_without_evidence": False,
            },
        }
        self._save(state)
        return {
            "session": state,
            "next": self.next_step(session_id),
        }

    def add_observation(self, session_id, observation, *, evidence_state="OBSERVED", target=None):
        state = self._load(session_id)
        row = {
            "observation": str(observation or "").strip()[:3000],
            "evidence_state": str(evidence_state or "OBSERVED").upper()[:20],
            "target": target,
            "at": time.time(),
        }
        if not row["observation"]:
            raise ValueError("observation is required")
        state["observations"].append(row)
        state["observations"] = state["observations"][-500:]
        self._save(state)
        return {"recorded": row, "next": self.next_step(session_id)}

    @staticmethod
    def _volts(value, unit):
        value = float(value)
        unit = str(unit or "")
        if unit == "mV":
            return value / 1000.0
        if unit == "V":
            return value
        return None

    def record_measurement(
        self,
        session_id,
        *,
        point,
        quantity,
        value,
        unit,
        reference="",
        target=None,
        circuit_state="unknown",
    ):
        state = self._load(session_id)
        quantity = str(quantity or "").strip().lower()
        if quantity not in self.SAFE_QUANTITIES:
            raise ValueError("unsupported repair measurement quantity")
        point = str(point or "").strip()
        if not point:
            raise ValueError("measurement point is required")
        if quantity == "continuity":
            normalized_value = bool(value)
        else:
            normalized_value = float(value)
        volts = self._volts(normalized_value, unit) if quantity == "voltage" else None
        hazardous = bool(
            (volts is not None and abs(volts) >= self.HIGH_VOLTAGE_VOLTS)
            or str(circuit_state or "").lower() in {
                "mains", "high_voltage", "energized_hv", "traction_battery"
            }
        )
        row = {
            "point": point[:160],
            "quantity": quantity,
            "value": normalized_value,
            "unit": str(unit or "").strip()[:32],
            "reference": str(reference or "").strip()[:240] or None,
            "target": target,
            "circuit_state": str(circuit_state or "unknown")[:80],
            "hazardous_voltage_possible": hazardous,
            "evidence_state": "MEASURED",
            "at": time.time(),
        }
        state["measurements"].append(row)
        state["measurements"] = state["measurements"][-1000:]
        self._save(state)
        return {
            "recorded": row,
            "warning": (
                "STOP live probing: hazardous voltage may be present. De-energize/isolate and use appropriately rated equipment/procedures."
                if hazardous else None
            ),
            "next": self.next_step(session_id),
        }

    def _verified_points(self, state):
        if not state.get("reference_verified"):
            return []
        rows = []
        for raw in state.get("test_points") or []:
            if not isinstance(raw, dict):
                continue
            label = str(raw.get("label") or raw.get("point") or "").strip()
            if not label:
                continue
            rows.append(raw)
        return rows

    def next_step(self, session_id):
        state = self._load(session_id)
        measurements = state.get("measurements") or []
        observations = state.get("observations") or []

        if any(x.get("hazardous_voltage_possible") for x in measurements[-3:]):
            return {
                "stage": "SAFETY_STOP",
                "instruction": "Stop live probing and de-energize/isolate the circuit before continuing.",
                "why": "The latest evidence indicates potentially hazardous voltage.",
                "evidence_required": "safe isolation/absence-of-voltage confirmation by an appropriately rated procedure",
            }

        if not observations:
            return {
                "stage": "VISUAL_INSPECTION",
                "instruction": "With power removed, inspect both sides and show Hawkeye the input connector, power section, regulators, visibly damaged/burnt/corroded areas and readable IC/board markings.",
                "target": "whole board, then power-input area",
                "instrument": "camera / magnification",
                "why": "A human repair technician establishes board identity, damage and the power path before probing.",
                "do_not": "Do not replace an IC only from the symptom.",
            }

        points = self._verified_points(state)
        measured_names = {str(x.get("point") or "").strip().lower() for x in measurements}

        for point in points:
            label = str(point.get("label") or point.get("point") or "").strip()
            if label.lower() in measured_names:
                continue
            return {
                "stage": "VERIFIED_TEST_POINT",
                "instruction": f"Measure {label} exactly as specified by the verified reference, then tell me the reading.",
                "target": {
                    "label": label,
                    "component_id": point.get("component_id"),
                    "bbox": point.get("bbox"),
                },
                "instrument": point.get("instrument") or "multimeter / appropriate instrument",
                "mode": point.get("quantity") or "reference-defined",
                "expected": {
                    "value": point.get("expected"),
                    "min": point.get("expected_min"),
                    "max": point.get("expected_max"),
                    "unit": point.get("unit"),
                },
                "why": point.get("reason") or "This is a verified reference test point in the diagnostic sequence.",
                "evidence_state": "REFERENCE_VERIFIED",
            }

        if not measurements:
            return {
                "stage": "POWER_PATH_IDENTIFICATION",
                "instruction": "Identify the board input connector/fuse/protection stage from visible markings or a verified schematic. With power removed, check for an obvious short to ground on the main input rail before applying power.",
                "target": "input connector / fuse / main input rail",
                "instrument": "multimeter",
                "mode": "resistance or continuity with power removed",
                "why": "This distinguishes a hard input short from a downstream startup problem without guessing ICs.",
                "reference_required_for": "exact pin numbers or expected resistance",
            }

        last = measurements[-1]
        if last["quantity"] == "voltage" and float(last["value"]) == 0.0:
            return {
                "stage": "ZERO_VOLTAGE_BRANCH",
                "instruction": "Do not move downstream yet. Verify the source/adapter, connector, fuse/protection device and both sides of the input path to find where voltage disappears.",
                "target": "upstream of " + str(last["point"]),
                "instrument": "multimeter",
                "mode": "voltage",
                "why": "A missing upstream supply makes downstream IC replacement unjustified.",
            }

        return {
            "stage": "EVIDENCE_REVIEW",
            "instruction": "The next exact component/pin test needs either a verified schematic/boardview/datasheet or a Hawkeye-visible component target. Add that reference or capture a closer image before continuing.",
            "why": "Without verified topology, exact pin/rail instructions would be guesswork.",
            "measurements_seen": len(measurements),
            "reference_verified": bool(state.get("reference_verified")),
        }

    def record_action(self, session_id, action, *, result="", evidence_state="OBSERVED"):
        state = self._load(session_id)
        row = {
            "action": str(action or "").strip()[:2000],
            "result": str(result or "").strip()[:3000],
            "evidence_state": str(evidence_state or "OBSERVED").upper()[:20],
            "at": time.time(),
        }
        if not row["action"]:
            raise ValueError("action is required")
        state["actions"].append(row)
        state["actions"] = state["actions"][-500:]
        self._save(state)
        return row

    def finish_session(self, session_id, *, outcome, repaired, verification="", notes=""):
        state = self._load(session_id)
        result = {
            "outcome": str(outcome or "").strip()[:3000],
            "repaired": bool(repaired),
            "verification": str(verification or "").strip()[:3000],
            "notes": str(notes or "").strip()[:3000],
            "finished_at": time.time(),
        }
        if not result["outcome"]:
            raise ValueError("repair outcome is required")
        state["outcome"] = result
        self._save(state)

        evidence = json.dumps({
            "device_type": state.get("device_type"),
            "model": state.get("model"),
            "board_id": state.get("board_id"),
            "symptom": state.get("symptom"),
            "reference_id": state.get("reference_id"),
            "reference_verified": state.get("reference_verified"),
            "observations": state.get("observations"),
            "measurements": state.get("measurements"),
            "actions": state.get("actions"),
            "outcome": result,
        }, ensure_ascii=False, separators=(",", ":"))

        topic_parts = [state.get("device_type"), state.get("model"), state.get("board_id")]
        topic = " ".join(str(x).strip() for x in topic_parts if str(x or "").strip())
        lesson = ResearchLesson(
            source="real-repair:" + state["session_id"],
            source_version=str(state.get("board_id") or state.get("model") or "field-session"),
            license="owner-observation",
            topic="electronics-repair:" + (topic or "unknown-device"),
            lesson=(
                "Real repair outcome: " + result["outcome"] +
                (" Repair verified: " + result["verification"] if result["verification"] else "")
            ),
            evidence=evidence,
            confidence=0.9 if result["repaired"] and result["verification"] else 0.7,
            status="candidate",
            failure_pattern="" if result["repaired"] else result["outcome"],
        )
        stored = self.learning.ingest(lesson)
        return {
            "session": state,
            "vishvakarma_learning": stored,
            "knowledge_status": "candidate",
            "brahma_review_required": True,
        }

    def status(self):
        count = len(list(self.sessions.glob("*.json")))
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "role": self.ROLE,
            "permanent": True,
            "sessions": count,
            "learning_sink": "VishvakarmaLearning",
            "workflow": [
                "research",
                "visual inspection",
                "reference-aware test plan",
                "real instrument measurements",
                "fault isolation",
                "repair",
                "post-repair verification",
                "distill success/failure into Vishvakarma knowledge",
            ],
            "safety": {
                "no_invented_pinouts": True,
                "no_component_replacement_without_evidence": True,
                "high_voltage_live_probe_authorized": False,
                "instrument_control": False,
            },
        }
