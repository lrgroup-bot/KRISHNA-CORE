"""GARUDA diagnostic plan: fail-closed read-only discovery and explicit repair approval.

No device access, shell execution, network scanning or repair is performed here.
The existing pairing/authentication and executor components own those operations.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

DeviceKind = Literal["windows", "linux", "android", "esp32"]
READ_ONLY = {
    "windows": ("system_inventory", "event_log_summary", "disk_smart_summary", "driver_health"),
    "linux": ("system_inventory", "journal_error_summary", "disk_smart_summary", "service_health"),
    "android": ("device_properties", "battery_health", "storage_summary", "package_inventory"),
    "esp32": ("firmware_identity", "sensor_health", "power_telemetry"),
}
DANGEROUS = frozenset({"flash_firmware", "erase_data", "disable_security", "factory_reset", "modify_boot", "replace_driver", "remove_package"})

@dataclass(frozen=True)
class DiagnosticPlan:
    device_id: str
    device_kind: DeviceKind
    actions: tuple[str, ...]
    paired: bool
    approval_required: bool = False

def plan_diagnostics(device_id: str, device_kind: DeviceKind, *, paired: bool, requested_actions=None) -> DiagnosticPlan:
    if not paired:
        raise PermissionError("device must be paired and authorized")
    if not isinstance(device_id, str) or not (1 <= len(device_id) <= 128) or any(c.isspace() for c in device_id):
        raise ValueError("invalid device identity")
    if device_kind not in READ_ONLY:
        raise ValueError("unsupported device type")
    actions = tuple(READ_ONLY[device_kind] if requested_actions is None else requested_actions)
    if len(actions) > 32 or not all(isinstance(x, str) and x in READ_ONLY[device_kind] for x in actions):
        raise PermissionError("diagnostic planner only permits read-only allowlisted actions")
    return DiagnosticPlan(device_id=device_id, device_kind=device_kind, actions=actions, paired=True)

def classify_repair_action(action: str) -> dict:
    if not isinstance(action, str) or not action:
        raise ValueError("invalid action")
    # A separate, authenticated executor must validate and approve all mutations.
    return {"action": action, "executable": False, "approval_required": True,
            "high_risk": action in DANGEROUS, "executor": "not_bound"}
