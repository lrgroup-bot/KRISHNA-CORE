"""KRISHNA model scout and zero-cost admission policy.

Discovery is deliberately separate from installation. Candidate models are scored and
benchmarked before KRISHNA promotes them to the active pool.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, time

@dataclass
class ModelCandidate:
    model_id: str
    source: str = "huggingface"
    task: str = "general"
    license: str = ""
    size_bytes: int = 0
    local_capable: bool = True
    cloud_free: bool = False
    quality: float = 0.0
    latency_ms: float = 0.0
    ram_bytes: int = 0
    vram_bytes: int = 0
    duplicate_of: str = ""
    notes: str = ""

class ZeroCostPolicy:
    """Hard spend guard: cloud calls are admitted only when zero-cost is known."""

    def __init__(self):
        self.max_spend_usd = 0.0
        self.exhausted_until: dict[str, float] = {}

    def mark_exhausted(self, provider: str, reset_at: float | None = None):
        # Unknown reset remains disabled until an explicit health/quota refresh clears it.
        self.exhausted_until[provider] = float(reset_at or 9_999_999_999)

    def mark_free_available(self, provider: str):
        self.exhausted_until.pop(provider, None)

    def cloud_allowed(self, provider: str, *, confirmed_free: bool, estimated_cost_usd: float = 0.0) -> bool:
        if not confirmed_free or float(estimated_cost_usd) > 0:
            return False
        until = self.exhausted_until.get(provider)
        if until is None:
            return True
        if until <= time.time():
            self.exhausted_until.pop(provider, None)
            return True
        return False

class ModelScout:
    """Evaluate candidate models without blindly downloading or activating them."""

    def __init__(self, state_path: str | Path):
        self.path = Path(state_path)
        self.rows: dict[str, dict] = {}
        if self.path.exists():
            try:
                self.rows = json.loads(self.path.read_text(encoding="utf-8")).get("models", {})
            except Exception:
                self.rows = {}

    @staticmethod
    def score(c: ModelCandidate) -> float:
        if c.duplicate_of:
            return -1.0
        # Quality dominates; latency and resource footprint break ties.
        latency_penalty = min(max(c.latency_ms, 0.0) / 10000.0, 1.0)
        ram_penalty = min(max(c.ram_bytes, 0) / (64 * 1024**3), 1.0)
        return round((c.quality * 0.75) + ((1-latency_penalty) * 0.15) + ((1-ram_penalty) * 0.10), 6)

    def evaluate(self, candidate: ModelCandidate, *, min_score: float = 0.55) -> dict:
        s = self.score(candidate)
        accepted = bool(candidate.local_capable and not candidate.duplicate_of and s >= min_score)
        row = asdict(candidate) | {
            "score": s,
            "accepted": accepted,
            "decision": "PROMOTE_LOCAL" if accepted else "REJECT_OR_HOLD",
            "evaluated_at": time.time(),
        }
        self.rows[candidate.model_id] = row
        self._save()
        return row

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"schema": 1, "models": self.rows}, indent=2), encoding="utf-8")

    def active(self):
        return [x for x in self.rows.values() if x.get("accepted")]

    def status(self):
        return {
            "source_strategy": "discover-many-benchmark-few-promote-best",
            "download_policy": "no blind bulk downloads",
            "cloud_spend_limit_usd": 0.0,
            "evaluated": len(self.rows),
            "active": len(self.active()),
        }
