from __future__ import annotations

from pathlib import Path
import base64
import hashlib
import json
import os
import shutil
import threading
import time
import uuid


class HawkeyeMediaSyncStore:
    """Resumable, local-only Hawkeye media inbox.

    Uploads are written as .partial files, are resumable at an exact byte offset,
    and are promoted atomically only after size + SHA-256 verification succeeds.
    This is a transport/store boundary only; it never sends media to cloud models.
    """

    VERSION = "hawkeye-media-sync-v1"
    MAX_BYTES = 128 * 1024 * 1024
    MAX_CHUNK_BYTES = 512 * 1024
    MIN_FREE_BYTES = 512 * 1024 * 1024

    def __init__(self, runtime_root: str | Path):
        self.root = Path(runtime_root).resolve() / "mobile" / "inbox" / "hawkeye"
        self.partial = self.root / ".partial"
        self.receipts = self.root / "receipts"
        self.partial.mkdir(parents=True, exist_ok=True)
        self.receipts.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @staticmethod
    def _safe(value: str, default="evidence"):
        text="".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_.")
        clean=(text[:160] or default).strip(".")
        return clean or default

    @staticmethod
    def _digest(value: str):
        value=str(value or "").strip().lower()
        if len(value)!=64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("sha256 must be a 64-character hex digest")
        return value

    def _state_path(self, upload_id):
        return self.partial / f"{self._safe(upload_id)}.json"

    def _part_path(self, upload_id):
        return self.partial / f"{self._safe(upload_id)}.partial"

    def _load(self, upload_id):
        path=self._state_path(upload_id)
        if not path.is_file():
            raise KeyError("media sync session not found")
        row=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(row,dict):
            raise RuntimeError("media sync state is invalid")
        return row

    def _save(self,row):
        path=self._state_path(row["upload_id"])
        tmp=path.with_suffix(".tmp")
        tmp.write_text(json.dumps(row,indent=2,sort_keys=True),encoding="utf-8")
        tmp.replace(path)

    def start(self, *, observation_id, session_id, filename, size_bytes, sha256,
              content_type="application/octet-stream", modality="unknown", metadata=None):
        size=int(size_bytes)
        if size<=0 or size>self.MAX_BYTES:
            raise ValueError(f"media size must be 1..{self.MAX_BYTES} bytes")
        digest=self._digest(sha256)
        observation=self._safe(observation_id,"observation")
        session=self._safe(session_id,"mobile-evidence")
        name=self._safe(filename or f"{observation}.bin",f"{observation}.bin")
        media_modality=self._safe(modality,"unknown").lower()
        if media_modality not in {"image","audio","video"}:
            raise ValueError("modality must be image, audio, or video")
        free=shutil.disk_usage(self.root).free
        if free < max(self.MIN_FREE_BYTES,size*2):
            raise RuntimeError("insufficient E-drive free space for verified media sync")

        # Stable upload id makes retries idempotent for the same observation/hash.
        upload_id=hashlib.sha256(f"{observation}:{digest}".encode()).hexdigest()[:32]
        state_path=self._state_path(upload_id)
        part_path=self._part_path(upload_id)
        final_path=self.root / f"{observation}-{digest[:16]}-{name}"

        with self._lock:
            if final_path.is_file() and final_path.stat().st_size==size:
                actual=hashlib.sha256(final_path.read_bytes()).hexdigest()
                if actual==digest:
                    return {
                        "version":self.VERSION,"upload_id":upload_id,"status":"SYNCED",
                        "next_offset":size,"size_bytes":size,"sha256":digest,
                        "retained_pc":True,"verified":True,"path":str(final_path),
                    }
            if state_path.is_file():
                row=self._load(upload_id)
                if int(row["size_bytes"])!=size or row["sha256"]!=digest:
                    raise RuntimeError("media sync session metadata conflict")
            else:
                row={
                    "version":self.VERSION,"upload_id":upload_id,
                    "observation_id":observation,"session_id":session,"filename":name,
                    "size_bytes":size,"sha256":digest,
                    "content_type":str(content_type or "application/octet-stream")[:160],
                    "modality":media_modality,
                    "metadata":dict(metadata or {}),"status":"WAITING_FOR_TRUSTED_LAN",
                    "created_at":time.time(),"updated_at":time.time(),
                    "final_path":str(final_path),
                }
                self._save(row)
            offset=part_path.stat().st_size if part_path.is_file() else 0
            if offset>size:
                part_path.unlink(missing_ok=True)
                offset=0
            row["status"]="TRANSFERRING" if offset else "WAITING_FOR_TRUSTED_LAN"
            row["updated_at"]=time.time()
            self._save(row)
            return {**row,"next_offset":offset,"retained_pc":False,"verified":False}

    def append(self, upload_id, offset, chunk_b64):
        raw=base64.b64decode(str(chunk_b64 or ""),validate=True)
        if not raw or len(raw)>self.MAX_CHUNK_BYTES:
            raise ValueError(f"chunk must be 1..{self.MAX_CHUNK_BYTES} bytes")
        with self._lock:
            row=self._load(upload_id)
            if row.get("status")=="SYNCED":
                return {**row,"next_offset":int(row["size_bytes"]),"retained_pc":True,"verified":True}
            part=self._part_path(upload_id)
            current=part.stat().st_size if part.is_file() else 0
            requested=int(offset)
            if requested!=current:
                return {
                    "version":self.VERSION,"upload_id":row["upload_id"],"status":"RESUME_REQUIRED",
                    "next_offset":current,"size_bytes":int(row["size_bytes"]),
                }
            if current+len(raw)>int(row["size_bytes"]):
                raise ValueError("chunk exceeds declared media size")
            with part.open("ab") as fh:
                fh.write(raw)
                fh.flush()
                os.fsync(fh.fileno())
            next_offset=current+len(raw)
            row["status"]="VERIFYING" if next_offset==int(row["size_bytes"]) else "TRANSFERRING"
            row["updated_at"]=time.time()
            self._save(row)
            return {
                "version":self.VERSION,"upload_id":row["upload_id"],"status":row["status"],
                "next_offset":next_offset,"size_bytes":int(row["size_bytes"]),
            }

    def complete(self, upload_id):
        with self._lock:
            row=self._load(upload_id)
            part=self._part_path(upload_id)
            expected_size=int(row["size_bytes"])
            if not part.is_file() or part.stat().st_size!=expected_size:
                current=part.stat().st_size if part.is_file() else 0
                return {
                    "version":self.VERSION,"upload_id":row["upload_id"],
                    "status":"RESUME_REQUIRED","next_offset":current,
                    "size_bytes":expected_size,"retained_pc":False,"verified":False,
                }
            digest=hashlib.sha256()
            with part.open("rb") as fh:
                for chunk in iter(lambda:fh.read(1024*1024),b""):
                    digest.update(chunk)
            actual=digest.hexdigest()
            if actual!=row["sha256"]:
                row["status"]="FAILED";row["error"]="sha256 mismatch";row["updated_at"]=time.time()
                self._save(row)
                raise ValueError("media SHA-256 verification failed")
            final=Path(row["final_path"])
            final.parent.mkdir(parents=True,exist_ok=True)
            part.replace(final)
            row["status"]="SYNCED";row["verified"]=True;row["retained_pc"]=True
            row["completed_at"]=time.time();row["updated_at"]=row["completed_at"]
            receipt=self.receipts/f"{row['upload_id']}.json"
            receipt.write_text(json.dumps(row,indent=2,sort_keys=True),encoding="utf-8")
            self._save(row)
            return {
                "version":self.VERSION,"upload_id":row["upload_id"],"status":"SYNCED",
                "next_offset":expected_size,"size_bytes":expected_size,"sha256":actual,
                "retained_pc":True,"verified":True,"pc_receipt_id":row["upload_id"],
                "path":str(final),
            }

    def status(self, upload_id):
        with self._lock:
            row=self._load(upload_id)
            part=self._part_path(upload_id)
            offset=part.stat().st_size if part.is_file() else (
                int(row["size_bytes"]) if row.get("status")=="SYNCED" else 0
            )
            return {**row,"next_offset":offset}
