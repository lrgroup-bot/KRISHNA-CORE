from __future__ import annotations

"""LAB BOT: bounded experiment planning, simulation and instrument orchestration.

LAB BOT turns a Rishi research question into a durable, machine-checkable
experiment record. It is deliberately not an unrestricted autonomous wet-lab
controller: physical execution requires an explicitly registered adapter,
Sudarshan/owner approval, protocol review, and domain-specific facility gates.

The runtime stores evidence/provenance and never accepts raw shell commands.
"""

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Callable
import json
import time
import uuid

from .quantum_nano_lab import QuantumNanoLab


@dataclass(frozen=True)
class LabAdapter:
    name: str
    capabilities: tuple[str, ...]
    domains: tuple[str, ...]
    physical: bool
    handler: Callable | None = None

    def status(self):
        return {
            "name": self.name,
            "capabilities": list(self.capabilities),
            "domains": list(self.domains),
            "physical": self.physical,
            "connected": callable(self.handler),
        }


class LabBot:
    VERSION = "krishna-lab-bot-v1"

    PHYSICAL_MODES = frozenset({"measurement", "fabrication", "wet_lab"})
    REVIEWED_DOMAINS = frozenset({
        "biology", "biomedical", "medicine", "pharmacology", "chemistry", "wet_lab",
        "nanotechnology", "nanomaterials", "quantum_hardware", "quantum_materials",
    })

    def __init__(self, state_root):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._adapters: dict[str, LabAdapter] = {}
        self.quantum_nano = QuantumNanoLab()
        self.register_adapter(
            "simulation",
            capabilities=("simulate", "dry_run", "protocol_validate"),
            domains=("general",),
            physical=False,
            handler=self._simulation_adapter,
        )

    @staticmethod
    def _now():
        return time.time()

    def _path(self, experiment_id):
        return self.root / (str(experiment_id) + ".json")

    def _write(self, record):
        path = self._path(record["experiment_id"])
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    def _read(self, experiment_id):
        path = self._path(experiment_id)
        if not path.is_file():
            raise KeyError(f"lab experiment not found: {experiment_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _clean_list(values, limit=64):
        return [str(x).strip()[:500] for x in (values or []) if str(x).strip()][:limit]

    def register_adapter(self, name, *, capabilities=(), domains=(), physical=False, handler=None):
        key = str(name or "").strip().lower()
        if not key or any(ch.isspace() for ch in key):
            raise ValueError("lab adapter name must be a non-empty token")
        row = LabAdapter(
            key,
            tuple(sorted({str(x).strip().lower() for x in capabilities if str(x).strip()})),
            tuple(sorted({str(x).strip().lower() for x in domains if str(x).strip()})),
            bool(physical),
            handler,
        )
        with self._lock:
            self._adapters[key] = row
        return row.status()

    def adapter_status(self):
        with self._lock:
            return [self._adapters[k].status() for k in sorted(self._adapters)]

    def request(self, payload):
        rishi = str(payload.get("rishi") or "").strip().lower()
        hypothesis = str(payload.get("hypothesis") or "").strip()
        objective = str(payload.get("objective") or "").strip()
        if not rishi:
            raise ValueError("rishi is required")
        if not hypothesis:
            raise ValueError("hypothesis is required")
        if not objective:
            raise ValueError("objective is required")

        mode = str(payload.get("mode") or "simulation").strip().lower()
        if mode not in {"simulation", "measurement", "fabrication", "wet_lab"}:
            raise ValueError("mode must be simulation, measurement, fabrication or wet_lab")

        domain = str(payload.get("domain") or "general").strip().lower() or "general"
        experiment_id = str(uuid.uuid4())
        record = {
            "schema": 1,
            "version": self.VERSION,
            "experiment_id": experiment_id,
            "created_at": self._now(),
            "updated_at": self._now(),
            "status": "PLANNED",
            "requested_by": rishi,
            "domain": domain,
            "mode": mode,
            "hypothesis": hypothesis[:4000],
            "objective": objective[:4000],
            "requested_artifact": str(payload.get("requested_artifact") or "").strip()[:2000],
            "independent_variable": str(payload.get("independent_variable") or "").strip()[:1000],
            "dependent_variables": self._clean_list(payload.get("dependent_variables")),
            "controls": self._clean_list(payload.get("controls")),
            "measurements": self._clean_list(payload.get("measurements")),
            "success_criteria": self._clean_list(payload.get("success_criteria")),
            "source_refs": self._clean_list(payload.get("source_refs"), 128),
            "limitations": self._clean_list(payload.get("limitations")),
            "preferred_adapter": str(payload.get("adapter") or "simulation").strip().lower(),
            "replication": {
                "independent_replication_required": True,
                "minimum_independent_runs": max(2, min(int(payload.get("minimum_independent_runs") or 3), 20)),
                "negative_control_required": True,
                "comparison_required": True,
            },
            "review": {
                "protocol_reviewed": False,
                "facility_approved": False,
                "human_operator_confirmed": False,
                "owner_approved": False,
            },
            "evidence": [],
            "execution": None,
        }
        with self._lock:
            self._write(record)
        return record

    def protocol(self, experiment_id):
        record = self._read(experiment_id)
        missing = []
        if not record.get("controls"):
            missing.append("controls")
        if not record.get("measurements"):
            missing.append("measurements")
        if not record.get("success_criteria"):
            missing.append("success_criteria")
        phases = [
            {"phase": "preflight", "purpose": "validate apparatus, calibration, controls and evidence capture"},
            {"phase": "baseline", "purpose": "capture control/baseline measurements before intervention"},
            {"phase": "intervention", "purpose": "apply only the reviewed experimental variable through the selected adapter"},
            {"phase": "measurement", "purpose": "record predefined outcomes and uncertainty"},
            {"phase": "replication", "purpose": "repeat independently and compare against controls"},
            {"phase": "verification", "purpose": "submit evidence to independent review before promotion to Gyan-Bhandar"},
        ]
        return {
            "experiment_id": record["experiment_id"],
            "status": record["status"],
            "mode": record["mode"],
            "domain": record["domain"],
            "adapter": record["preferred_adapter"],
            "phases": phases,
            "missing_design_fields": missing,
            "ready_for_simulation": not missing,
            "ready_for_physical_review": not missing and record["mode"] in self.PHYSICAL_MODES,
            "policy": (
                "LAB BOT plans and validates experiments; physical actions require a connected approved adapter "
                "plus explicit review/approval gates."
            ),
        }

    def simulate(self, experiment_id):
        record = self._read(experiment_id)
        protocol = self.protocol(experiment_id)
        if protocol["missing_design_fields"]:
            return {
                "experiment_id": experiment_id,
                "status": "DESIGN_INCOMPLETE",
                "verification": {
                    "passed": False,
                    "reason": "missing experimental design fields: " + ",".join(protocol["missing_design_fields"]),
                },
                "protocol": protocol,
            }
        result = self._simulation_adapter(record, {"protocol": protocol})
        record["status"] = "SIMULATED"
        record["updated_at"] = self._now()
        record["execution"] = result
        record["evidence"].append({
            "kind": "simulation",
            "at": self._now(),
            "summary": result["summary"],
        })
        self._write(record)
        return {
            "experiment_id": experiment_id,
            "status": record["status"],
            "result": result,
            "verification": {
                "passed": True,
                "reason": "experiment design passed dry-run validation; no physical claim is implied",
            },
        }

    def review(self, experiment_id, *, protocol_reviewed=False, facility_approved=False,
               human_operator_confirmed=False, owner_approved=False):
        record = self._read(experiment_id)
        record["review"] = {
            "protocol_reviewed": bool(protocol_reviewed),
            "facility_approved": bool(facility_approved),
            "human_operator_confirmed": bool(human_operator_confirmed),
            "owner_approved": bool(owner_approved),
        }
        record["updated_at"] = self._now()
        self._write(record)
        return record["review"]

    def execute(self, experiment_id, *, adapter=None):
        record = self._read(experiment_id)
        mode = record["mode"]
        if mode == "simulation":
            return self.simulate(experiment_id)

        review = dict(record.get("review") or {})
        if not review.get("owner_approved") or not review.get("protocol_reviewed"):
            raise PermissionError("physical lab execution requires owner approval and protocol review")
        if record["domain"] in self.REVIEWED_DOMAINS:
            if not review.get("facility_approved") or not review.get("human_operator_confirmed"):
                raise PermissionError(
                    "reviewed biological/chemical domains require facility approval and a confirmed human operator"
                )

        adapter_name = str(adapter or record.get("preferred_adapter") or "").strip().lower()
        with self._lock:
            selected = self._adapters.get(adapter_name)
        if not selected:
            raise RuntimeError(f"approved lab adapter is not registered: {adapter_name}")
        if not selected.physical:
            raise RuntimeError("physical experiment cannot execute through a non-physical adapter")
        if not callable(selected.handler):
            raise RuntimeError(f"lab adapter is not connected: {adapter_name}")
        if selected.domains and "general" not in selected.domains and record["domain"] not in selected.domains:
            raise PermissionError(f"adapter {adapter_name} is not approved for domain {record['domain']}")

        result = selected.handler(record, {"protocol": self.protocol(experiment_id)})
        record["status"] = "EXECUTED_PENDING_VERIFICATION"
        record["updated_at"] = self._now()
        record["execution"] = {
            "adapter": adapter_name,
            "physical": True,
            "result": result,
        }
        record["evidence"].append({
            "kind": "physical_execution",
            "adapter": adapter_name,
            "at": self._now(),
            "result": result,
        })
        self._write(record)
        return {
            "experiment_id": experiment_id,
            "status": record["status"],
            "adapter": adapter_name,
            "result": result,
            "verification": {
                "passed": True,
                "reason": "adapter completed; scientific conclusion still requires independent replication/review",
            },
        }

    def record_result(self, experiment_id, evidence):
        record = self._read(experiment_id)
        row = {
            "kind": str((evidence or {}).get("kind") or "measurement")[:80],
            "at": self._now(),
            "summary": str((evidence or {}).get("summary") or "")[:4000],
            "source_refs": self._clean_list((evidence or {}).get("source_refs"), 128),
            "measurements": list((evidence or {}).get("measurements") or [])[:256],
        }
        record["evidence"].append(row)
        record["updated_at"] = self._now()
        self._write(record)
        return row

    def list(self, limit=100):
        rows = []
        for path in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            rows.append({
                "experiment_id": data.get("experiment_id"),
                "requested_by": data.get("requested_by"),
                "domain": data.get("domain"),
                "mode": data.get("mode"),
                "status": data.get("status"),
                "hypothesis": data.get("hypothesis"),
                "updated_at": data.get("updated_at"),
            })
            if len(rows) >= max(1, min(int(limit), 500)):
                break
        return rows

    def get(self, experiment_id):
        return self._read(experiment_id)

    def status(self):
        adapters = self.adapter_status()
        return {
            "component": "KRISHNA LAB BOT",
            "version": self.VERSION,
            "authority": "KRISHNA -> Sudarshan -> LAB BOT -> approved adapter -> independent verification",
            "experiments": len(self.list(500)),
            "adapters": adapters,
            "physical_adapters_connected": sum(1 for x in adapters if x["physical"] and x["connected"]),
            "capability_classes": [
                "simulation", "measurement", "fabrication", "wet_lab", "imaging", "acoustics",
                "quantum", "nanotechnology", "quantum_materials", "nanophotonics",
            ],
            "quantum_nano": self.quantum_nano.status(),
            "future_adapter_targets": [
                "PyLabRobot-compatible lab automation",
                "Opentrons Python Protocol API",
                "bench measurement instruments",
                "microscopy/imaging",
                "signal generators/acoustic rigs",
                "approved fabrication hardware",
            ],
            "policy": {
                "rishi_can_request": True,
                "simulation_can_run_without_physical_hardware": True,
                "physical_execution_requires_approval": True,
                "reviewed_bio_chem_requires_facility_and_human_operator": True,
                "raw_shell_or_unregistered_hardware_commands": False,
                "result_requires_independent_replication_before_verified_knowledge": True,
            },
        }

    @staticmethod
    def _simulation_adapter(record, context):
        protocol = dict(context.get("protocol") or {})
        return {
            "adapter": "simulation",
            "physical": False,
            "summary": (
                "Dry-run validated experiment structure, controls, measurements, replication "
                "requirements and adapter requirements."
            ),
            "phases": list(protocol.get("phases") or []),
            "claim_scope": "design validation only; no physical or biomedical efficacy claim",
        }
