from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Mapping
import hashlib
import json
import time


_MODES = {
    "IDLE",
    "ENGAGE",
    "FOCUS",
    "PERSIST",
    "INTENSIFY",
    "EXPLORE",
    "ESCALATE",
    "RECOVER",
    "ABORT",
}


def _clamp(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


@dataclass(frozen=True)
class AMCCSignals:
    """Normalized decision signals for KRISHNA's adaptive effort controller.

    This is a software control model inspired by computational accounts of the
    anterior midcingulate/dorsal ACC.  It is deliberately not a biological
    simulation and makes no claim that KRISHNA has human feelings or cognition.
    """

    goal_value: float = 0.75
    expected_success: float = 0.65
    information_gain: float = 0.50
    urgency: float = 0.50
    owner_priority: float = 0.85
    long_term_benefit: float = 0.55
    compute_cost: float = 0.25
    time_cost: float = 0.25
    failure_cost: float = 0.35
    risk: float = 0.10
    resource_pressure: float = 0.10
    progress: float = 0.00
    uncertainty: float = 0.35
    conflict: float = 0.00
    failure_streak: int = 0

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None = None, *, failure_streak: int = 0) -> "AMCCSignals":
        values = dict(values or {})
        defaults = cls()
        numeric = {}
        for key in (
            "goal_value", "expected_success", "information_gain", "urgency",
            "owner_priority", "long_term_benefit", "compute_cost", "time_cost",
            "failure_cost", "risk", "resource_pressure", "progress",
            "uncertainty", "conflict",
        ):
            numeric[key] = _clamp(values.get(key, getattr(defaults, key)), getattr(defaults, key))
        raw_streak = values.get("failure_streak", failure_streak)
        try:
            streak = max(0, min(int(raw_streak), 1000))
        except (TypeError, ValueError):
            streak = max(0, min(int(failure_streak), 1000))
        return cls(**numeric, failure_streak=streak)


