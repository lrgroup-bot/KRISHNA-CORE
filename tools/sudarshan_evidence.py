"""SUDARSHAN evidence ledger: observations must be traceable, not guessed."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

@dataclass(frozen=True)
class Observation:
    feature_id: str
    kind: str
    source: str
    summary: str
    digest: str

KINDS = {"screenshot", "interaction", "accessibility", "network-metadata", "source", "manual"}

def record_observation(feature_id, kind, source, summary, content: bytes):
    for value in (feature_id, source, summary):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("nonempty evidence metadata required")
    if kind not in KINDS:
        raise ValueError("unsupported evidence type")
    if not isinstance(content, bytes) or not content:
        raise ValueError("evidence bytes required")
    return Observation(feature_id.strip(), kind, source.strip(), summary.strip(), sha256(content).hexdigest())

def feature_coverage(plan, observations):
    known = {f["name"] for f in plan["features"]}
    found = {o.feature_id for o in observations if isinstance(o, Observation)}
    unknown = found - known
    if unknown:
        raise ValueError("observations for unknown features")
    return {"observed": sorted(found), "missing": sorted(known - found), "coverage": len(found)/len(known) if known else 0, "release_ready": False}
