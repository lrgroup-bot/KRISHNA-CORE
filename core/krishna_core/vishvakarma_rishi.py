from __future__ import annotations

"""Durable design/UI/software-craft knowledge curator for KRISHNA."""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time


@dataclass(frozen=True)
class DesignFinding:
    source: str
    topic: str
    finding: str
    license: str = "unknown"
    confidence: float = 0.5
    evidence: str = ""
    version: str = ""
    status: str = "candidate"
    learned_at: float = 0.0

    def normalized(self) -> dict:
        source=str(self.source or "").strip()
        topic=str(self.topic or "").strip()
        finding=str(self.finding or "").strip()
        evidence=str(self.evidence or "").strip()
        if not source or not topic or not finding or not evidence:
            raise ValueError("source, topic, finding and evidence are required")
        confidence=max(0.0,min(float(self.confidence),1.0))
        status=str(self.status or "candidate").strip().lower()
        if status not in {"candidate","verified","rejected","superseded"}:
            raise ValueError("unsupported Vishvakarma finding status")
        return {
            **asdict(self),
            "source":source[:1000],
            "topic":topic[:240],
            "finding":finding[:6000],
            "license":str(self.license or "unknown")[:160],
            "confidence":confidence,
            "evidence":evidence[:6000],
            "version":str(self.version or "")[:240],
            "status":status,
            "learned_at":float(self.learned_at or time.time()),
        }


class VishvakarmaRishi:
    DOMAINS=(
        "design-systems","ui-ux","typography","spacing","responsive-ui",
        "component-architecture","image-to-code","visual-diff","browser-testing",
        "accessibility","design-drift","frontend-quality","ui-repair",
    )
    VERSION="vishvakarma-rishi-v2"

    def __init__(self,root):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"vishvakarma_findings.jsonl"

    def learn(self,finding:DesignFinding):
        row=finding.normalized()
        with self.path.open("a",encoding="utf-8") as h:
            h.write(json.dumps(row,ensure_ascii=False)+"\n")
        return {"stored":True,"rishi":"Vishvakarma","path":str(self.path),"finding":row}

    def _rows(self):
        if not self.path.exists():
            return []
        rows=[]
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                value=json.loads(line)
            except ValueError:
                continue
            if isinstance(value,dict):
                rows.append(value)
        return rows

    def retrieve(self,topic,limit=20,verified_only=False):
        q=str(topic or "").strip().lower()
        if not q:
            raise ValueError("topic is required")
        rows=self._rows()
        if verified_only:
            rows=[r for r in rows if str(r.get("status") or "").lower()=="verified"]
        terms=[x for x in q.split() if x]
        def score(row):
            text=(" ".join([
                str(row.get("topic") or ""),
                str(row.get("finding") or ""),
                str(row.get("evidence") or ""),
            ])).lower()
            return sum(1 for t in terms if t in text)
        rows=[r for r in rows if score(r)>0]
        rows.sort(key=lambda r:(score(r),float(r.get("confidence") or 0),float(r.get("learned_at") or 0)),reverse=True)
        return rows[:max(1,min(int(limit),100))]

    def status(self):
        rows=self._rows()
        return {
            "name":"Rishi Vishvakarma",
            "version":self.VERSION,
            "domains":list(self.DOMAINS),
            "findings":len(rows),
            "verified":sum(1 for x in rows if x.get("status")=="verified"),
            "candidate":sum(1 for x in rows if x.get("status")=="candidate"),
            "authority":"design/UI/software-craft knowledge curator; Sudarshan remains execution/verification authority",
            "historical_claim_policy":"modern design specializations are KRISHNA roles, not claims of historical practice",
        }