class AMCCController:
    """Adaptive effort, persistence and strategy-switch controller.

    Safety/permission policy remains authoritative.  aMCC decisions may reduce
    effort or stop a task on explicit high-risk signals, but can never grant
    permissions, approve a mutation, or promote unverified work.
    """

    schema_version = 1

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "state.json"
        self._lock = RLock()
        self._state = self._load()

    def _load(self) -> dict:
        if not self.state_path.exists():
            return {"schema_version": self.schema_version, "goals": {}}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("aMCC state must be an object")
            data.setdefault("schema_version", self.schema_version)
            data.setdefault("goals", {})
            if not isinstance(data["goals"], dict):
                data["goals"] = {}
            return data
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # A corrupt telemetry file must never prevent KRISHNA from starting.
            return {"schema_version": self.schema_version, "goals": {}}

    def _save(self) -> None:
        payload = json.dumps(self._state, ensure_ascii=False, sort_keys=True, indent=2)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(self.state_path)

    @staticmethod
    def _goal_key(project: str, goal: str) -> str:
        raw = f"{str(project).strip()}\n{str(goal).strip()}".encode("utf-8", errors="replace")
        return hashlib.sha256(raw).hexdigest()[:24]

    def _goal_state(self, project: str, goal: str) -> dict:
        key = self._goal_key(project, goal)
        goals = self._state.setdefault("goals", {})
        item = goals.setdefault(key, {
            "project": str(project),
            "goal": str(goal),
            "evaluations": 0,
            "attempts": 0,
            "failure_streak": 0,
            "successes": 0,
            "last_mode": "IDLE",
            "last_strategy": "none",
            "last_outcome": None,
            "last_error": None,
            "updated_at": 0.0,
        })
        return item

    @staticmethod
    def _score(signals: AMCCSignals) -> tuple[float, float, float]:
        benefit = (
            0.22 * signals.goal_value
            + 0.18 * signals.expected_success
            + 0.16 * signals.owner_priority
            + 0.10 * signals.information_gain
            + 0.10 * signals.urgency
            + 0.10 * signals.long_term_benefit
            + 0.08 * signals.progress
            + 0.06 * (1.0 - signals.uncertainty)
        )
        cost = (
            0.20 * signals.compute_cost
            + 0.15 * signals.time_cost
            + 0.20 * signals.failure_cost
            + 0.25 * signals.risk
            + 0.20 * signals.resource_pressure
        )
        control_demand = min(
            1.0,
            0.35 * signals.uncertainty
            + 0.25 * signals.conflict
            + 0.40 * min(1.0, signals.failure_streak / 4.0),
        )
        expected_value = max(0.0, min(1.0, benefit - 0.55 * cost))
        return expected_value, control_demand, cost

    @staticmethod
    def _choose_mode(signals: AMCCSignals, expected_value: float, control_demand: float) -> tuple[str, str, int]:
        if signals.risk >= 0.90:
            return "ABORT", "safety_gate", 0
        if signals.resource_pressure >= 0.90 and signals.urgency < 0.85:
            return "RECOVER", "resource_recovery", 0
        if signals.failure_streak >= 4:
            return "ESCALATE", "specialist_root_cause_research", 0
        if signals.failure_streak >= 2:
            return "EXPLORE", "strategy_switch", 1
        if signals.urgency >= 0.80 and expected_value >= 0.45:
            return "INTENSIFY", "increase_reasoning_and_verification", 2
        if control_demand >= 0.60 and expected_value >= 0.45:
            return "FOCUS", "suppress_lower_priority_work", 2
        if expected_value >= 0.62:
            return "PERSIST", "bounded_persistence", 2
        return "ENGAGE", "normal_execution", 1

    @staticmethod
    def _rationale(signals: AMCCSignals, mode: str, expected_value: float, control_demand: float) -> list[str]:
        reasons = [f"expected_control_value={expected_value:.3f}", f"control_demand={control_demand:.3f}"]
        if signals.failure_streak:
            reasons.append(f"failure_streak={signals.failure_streak}")
        if signals.risk >= 0.60:
            reasons.append(f"risk={signals.risk:.2f}")
        if signals.resource_pressure >= 0.70:
            reasons.append(f"resource_pressure={signals.resource_pressure:.2f}")
        if signals.uncertainty >= 0.60:
            reasons.append(f"uncertainty={signals.uncertainty:.2f}")
        if signals.urgency >= 0.75:
            reasons.append(f"urgency={signals.urgency:.2f}")
        reasons.append(f"mode={mode}")
        return reasons

    def evaluate(
        self,
        project: str,
        goal: str,
        signals: Mapping[str, Any] | None = None,
        *,
        action: str | None = None,
    ) -> dict:
        project = str(project or "").strip() or "KRISHNA"
        goal = str(goal or "").strip()
        if not goal:
            return {
                "mode": "IDLE",
                "strategy": "none",
                "execute": False,
                "retry_budget": 0,
                "control_intensity": 0.0,
                "expected_control_value": 0.0,
                "control_demand": 0.0,
                "cost": 0.0,
                "signals": asdict(AMCCSignals()),
                "rationale": ["empty_goal"],
                "safety_authority": "external_policy_remains_authoritative",
            }

        with self._lock:
            item = self._goal_state(project, goal)
            merged = dict(signals or {})
            if "failure_streak" not in merged:
                merged["failure_streak"] = int(item.get("failure_streak") or 0)
            normalized = AMCCSignals.from_mapping(merged, failure_streak=int(item.get("failure_streak") or 0))
            expected_value, control_demand, cost = self._score(normalized)
            mode, strategy, retry_budget = self._choose_mode(normalized, expected_value, control_demand)
            assert mode in _MODES
            intensity = max(0.0, min(1.0, 0.35 + 0.45 * expected_value + 0.20 * control_demand))
            now = time.time()
            item.update({
                "evaluations": int(item.get("evaluations") or 0) + 1,
                "last_mode": mode,
                "last_strategy": strategy,
                "last_action": str(action or ""),
                "last_expected_control_value": round(expected_value, 6),
                "last_control_demand": round(control_demand, 6),
                "updated_at": now,
            })
            self._save()

        return {
            "mode": mode,
            "strategy": strategy,
            "execute": mode != "ABORT",
            "retry_budget": retry_budget,
            "control_intensity": round(intensity, 4),
            "expected_control_value": round(expected_value, 4),
            "control_demand": round(control_demand, 4),
            "cost": round(cost, 4),
            "signals": asdict(normalized),
            "rationale": self._rationale(normalized, mode, expected_value, control_demand),
            "safety_authority": "permissions_policy_verification_and_owner_approval",
            "biological_claim": "none_software_control_analogy_only",
        }

    def record_outcome(
        self,
        project: str,
        goal: str,
        status: str,
        *,
        progress: float | None = None,
        error: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict:
        project = str(project or "").strip() or "KRISHNA"
        goal = str(goal or "").strip()
        status = str(status or "unknown").strip().lower()
        if not goal:
            raise ValueError("goal is required")

        success_states = {"success", "completed", "verified", "promoted"}
        failure_states = {"failed", "rejected", "error", "blocked"}
        with self._lock:
            item = self._goal_state(project, goal)
            item["attempts"] = int(item.get("attempts") or 0) + 1
            if status in success_states:
                item["successes"] = int(item.get("successes") or 0) + 1
                item["failure_streak"] = 0
            elif status in failure_states:
                item["failure_streak"] = int(item.get("failure_streak") or 0) + 1
            item["last_outcome"] = status
            item["last_error"] = str(error or "")[:1000] or None
            if progress is not None:
                item["last_progress"] = _clamp(progress, 0.0)
            if metadata:
                item["last_metadata"] = {
                    str(k): v for k, v in dict(metadata).items()
                    if isinstance(v, (str, int, float, bool)) or v is None
                }
            item["updated_at"] = time.time()
            self._save()
            return dict(item)

    def status(self, project: str | None = None, limit: int = 50) -> dict:
        project = str(project or "").strip()
        limit = max(1, min(int(limit), 500))
        with self._lock:
            rows = [
                dict(item) for item in self._state.get("goals", {}).values()
                if not project or str(item.get("project")) == project
            ]
        rows.sort(key=lambda x: float(x.get("updated_at") or 0.0), reverse=True)
        modes: dict[str, int] = {}
        for row in rows:
            mode = str(row.get("last_mode") or "IDLE")
            modes[mode] = modes.get(mode, 0) + 1
        return {
            "controller": "KRISHNA aMCC Adaptive Effort Controller",
            "schema_version": self.schema_version,
            "biological_claim": "none_software_control_analogy_only",
            "authority": "advisory_plus_explicit_high_risk_abort_never_permission_granting",
            "goals": rows[:limit],
            "goal_count": len(rows),
            "modes": modes,
        }
