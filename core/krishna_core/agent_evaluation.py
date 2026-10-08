from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Iterable


@dataclass(frozen=True)
class TrajectoryStep:
    action: str
    status: str = "completed"

    def as_dict(self):
        return asdict(self)


class AgentTrajectoryEvaluator:
    """Deterministic, local evaluator for KRISHNA action trajectories.

    This does not judge natural-language quality. It checks observable action
    behavior: required ordering, forbidden actions, failures and unexpected
    side effects. LLM judges may be layered above this later, but cannot replace
    these objective checks.
    """

    @staticmethod
    def _steps(rows: Iterable[dict]) -> list[TrajectoryStep]:
        out = []
        for row in rows or []:
            action = str(row.get("action") or row.get("name") or "").strip()
            if not action:
                continue
            out.append(TrajectoryStep(action, str(row.get("status") or "completed").lower()))
        return out

    def evaluate(
        self,
        observed: Iterable[dict],
        *,
        required_order: Iterable[str] = (),
        forbidden_actions: Iterable[str] = (),
        allowed_actions: Iterable[str] | None = None,
        fail_on_failed_step: bool = True,
    ) -> dict:
        steps = self._steps(observed)
        actions = [x.action for x in steps]
        forbidden = {str(x) for x in forbidden_actions}
        allowed = None if allowed_actions is None else {str(x) for x in allowed_actions}

        forbidden_hits = [
            {"index": i, "action": step.action}
            for i, step in enumerate(steps) if step.action in forbidden
        ]
        unexpected = [
            {"index": i, "action": step.action}
            for i, step in enumerate(steps) if allowed is not None and step.action not in allowed
        ]
        failed_steps = [
            {"index": i, **step.as_dict()}
            for i, step in enumerate(steps)
            if step.status in {"fail", "failed", "error", "blocked"}
        ]

        required = [str(x) for x in required_order]
        positions = []
        cursor = 0
        missing = []
        for action in required:
            try:
                index = actions.index(action, cursor)
            except ValueError:
                missing.append(action)
                continue
            positions.append({"action": action, "index": index})
            cursor = index + 1

        passed = (
            not missing
            and not forbidden_hits
            and not unexpected
            and (not fail_on_failed_step or not failed_steps)
        )
        return {
            "passed": passed,
            "observed": [x.as_dict() for x in steps],
            "required_order": required,
            "required_positions": positions,
            "missing_required": missing,
            "forbidden_hits": forbidden_hits,
            "unexpected_actions": unexpected,
            "failed_steps": failed_steps,
            "policy": "objective action evidence only; final-answer quality requires separate evaluation",
        }


class EvaluatorCalibration:
    """Proves an evaluator distinguishes known-good from known-bad fixtures."""

    def calibrate(
        self,
        evaluator: Callable[[object], object],
        *,
        known_good: Iterable[object],
        known_bad: Iterable[object],
    ) -> dict:
        good_rows = []
        bad_rows = []

        def verdict(value):
            result = evaluator(value)
            if isinstance(result, dict):
                return bool(result.get("passed"))
            return bool(result)

        for index, case in enumerate(known_good):
            try:
                passed = verdict(case)
                good_rows.append({"index": index, "passed": passed})
            except Exception as exc:
                good_rows.append({"index": index, "passed": False, "error": type(exc).__name__})

        for index, case in enumerate(known_bad):
            try:
                rejected = not verdict(case)
                bad_rows.append({"index": index, "rejected": rejected})
            except Exception as exc:
                bad_rows.append({"index": index, "rejected": True, "error": type(exc).__name__})

        good_ok = bool(good_rows) and all(x["passed"] for x in good_rows)
        bad_ok = bool(bad_rows) and all(x["rejected"] for x in bad_rows)
        return {
            "calibrated": good_ok and bad_ok,
            "known_good": good_rows,
            "known_bad": bad_rows,
            "good_pass_rate": (
                sum(1 for x in good_rows if x["passed"]) / len(good_rows) if good_rows else 0.0
            ),
            "bad_reject_rate": (
                sum(1 for x in bad_rows if x["rejected"]) / len(bad_rows) if bad_rows else 0.0
            ),
            "policy": "an evaluator is trusted only after known-good passes and deliberately-wrong cases fail",
        }
