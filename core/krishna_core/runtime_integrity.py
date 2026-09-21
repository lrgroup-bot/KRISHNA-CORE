from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from .config import RUNTIME_ROOT

CRITICAL_PATHS=(
    "core/krishna_core/server.py",
    "core/krishna_core/orchestrator.py",
    "core/krishna_core/agi_kernel.py",
    "core/web_validation.html",
)

def _sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def _git_head(repo:Path):
    try:
        head=(repo/".git"/"HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            ref=head[5:].strip(); p=repo/".git"/ref
            if p.exists(): return p.read_text(encoding="utf-8").strip()
            packed=repo/".git"/"packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line and not line.startswith(("#","^")):
                        sha,name=line.split(" ",1)
                        if name.strip()==ref:return sha.strip()
            return None
        return head or None
    except OSError:
        return None

class RuntimeIntegrity:
    def __init__(self,runtime_root=RUNTIME_ROOT,source_root=None):
        self.runtime=Path(runtime_root).resolve()
        self.source=Path(source_root or os.getenv("KRISHNA_SOURCE_ROOT","E:/KRISHNA-SOURCE")).resolve()
        self.manifest_path=self.runtime/"state"/"deployment"/"DEPLOYED_COMMIT.json"
    def manifest(self):
        try:
            raw=json.loads(self.manifest_path.read_text(encoding="utf-8-sig"))
            return raw if isinstance(raw,dict) else {}
        except (OSError,ValueError):
            return {}
    def status(self):
        manifest=self.manifest()
        if not manifest:
            return {"status":"UNVERIFIED","synced":False,"reason":"deployment manifest missing",
                    "manifest_path":str(self.manifest_path),"source_head":_git_head(self.source)}
        expected=manifest.get("files") or {}
        mismatches=[]; missing=[]
        for rel,sha in expected.items():
            p=self.runtime/rel
            if not p.is_file(): missing.append(rel); continue
            try:
                if _sha256(p)!=sha:mismatches.append(rel)
            except OSError:mismatches.append(rel)
        source_head=_git_head(self.source)
        deployed=str(manifest.get("commit") or "")
        source_drift=bool(source_head and deployed and source_head!=deployed)
        synced=not missing and not mismatches and not source_drift
        return {
            "status":"SYNCED" if synced else "DRIFT",
            "synced":synced,
            "commit":deployed or None,
            "branch":manifest.get("branch"),
            "deployed_at":manifest.get("deployed_at"),
            "release_ready":bool(manifest.get("release_ready",False)),
            "acceptance_status":manifest.get("acceptance_status","unknown"),
            "acceptance_completed_at":manifest.get("acceptance_completed_at"),
            "file_count":len(expected),
            "missing":missing[:100],
            "mismatches":mismatches[:100],
            "source_head":source_head,
            "source_drift":source_drift,
            "manifest_path":str(self.manifest_path),
        }
    @staticmethod
    def critical_paths(): return list(CRITICAL_PATHS)
