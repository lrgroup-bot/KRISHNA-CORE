from __future__ import annotations

"""Rishi Vishvakarma: provenance-preserving design, electronics and engineering-craft curator."""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time


@dataclass
class DesignFinding:
    source: str
    topic: str
    finding: str
    license: str = "unknown"
    confidence: float = 0.5
    evidence: str = ""
    version: str = ""
    learned_at: float = 0.0

    def normalized(self):
        row = asdict(self)
        row["learned_at"] = self.learned_at or time.time()
        row["confidence"] = max(0.0, min(float(self.confidence), 1.0))
        return row


class VishvakarmaRishi:
    VERSION = "vishvakarma-rishi-v3"
    DOMAINS = (
        "design-systems", "ui-ux", "typography", "spacing", "responsive-ui",
        "component-architecture", "image-to-code", "visual-diff",
        "browser-testing", "accessibility", "design-drift", "frontend-quality",
        "ui-repair",
        "electronics", "electrical-systems", "pcb-repair", "power-electronics",
        "embedded-hardware", "sensors", "motors", "instrumentation",
        "fault-isolation", "repair-verification", "salvage-reuse", "hardware-fabrication",
    )

    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "vishvakarma_findings.jsonl"

    def learn(self, finding: DesignFinding):
        if not finding.source or not finding.finding or not finding.evidence:
            raise ValueError("provenance, finding and evidence are required")
        row = finding.normalized()
        row["rishi"] = "Vishvakarma"
        row["status"] = "candidate"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return {"stored": True, "rishi": "Vishvakarma", "path": str(self.path), "finding": row}

    def retrieve(self, topic, limit=20):
        if not self.path.exists():
            return []
        q = str(topic or "").strip().lower()
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            haystack = " ".join(str(row.get(x) or "") for x in ("topic", "finding", "evidence")).lower()
            if not q or q in haystack:
                rows.append(row)
        return rows[-max(1, min(int(limit), 200)):]

    def status(self):
        return {
            "name": "Rishi Vishvakarma",
            "version": self.VERSION,
            "domains": list(self.DOMAINS),
            "knowledge_path": str(self.path),
            "provenance_required": True,
            "authority": "design/electronics/engineering knowledge candidate; domain verification + BRAHMA/Verifier gate implementation truth",
        }
