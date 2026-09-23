from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time

from .vishvakarma_curriculum import CURRICULUM, RULES


@dataclass
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
    VERSION = "vishvakarma-learning-v3"

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "vishvakarma_knowledge.jsonl"

    def ingest(self, lesson: ResearchLesson):
        if not lesson.source or not lesson.lesson or not lesson.evidence:
            raise ValueError("provenance and evidence are required")
        if lesson.status not in {"candidate", "verified", "rejected", "superseded"}:
            raise ValueError("invalid design-learning status")
        confidence = max(0.0, min(float(lesson.confidence), 1.0))
        row = asdict(lesson)
        row.update({
            "confidence": confidence,
            "rishi": "Vishvakarma",
            "brahma_review_required": lesson.status == "candidate",
            "learned_at": time.time(),
        })
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def verify(self, lesson: ResearchLesson):
        verified = ResearchLesson(**{
            **asdict(lesson),
            "status": "verified",
            "confidence": max(float(lesson.confidence), 0.8),
        })
        return self.ingest(verified)

    def list(self, *, topic="", status=None, limit=200):
        if not self.path.exists():
            return []
        q=str(topic or "").strip().lower()
        wanted=None if status in (None,"") else str(status).strip().lower()
        rows=[]
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except Exception:
                continue
            if wanted and str(row.get("status") or "").lower()!=wanted:
                continue
            haystack=" ".join(str(row.get(x) or "") for x in ("topic","lesson","evidence","failure_pattern")).lower()
            if q and q not in haystack:
                continue
            rows.append(row)
        return rows[-max(1,min(int(limit),1000)):]

    def status(self):
        rows=self.list(limit=1000)
        return {
            "version":self.VERSION,
            "candidate":sum(1 for x in rows if x.get("status")=="candidate"),
            "verified":sum(1 for x in rows if x.get("status")=="verified"),
            "rejected":sum(1 for x in rows if x.get("status")=="rejected"),
            "superseded":sum(1 for x in rows if x.get("status")=="superseded"),
            "path":str(self.path),
            "provenance_required":True,
        }

    def curriculum(self):
        return {"curriculum": CURRICULUM, "rules": list(RULES), "version": self.VERSION}
