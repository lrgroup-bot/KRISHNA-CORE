from __future__ import annotations

"""Read-only transport boundary for real diagnostic evidence.

Hardware-specific collectors may write bounded JSON/JSONL evidence into an owner-
configured local inbox. KRISHNA consumes that evidence through the existing
measurement adapters. This module intentionally has no transmit/write/ECU-control
API and therefore cannot be used to actuate a vehicle or instrument.
"""

from pathlib import Path
import hashlib
import json
import time

from .diagnostic_adapters import DiagnosticAdapterRegistry


SUPPORTED = {"electronics","obd2","can","can-fd","j1939","acoustic"}


def _fingerprint(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class DiagnosticEvidenceTransport:
    VERSION="diagnostic-transport-v1"

    def __init__(self,inbox_root,adapters=None):
        self.root=Path(inbox_root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.adapters=adapters or DiagnosticAdapterRegistry()

    def status(self):
        return {
            "version":self.VERSION,
            "mode":"read-only local evidence inbox",
            "supported":sorted(SUPPORTED),
            "inbox":str(self.root),
            "transmit":False,
            "programming":False,
            "instrument_control":False,
            "ready":True,
        }

    def _resolve(self,path):
        p=Path(path)
        if not p.is_absolute():
            p=self.root/p
        p=p.resolve()
        try:
            p.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError("diagnostic evidence must stay inside the configured inbox") from exc
        if not p.is_file():
            raise FileNotFoundError(str(p))
        if p.suffix.lower() not in {".json",".jsonl"}:
            raise ValueError("diagnostic evidence must be JSON or JSONL")
        return p

    @staticmethod
    def _load(path):
        text=path.read_text(encoding="utf-8-sig")
        if path.suffix.lower()==".jsonl":
            rows=[json.loads(line) for line in text.splitlines() if line.strip()]
            return {"records":rows}
        value=json.loads(text)
        if not isinstance(value,dict):
            raise ValueError("diagnostic JSON root must be an object")
        return value

    def ingest(self,kind,path,*,source=None):
        kind=str(kind or "").strip().lower()
        if kind not in SUPPORTED:
            raise ValueError("unsupported diagnostic evidence kind")
        p=self._resolve(path)
        payload=self._load(p)
        src=str(source or payload.get("source") or p.name)[:160]
        if kind=="electronics":
            rows=payload.get("measurements") or payload.get("records") or []
            result=self.adapters.electronics.ingest(
                rows,source=src,reference_id=payload.get("reference_id"),
                captured_at=payload.get("captured_at"),
                circuit_state=payload.get("circuit_state","unknown"),
            )
        elif kind in {"obd2","can","can-fd","j1939"}:
            rows=payload.get("frames") or payload.get("records") or []
            result=self.adapters.vehicle.ingest(
                kind,rows,source=src,captured_at=payload.get("captured_at")
            )
        else:
            samples=payload.get("samples") or []
            result=self.adapters.acoustic.ingest(
                samples,payload.get("sample_rate_hz") or payload.get("sample_rate"),
                source=src,axis=payload.get("axis"),captured_at=payload.get("captured_at"),
            )
        receipt={
            "transport":self.VERSION,
            "kind":kind,
            "source_file":p.name,
            "source_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
            "ingested_at":time.time(),
            "result":result,
            "read_only":True,
            "hardware_verified":False,
            "verification_required":True,
        }
        receipt["fingerprint"]=_fingerprint({k:v for k,v in receipt.items() if k!="fingerprint"})
        return receipt
