from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json
import math
import time
import uuid


REQUIRED_RELEASE_GATES = (
    "requirements", "unit", "integration", "backend_api", "browser_e2e",
    "ui_geometry", "visual_regression", "responsive", "accessibility",
    "security", "adversarial", "restart_recovery", "package_build",
    "installed_artifact",
)


@dataclass
class WorkItem:
    id: str
    role: str
    estimate_minutes: float
    dependencies: tuple[str, ...] = ()
    parallelizable: bool = True
    critical: bool = True


@dataclass
class TeamPlan:
    deadline_minutes: float
    serial_minutes: float
    parallel_minutes: float
    recommended_workers: int
    assignments: dict[str, int]
    predicted_minutes: float
    resource_limited: bool


class DeadlineHR:
    """Deadline-driven team sizing for KRISHNA's bounded ephemeral workers."""

    def plan(self, work: Iterable[WorkItem], deadline_minutes: float, max_workers: int = 8) -> TeamPlan:
        items = list(work)
        deadline = max(1.0, float(deadline_minutes))
        cap = max(1, int(max_workers))
        serial = sum(x.estimate_minutes for x in items if not x.parallelizable)
        parallel = sum(x.estimate_minutes for x in items if x.parallelizable)
        usable = max(1.0, deadline - serial)
        needed = max(1, math.ceil(parallel / usable)) if parallel else 1
        workers = min(cap, needed)
        roles: dict[str, float] = {}
        for item in items:
            roles[item.role] = roles.get(item.role, 0.0) + item.estimate_minutes
        total = sum(roles.values()) or 1.0
        assignments = {role: max(1, round(workers * minutes / total)) for role, minutes in roles.items()}
        while sum(assignments.values()) > cap and len(assignments) > 1:
            role = max(assignments, key=lambda k: assignments[k])
            if assignments[role] <= 1:
                break
            assignments[role] -= 1
        predicted = serial + (parallel / workers if workers else parallel)
        return TeamPlan(deadline, serial, parallel, workers, assignments, predicted, needed > cap)


@dataclass
class ElementGeometry:
    selector: str
    x: float
    y: float
    width: float
    height: float
    visible: bool = True
    text: str = ""
    z_index: int = 0
    ancestors: list[str] = field(default_factory=list)
    scroll_width: float = 0
    scroll_height: float = 0
    client_width: float = 0
    client_height: float = 0
    overflow_x: str = "visible"
    overflow_y: str = "visible"
    interactive: bool = False
    pointer_events: str = "auto"
    opacity: float = 1.0

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


class UIGeometryVerifier:
    """Objective X/Y layout checks. BrowserOperator supplies measured DOM boxes."""

    def inspect(self, elements: Iterable[ElementGeometry], viewport_width: int, viewport_height: int) -> list[dict[str, Any]]:
        rows = list(elements)
        findings: list[dict[str, Any]] = []
        for el in rows:
            if not el.visible:
                continue
            if el.width <= 0 or el.height <= 0:
                findings.append({"type": "zero_area", "selector": el.selector})
            if el.x < -2 or el.right > viewport_width + 2:
                findings.append({
                    "type": "viewport_overflow", "selector": el.selector,
                    "box": [el.x, el.y, el.right, el.bottom],
                    "viewport": [viewport_width, viewport_height],
                })
            if el.text.strip():
                clipped_x=el.scroll_width > el.client_width + 2 and el.overflow_x in {"hidden","clip"}
                clipped_y=el.scroll_height > el.client_height + 2 and el.overflow_y in {"hidden","clip"}
                if clipped_x or clipped_y:
                    findings.append({"type":"clipped_content","selector":el.selector,
                                     "horizontal":clipped_x,"vertical":clipped_y})
            if el.interactive and (el.pointer_events=="none" or el.opacity <= 0.01):
                findings.append({"type":"non_interactable_visible_control","selector":el.selector,
                                 "pointer_events":el.pointer_events,"opacity":el.opacity})
        for i, left in enumerate(rows):
            if not left.visible:
                continue
            for right in rows[i + 1:]:
                if not right.visible or left.z_index != right.z_index:
                    continue
                if left.selector in (right.ancestors or []) or right.selector in (left.ancestors or []):
                    continue
                ox = min(left.right, right.right) - max(left.x, right.x)
                oy = min(left.bottom, right.bottom) - max(left.y, right.y)
                if ox > 2 and oy > 2:
                    area = ox * oy
                    smaller = min(left.width * left.height, right.width * right.height)
                    if smaller > 0 and area / smaller > 0.35:
                        findings.append({
                            "type": "substantial_overlap",
                            "selectors": [left.selector, right.selector],
                            "overlap_ratio": round(area / smaller, 4),
                        })
        return findings


