from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
import json
import time

from .vishvakarma_rishi import DesignFinding, VishvakarmaRishi


@dataclass(frozen=True)
class ResearchLesson:
    source: str
    source_version: str
    license: str
    topic: str
    lesson: str
    evidence: str
    confidence: float = 0.5
    status: str = "candidate"
    failure_pattern: str = ""


class VishvakarmaLearning:
    """Provenance-first learning intake; candidate findings require BRAHMA review."""

    VERSION="vishvakarma-learning-v2"

    def __init__(self,root,rishi:VishvakarmaRishi|None=None):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"vishvakarma_knowledge.jsonl"
        self.rishi=rishi

    def ingest(self,x:ResearchLesson):
        if not x.source or not x.topic or not x.lesson or not x.evidence:
            raise ValueError("source, topic, lesson and evidence provenance are required")
        status=str(x.status or "candidate").strip().lower()
        if status not in {"candidate","verified","rejected"}:
            raise ValueError("unsupported learning status")
        row=asdict(x)
        row.update({
            "rishi":"Vishvakarma",
            "confidence":max(0.0,min(float(x.confidence),1.0)),
            "status":status,
            "brahma_review_required":status=="candidate",
            "learned_at":time.time(),
        })
        with self.path.open("a",encoding="utf-8") as h:
            h.write(json.dumps(row,ensure_ascii=False)+"\n")
        linked=None
        if self.rishi is not None:
            linked=self.rishi.learn(DesignFinding(
                source=f"{x.source}@{x.source_version}" if x.source_version else x.source,
                topic=x.topic,
                finding=x.lesson,
                license=x.license or "unknown",
                confidence=row["confidence"],
                evidence=x.evidence,
                version=x.source_version,
                status=status,
            ))
        return {**row,"rishi_store":linked}

    def verify(self,x:ResearchLesson):
        verified=replace(x,status="verified",confidence=max(float(x.confidence),0.8))
        return self.ingest(verified)

    def status(self):
        count=0
        if self.path.exists():
            count=sum(1 for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())
        return {
            "version":self.VERSION,
            "lessons":count,
            "brahma_review":"candidate lessons remain unverified until reviewed",
            "rishi_bound":self.rishi is not None,
        }
