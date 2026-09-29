"""KRISHNA-native patterns distilled from selected open-source agent projects.

This module deliberately implements interoperable ideas rather than embedding third-party
runtimes.  It keeps KRISHNA local-first, auditable, free-only by default and compatible
with the existing action/security layers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AgentCheckpoint:
    project: str
    agent: str
    objective: str
    commit: str = ""
    branch: str = ""
    files: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()
    created_at: str = field(default_factory=_utcnow)

    @property
    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()


class AgentCheckpointLedger:
    """Atlas-style provenance without replacing Git or KRISHNA's existing runtime."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "agent-checkpoints.jsonl"

    def append(self, checkpoint: AgentCheckpoint) -> dict[str, Any]:
        record = asdict(checkpoint) | {"fingerprint": checkpoint.fingerprint}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def recent(self, limit: int = 25) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-max(1, limit):]
        return [json.loads(line) for line in lines if line.strip()]


@dataclass(frozen=True)
class ExperimentSpec:
    question: str
    hypothesis: str
    method: str
    success_metrics: tuple[str, ...]
    project: str = "KRISHNA"


class ResearchExperimentFabric:
    """OpenResearch/MiroFish-inspired evidence-first experiment planning.

    It creates reproducible experiment manifests; execution remains under KRISHNA's
    existing permission, sandbox and action gates.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, spec: ExperimentSpec, agents: Iterable[str] = ()) -> dict[str, Any]:
        payload = {
            "schema": "krishna.research-experiment.v1",
            "created_at": _utcnow(),
            "project": spec.project,
            "question": spec.question.strip(),
            "hypothesis": spec.hypothesis.strip(),
            "method": spec.method.strip(),
            "success_metrics": list(spec.success_metrics),
            "agents": list(dict.fromkeys(str(x).strip() for x in agents if str(x).strip())),
            "status": "PLANNED",
            "evidence": [],
            "result": None,
        }
        identity = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
        payload["experiment_id"] = identity
        path = self.root / f"{identity}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def record_result(self, experiment_id: str, result: dict[str, Any], evidence: Iterable[str]) -> dict[str, Any]:
        path = self.root / f"{experiment_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = "COMPLETED"
        payload["completed_at"] = _utcnow()
        payload["evidence"] = list(evidence)
        payload["result"] = result
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload


class AndroidInspectionPolicy:
    """Safe boundary for ASC-like APK inspection workflows."""

    @staticmethod
    def authorize(*, owner_authorized: bool, purpose: str, package_path: str) -> dict[str, Any]:
        suffix = Path(package_path).suffix.lower()
        allowed = bool(owner_authorized and suffix in {".apk", ".aab"})
        return {
            "allowed": allowed,
            "purpose": purpose.strip(),
            "package": Path(package_path).name,
            "mode": "STATIC_INSPECTION_ONLY",
            "constraints": [
                "owner-or-explicitly-authorized-apps-only",
                "no-credential-extraction",
                "no-auth-bypass",
                "no-malware-payload-generation",
                "sandbox-output",
            ],
        }


class LocalVoicePolicy:
    """VoiceStudio-derived local voice workflow policy; engines remain pluggable."""

    @staticmethod
    def plan(*, consent: bool, language: str, operation: str) -> dict[str, Any]:
        supported = {"tts", "stt", "clone", "dub", "transcribe", "audiobook"}
        op = operation.strip().lower()
        return {
            "allowed": bool(consent and op in supported),
            "operation": op,
            "language": language.strip(),
            "local_first": True,
            "cloud_upload": False,
            "requires_voice_owner_consent": op in {"clone", "dub"},
        }


REPO_PATTERN_CATALOG = {
    "RuView": "HAWKEYE RF/CSI sensing adapter (implemented separately)",
    "ASC": "authorized APK/AAB static-inspection boundary",
    "OpenResearch": "hypothesis -> experiment -> evidence -> result lineage",
    "MiroFish": "bounded multi-agent scenario/experiment manifests",
    "VoiceStudio": "consent-gated local voice workflow abstraction",
    "Atlas": "Git-linked agent checkpoint/provenance ledger",
    "Pi": "small composable agent/tool contracts; reuse KRISHNA runtime instead of duplicating it",
    "Agent Lightning": "retain trajectory/evaluation signals for later agent improvement, without online self-modification",
}
