"""KRISHNA evidence-first decision gate.

Inspired by decision-system boundary principles: judgments are evidence, never
authority. A task is not DONE merely because execution returned successfully.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class WorkState(str, Enum):
    PROPOSED = "PROPOSED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    OBSERVED = "OBSERVED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    BLOCKED = "BLOCKED"


class Decision(str, Enum):
    PROCEED = "PROCEED"
    GATHER_EVIDENCE = "GATHER_EVIDENCE"
    ASK_OWNER = "ASK_OWNER"
    REJECT = "REJECT"
    ROLLBACK = "ROLLBACK"


@dataclass(frozen=True)
class Evidence:
    source: str
    kind: str
    value: Any
    independent: bool = False


@dataclass
class EvidenceReceipt:
    action: str
    project: str = "KRISHNA"
    state: WorkState = WorkState.PROPOSED
    reason: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    rollback_point: str | None = None
    owner_approval: bool | None = None
    outcome: Any = None

    def add_evidence(self, source: str, kind: str, value: Any, *, independent: bool = False):
        self.evidence.append(Evidence(source, kind, value, independent))
        return self

    @property
    def independently_verified(self) -> bool:
        return any(e.independent and bool(e.value) for e in self.evidence)

    def execute(self, *, rollback_point: str | None = None):
        if self.state is not WorkState.PROPOSED:
            raise ValueError("only PROPOSED work may execute")
        self.rollback_point = rollback_point
        self.state = WorkState.EXECUTED
        return self

    def verify(self):
        if self.state is not WorkState.EXECUTED:
            raise ValueError("verification requires EXECUTED state")
        if not self.independently_verified:
            raise ValueError("independent evidence is required before VERIFIED")
        self.state = WorkState.VERIFIED
        return self

    def observe(self, outcome: Any):
        if self.state is not WorkState.VERIFIED:
            raise ValueError("observation requires VERIFIED state")
        self.outcome = outcome
        self.state = WorkState.OBSERVED
        return self

    def rollback(self, reason: str):
        if not self.rollback_point:
            raise ValueError("rollback requires a rollback point")
        self.reason = reason
        self.state = WorkState.ROLLED_BACK
        return self

    def as_dict(self):
        return {
            "action": self.action, "project": self.project, "state": self.state.value,
            "reason": self.reason,
            "evidence": [e.__dict__ for e in self.evidence],
            "tests_run": list(self.tests_run), "rollback_point": self.rollback_point,
            "owner_approval": self.owner_approval, "outcome": self.outcome,
            "independently_verified": self.independently_verified,
        }


def classify_step(*, deterministic: bool = False, generative: bool = False) -> str:
    if deterministic and generative:
        raise ValueError("a step cannot be both deterministic and generative")
    if deterministic:
        return "EXACT"
    if generative:
        return "GENERATIVE"
    return "JUDGMENT"


def decide(*, evidence_complete: bool, authorized: bool, verification_passed: bool | None,
           consequential: bool = False, owner_approved: bool = False) -> Decision:
    if not evidence_complete:
        return Decision.GATHER_EVIDENCE
    if not authorized:
        return Decision.REJECT
    if consequential and not owner_approved:
        return Decision.ASK_OWNER
    if verification_passed is False:
        return Decision.ROLLBACK
    if verification_passed is None:
        return Decision.GATHER_EVIDENCE
    return Decision.PROCEED


def require_independent_verification(evidence: Iterable[Evidence]) -> bool:
    return any(item.independent and bool(item.value) for item in evidence)
