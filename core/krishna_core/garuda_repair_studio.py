"""GARUDA Repair Studio: original, offline-first repair case engine.

Does not copy third-party repair guides or execute device commands.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import json
import re

SAFE_STEPS = {
    "storage": (
        ("collect_disk_health", "Collect authorized read-only SMART/health report"),
        ("check_backup", "Confirm a current, readable backup before changes"),
        ("inspect_connections", "With power removed, have a technician inspect storage connections"),
        ("verify_storage", "Repeat health checks and compare evidence"),
    ),
    "thermal": (
        ("collect_thermal_readings", "Collect temperature and fan telemetry"),
        ("inspect_airflow", "Check external vents and airflow without opening powered equipment"),
        ("technician_service", "Ask a qualified technician to inspect cooling hardware if necessary"),
        ("verify_thermal", "Recheck temperatures under a controlled workload"),
    ),
    "power": (
        ("collect_power_events", "Review existing power and shutdown events"),
        ("inspect_external_supply", "Check accessible cables and rated external power supply"),
        ("technician_service", "Refer internal PSU or battery work to a qualified technician"),
        ("verify_power", "Observe stability after an approved intervention"),
    ),
    "software": (
        ("collect_event_logs", "Collect authorized system error summaries"),
        ("check_restore", "Confirm backup or restore options before modification"),
        ("propose_change", "Propose a reversible software fix for explicit approval"),
        ("verify_software", "Re-run the original failing test"),
    ),
}
HIGH_RISK = {"power", "battery", "mains", "high_voltage", "swollen_battery"}

@dataclass(frozen=True)
class RepairCase:
    case_id: str
    device_id: str
    category: str
    symptom: str
    evidence_refs: tuple[str, ...]
    steps: tuple[dict, ...]
    status: str = "draft"
    requires_technician: bool = False

def create_repair_case(device_id: str, category: str, symptom: str, evidence_refs=()) -> RepairCase:
    if not isinstance(device_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", device_id):
        raise ValueError("invalid device id")
    if category not in SAFE_STEPS:
        raise ValueError("unsupported diagnostic category")
    if not isinstance(symptom, str) or not (3 <= len(symptom.strip()) <= 2000):
        raise ValueError("symptom must be 3-2000 characters")
    refs = tuple(evidence_refs)
    if len(refs) > 32 or any(not isinstance(r, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,256}", r) for r in refs):
        raise ValueError("invalid evidence references")
    refs = tuple(dict.fromkeys(refs))
    steps = tuple({"step_id": key, "instruction": desc, "completed": False,
                   "requires_approval": key in {"technician_service", "propose_change"}} for key, desc in SAFE_STEPS[category])
    payload = {"device_id": device_id, "category": category, "symptom": symptom.strip(),
               "evidence_refs": refs, "steps": steps}
    case_id = "grc_" + sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
    return RepairCase(case_id, device_id, category, symptom.strip(), refs, steps,
                      requires_technician=(category == "power"))

def export_case(case: RepairCase, path: str | Path) -> Path:
    """Export to a new file; never overwrite original repair evidence."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        json.dump(asdict(case), handle, indent=2)
        handle.write("\n")
    return target