@dataclass
class RegressionRecord:
    bug_id: str
    project: str
    trigger: str
    root_cause: str
    regression_test: str
    verification: str
    created_at: float = field(default_factory=time.time)


class ImmuneMemory:
    """Persistent bug-to-regression memory. Restarting KRISHNA must not forget learned defects."""

    def __init__(self, path: str | Path | None=None) -> None:
        self.path=Path(path).resolve() if path else None
        self.records: dict[str, RegressionRecord] = {}
        self._load()

    def _load(self):
        if not self.path or not self.path.is_file():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            for row in raw.get("records") or []:
                record=RegressionRecord(**row)
                self.records[record.bug_id]=record
        except Exception:
            self.records={}

    def _save(self):
        if not self.path:return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(self.path.suffix+".tmp")
        tmp.write_text(json.dumps({"version":1,"records":[asdict(x) for x in self.records.values()]},indent=2),encoding="utf-8")
        tmp.replace(self.path)

    def immunize(self, project: str, trigger: str, root_cause: str, regression_test: str, verification: str) -> RegressionRecord:
        if not regression_test.strip():
            raise ValueError("regression_test is required before a defect can be immunized")
        digest = sha256(f"{project}|{trigger}|{root_cause}".encode()).hexdigest()[:12]
        record = RegressionRecord(f"BUG-{digest.upper()}", project, trigger, root_cause, regression_test, verification)
        self.records[record.bug_id] = record
        self._save()
        return record

    def required_tests(self, project: str) -> list[str]:
        return sorted({r.regression_test for r in self.records.values() if r.project == project})


@dataclass
class GateEvidence:
    gate: str
    passed: bool
    evidence: list[str] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)


class CompletionProof:
    """Evidence-based Definition of Done. Percent-complete cannot override a failed gate."""

    def __init__(self, required_gates: Iterable[str] = REQUIRED_RELEASE_GATES):
        self.required_gates = tuple(required_gates)

    def certify(self, project: str, build_hash: str, gates: Iterable[GateEvidence], mutation_detection: float | None = None) -> dict[str, Any]:
        by_name = {g.gate: g for g in gates}
        missing = [name for name in self.required_gates if name not in by_name]
        failed = [name for name in self.required_gates if name in by_name and not by_name[name].passed]
        critical = [x for g in by_name.values() for x in g.critical_failures]
        passed = not missing and not failed and not critical
        return {
            "certificate_id": str(uuid.uuid4()),
            "project": project,
            "build_hash": build_hash,
            "required_gates": list(self.required_gates),
            "missing_gates": missing,
            "failed_gates": failed,
            "critical_failures": critical,
            "mutation_detection": mutation_detection,
            "verdict": "RELEASE_GATES_PASSED" if passed else "NOT_COMPLETE",
            "passed": passed,
            "evidence": {name: asdict(g) for name, g in by_name.items()},
            "created_at": time.time(),
        }


class ProjectPerfectionLoop:
    """Coordinator contract joining HR, browser QA, immune memory and release proof.

    Tool-specific execution remains delegated to KRISHNA's existing BrowserOperator,
    DevelopmentOperator, CriticVerifier, KABACH and ephemeral Shishya runtime.
    """

    def __init__(self, max_workers: int = 8, immune_path: str | Path | None=None):
        self.hr = DeadlineHR()
        self.geometry = UIGeometryVerifier()
        self.immune = ImmuneMemory(immune_path)
        self.completion = CompletionProof()
        self.max_workers = max(1, int(max_workers))

    @staticmethod
    def page_state_key(route: str, viewport: str, state: str, action: str) -> str:
        return sha256(f"{route}|{viewport}|{state}|{action}".encode()).hexdigest()[:20]

    @staticmethod
    def discovery_contract() -> dict[str, Any]:
        return {
            "browser": {
                "discover_routes": True,
                "discover_controls": True,
                "capture_console": True,
                "capture_network_failures": True,
                "capture_dom_geometry": True,
                "capture_accessibility_tree": True,
                "capture_screenshots": True,
                "generate_deterministic_regressions": True,
            },
            "states": [
                "default", "hover", "focus", "pressed", "disabled", "loading",
                "success", "error", "empty", "long_text", "offline",
            ],
            "viewports": [375, 390, 430, 768, 1024, 1366, 1440, 1920, 2560],
            "adversarial": [
                "empty_input", "oversized_input", "unicode", "double_click",
                "refresh_mid_action", "api_500", "api_timeout", "offline",
                "permission_denied", "service_restart",
            ],
            "post_package_retest": True,
            "rule": "objective repaired defects require a regression detector before closure",
        }

    def status(self) -> dict[str, Any]:
        return {
            "max_workers": self.max_workers,
            "required_release_gates": list(self.completion.required_gates),
            "immune_records": len(self.immune.records),
            "discovery": self.discovery_contract(),
        }
