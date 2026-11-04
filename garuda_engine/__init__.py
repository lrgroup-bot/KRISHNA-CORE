"""GARUDA Engine: deterministic hardware/network triage and capacity admission.

Standard-library only. No device probing or stress testing occurs on import.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Status(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NOT_TESTED = "NOT_TESTED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class Device:
    id: str
    category: str
    connection: str
    enrolled: bool = False
    selected: bool = False
    admin_approved: bool = False
    critical_data: bool = False
    clicking: bool = False
    unstable: bool = False


@dataclass(frozen=True)
class TestPlan:
    device_id: str
    profile: str
    checks: tuple[str, ...]
    status: Status
    reason: str
    destructive_allowed: bool = False


CHECKS = {
    "storage": ("identity", "usb_bridge_capabilities", "smart_if_supported", "temperature", "read_only_scan_if_safe"),
    "computer": ("hardware_inventory", "cpu_stress", "memory_stability", "gpu_stress_if_present", "thermal_watch", "network"),
    "switch": ("port_inventory", "link_negotiation", "snmp_if_authorized", "throughput_with_endpoints", "poe_with_tester"),
    "router": ("interface_inventory", "latency", "packet_loss", "throughput_with_endpoints", "management_if_authorized"),
    "display": ("edid_if_supported", "pixel_patterns", "input_ports", "calibrated_colorimeter_if_present"),
    "ups": ("telemetry_if_supported", "battery_status", "instrument_assisted_checks"),
}


def diagnostic_plan(device: Device) -> TestPlan:
    """Plan full PRO coverage; do not run anything or imply unperformed checks passed."""
    if not device.selected:
        return TestPlan(device.id, "FULL_PRO", (), Status.BLOCKED, "Device not explicitly selected")
    if device.category == "computer" and not device.enrolled:
        return TestPlan(device.id, "FULL_PRO", (), Status.BLOCKED, "Remote host not enrolled")
    if not device.admin_approved:
        return TestPlan(device.id, "FULL_PRO", (), Status.BLOCKED, "Target authorization required")
    if device.category == "storage" and (device.critical_data or device.clicking or device.unstable):
        return TestPlan(device.id, "RECOVERY_PROTECT", ("identity_if_safe",), Status.BLOCKED,
                        "Suspected failing or critical-data storage: no stress, SMART self-test, surface scan or writes")
    checks = CHECKS.get(device.category)
    if checks is None:
        return TestPlan(device.id, "FULL_PRO", ("visual_inspection", "identify_interfaces"), Status.NOT_TESTED,
                        "No device-specific diagnostic adapter installed")
    return TestPlan(device.id, "FULL_PRO", checks, Status.NOT_TESTED,
                    "Plan only: supported tests require approved adapters, safety preflight and evidence")


@dataclass(frozen=True)
class Worker:
    id: str
    online: bool
    healthy: bool
    cpu_cores: int
    cpu_utilization: float
    ram_total_gb: float
    ram_used_gb: float
    vram_total_gb: float = 0
    vram_used_gb: float = 0
    temperature_c: Optional[float] = None
    max_safe_temperature_c: Optional[float] = None


@dataclass(frozen=True)
class Job:
    id: str
    cpu_cores: int
    ram_gb: float
    vram_gb: float = 0
    priority: int = 0


def can_admit(worker: Worker, job: Job, ram_reserve_gb: float = 4,
              cpu_utilization_ceiling: float = 0.80, vram_reserve_gb: float = 0.5) -> bool:
    """Conservative admission, not a guarantee of performance."""
    if not worker.online or not worker.healthy:
        return False
    if worker.temperature_c is not None and worker.max_safe_temperature_c is not None:
        if worker.temperature_c >= worker.max_safe_temperature_c:
            return False
    if not (0 <= worker.cpu_utilization <= 1):
        return False
    if worker.cpu_utilization >= cpu_utilization_ceiling:
        return False
    if job.cpu_cores < 1 or job.ram_gb <= 0 or job.vram_gb < 0:
        return False
    if job.cpu_cores > worker.cpu_cores * max(0, cpu_utilization_ceiling - worker.cpu_utilization):
        return False
    if worker.ram_total_gb - worker.ram_used_gb - ram_reserve_gb < job.ram_gb:
        return False
    if job.vram_gb > 0 and worker.vram_total_gb - worker.vram_used_gb - vram_reserve_gb < job.vram_gb:
        return False
    return True


def select_worker(workers: list[Worker], job: Job) -> Optional[str]:
    """Deterministic placement; jobs are not started by this function."""
    eligible = [w for w in workers if can_admit(w, job)]
    if not eligible:
        return None
    eligible.sort(key=lambda w: (w.cpu_utilization, -(w.ram_total_gb - w.ram_used_gb), w.id))
    return eligible[0].id
