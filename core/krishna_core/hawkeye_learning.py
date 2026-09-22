from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time
import uuid


@dataclass(frozen=True)
class LearningFinding:
    finding_id: str
    specialist: str
    title: str
    claim: str
    source_url: str
    source_type: str
    evidence_state: str
    confidence: float
    limitations: tuple[str, ...]
    retrieved_at: float

    def as_dict(self):
        return asdict(self)


class HawkeyeLearningRuntime:
    """Isolated, evidence-gated learning runtime for Hawkeye.

    KRISHNA may schedule research missions daily, but research never edits
    production behavior directly. Findings enter a ledger, candidate upgrades
    run in a sandbox, and only verified promotions may be proposed.
    """

    SPECIALISTS = {
        "perception": "What do I actually see/hear?",
        "physio": "What measurable physical signals changed?",
        "behavior": "What observable behavior occurred?",
        "temporal": "What changed compared with 5 seconds, 5 minutes or previous sessions?",
        "reasoner": "What conclusions are supported by multiple independent sources?",
    }

    RESEARCH_FIELDS = {
        "perception": ("computer vision", "audio perception", "multimodal sensing", "detection", "segmentation", "gaze", "pose"),
        "physio": ("rPPG", "thermal sensing", "radar sensing", "wearables", "biosignal quality"),
        "behavior": ("observable behavior", "HCI", "engagement", "speech patterns", "gesture patterns", "deception limitations"),
        "temporal": ("change detection", "tracking", "temporal models", "sequence analysis", "memory"),
        "reasoner": ("evidence fusion", "uncertainty", "provenance", "causal reasoning", "verification"),
    }

    ALLOWED_EVIDENCE_STATES = {"candidate", "replicated", "verified", "rejected"}

    def __init__(self, state_dir: str | Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.state_dir / "learning-ledger.jsonl"
        self.missions = self.state_dir / "missions"
        self.missions.mkdir(exist_ok=True)
        self.candidates = self.state_dir / "candidates"
        self.candidates.mkdir(exist_ok=True)

    def daily_missions(self):
        """Return KRISHNA-native daily research jobs for all Hawkeye specialists."""
        today = time.strftime("%Y-%m-%d", time.gmtime())
        return [
            {
                "mission_id": f"hawkeye-{name}-{today}",
                "agent": "hawkeye",
                "specialist": name,
                "question": question,
                "fields": list(self.RESEARCH_FIELDS[name]),
                "sources": ["peer-reviewed papers", "standards", "benchmarks", "datasets", "official documentation", "reputable open-source repositories"],
                "rules": [
                    "preserve source URL and retrieval time",
                    "separate measured evidence from interpretation",
                    "record limitations and uncertainty",
                    "cross-check important claims with independent sources",
                    "do not treat body language, gaze or physiology as proof of deception or private mental state",
                    "do not modify production code from research results",
                ],
            }
            for name, question in self.SPECIALISTS.items()
        ]

    def record_finding(self, *, specialist: str, title: str, claim: str,
                       source_url: str, source_type: str = "internet",
                       evidence_state: str = "candidate", confidence: float = 0.5,
                       limitations=None):
        specialist = specialist.strip().lower()
        if specialist not in self.SPECIALISTS:
            raise ValueError(f"unknown Hawkeye specialist: {specialist}")
        if evidence_state not in self.ALLOWED_EVIDENCE_STATES:
            raise ValueError(f"invalid evidence state: {evidence_state}")
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not str(source_url).startswith(("https://", "http://")):
            raise ValueError("source_url is required for provenance")
        row = LearningFinding(
            finding_id=str(uuid.uuid4()),
            specialist=specialist,
            title=str(title).strip(),
            claim=str(claim).strip(),
            source_url=str(source_url).strip(),
            source_type=str(source_type).strip(),
            evidence_state=evidence_state,
            confidence=confidence,
            limitations=tuple(str(x) for x in (limitations or [])),
            retrieved_at=time.time(),
        )
        with self.ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return row.as_dict()

    def propose_candidate(self, *, specialist: str, finding_ids, change_summary: str,
                          benchmark_plan: list[str], rollback_plan: str):
        specialist = specialist.strip().lower()
        if specialist not in self.SPECIALISTS:
            raise ValueError(f"unknown Hawkeye specialist: {specialist}")
        if not finding_ids:
            raise ValueError("candidate upgrade requires evidence finding_ids")
        if not benchmark_plan:
            raise ValueError("candidate upgrade requires benchmark plan")
        if not rollback_plan.strip():
            raise ValueError("candidate upgrade requires rollback plan")
        candidate_id = str(uuid.uuid4())
        row = {
            "candidate_id": candidate_id,
            "specialist": specialist,
            "finding_ids": list(finding_ids),
            "change_summary": str(change_summary).strip(),
            "benchmark_plan": list(benchmark_plan),
            "rollback_plan": str(rollback_plan).strip(),
            "status": "sandbox-only",
            "production_modified": False,
            "created_at": time.time(),
        }
        (self.candidates / f"{candidate_id}.json").write_text(
            json.dumps(row, indent=2, sort_keys=True), encoding="utf-8"
        )
        return row

    def evaluate_candidate(self, candidate_id: str, *, baseline_score: float,
                           candidate_score: float, regressions=None, security_passed=False,
                           license_passed=False):
        path = self.candidates / f"{candidate_id}.json"
        if not path.exists():
            raise KeyError(candidate_id)
        row = json.loads(path.read_text(encoding="utf-8"))
        regressions = list(regressions or [])
        improved = float(candidate_score) > float(baseline_score)
        eligible = improved and not regressions and bool(security_passed) and bool(license_passed)
        row["evaluation"] = {
            "baseline_score": float(baseline_score),
            "candidate_score": float(candidate_score),
            "regressions": regressions,
            "security_passed": bool(security_passed),
            "license_passed": bool(license_passed),
            "eligible_for_promotion_review": eligible,
            "evaluated_at": time.time(),
        }
        row["status"] = "verified-candidate" if eligible else "rejected-or-needs-work"
        row["production_modified"] = False
        path.write_text(json.dumps(row, indent=2, sort_keys=True), encoding="utf-8")
        return row
