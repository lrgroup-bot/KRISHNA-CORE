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

def _git_dir(repo:Path)->Path|None:
    marker=repo/".git"
    try:
        if marker.is_dir():return marker
        if marker.is_file():
            raw=marker.read_text(encoding="utf-8").strip()
            if raw.lower().startswith("gitdir:"):
                target=raw.split(":",1)[1].strip()
                path=Path(target)
                if not path.is_absolute():path=(repo/path).resolve()
                return path
    except OSError:
        pass
    return None

def _git_ref(repo:Path,ref:str):
    git=_git_dir(repo)
    if not git:return None
    try:
        # Linked worktrees keep HEAD locally but share branch and origin refs.
        common=git/"commondir"
        if common.is_file():
            target=Path(common.read_text(encoding="utf-8").strip())
            git=target if target.is_absolute() else (git/target).resolve()
        path=git/ref
        if path.exists():return path.read_text(encoding="utf-8").strip() or None
        packed=git/"packed-refs"
        if packed.exists():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith(("#","^")):
                    sha,name=line.split(" ",1)
                    if name.strip()==ref:return sha.strip()
    except (OSError,ValueError):
        return None
    return None

def _git_head(repo:Path):
    git=_git_dir(repo)
    if not git:return None
    try:
        head=(git/"HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: "):
            return _git_ref(repo,head[5:].strip())
        return head or None
    except OSError:
        return None

def _git_branch(repo:Path):
    git=_git_dir(repo)
    if not git:return None
    try:
        head=(git/"HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref: refs/heads/"):return head[len("ref: refs/heads/"):].strip() or None
    except OSError:
        pass
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
        source_head=_git_head(self.source)
        source_branch=_git_branch(self.source)
        if not manifest:
            remote_head=_git_ref(self.source,f"refs/remotes/origin/{source_branch}") if source_branch else None
            return {
                "status":"UNVERIFIED","synced":False,"reason":"deployment manifest missing",
                "manifest_path":str(self.manifest_path),"source_head":source_head,
                "source_branch":source_branch,"remote_head":remote_head,
                "remote_verified":bool(remote_head),
            }
        expected=manifest.get("files") or {}
        mismatches=[]; missing=[]
        for rel,sha in expected.items():
            p=self.runtime/rel
            if not p.is_file(): missing.append(rel); continue
            try:
                if _sha256(p)!=sha:mismatches.append(rel)
            except OSError:mismatches.append(rel)
        deployed=str(manifest.get("commit") or "")
        branch=str(manifest.get("branch") or source_branch or "")
        source_drift=bool(source_head and deployed and source_head!=deployed)
        remote_head=_git_ref(self.source,f"refs/remotes/origin/{branch}") if branch else None
        remote_verified=bool(remote_head)
        remote_drift=bool(source_head and remote_head and source_head!=remote_head)
        deployed_remote_drift=bool(deployed and remote_head and deployed!=remote_head)
        synced=not missing and not mismatches and not source_drift and not remote_drift
        return {
            "status":"SYNCED" if synced else "DRIFT",
            "synced":synced,
            "commit":deployed or None,
            "branch":branch or None,
            "deployed_at":manifest.get("deployed_at"),
            "file_count":len(expected),
            "missing":missing[:100],
            "mismatches":mismatches[:100],
            "source_head":source_head,
            "source_branch":source_branch,
            "source_drift":source_drift,
            "remote_head":remote_head,
            "remote_verified":remote_verified,
            "remote_drift":remote_drift,
            "deployed_remote_drift":deployed_remote_drift,
            "remote_note":"origin ref reflects the last successful git fetch; DEPLOY_KRISHNA_ONCE fetches origin before deployment",
            "manifest_path":str(self.manifest_path),
        }
    @staticmethod
    def critical_paths(): return list(CRITICAL_PATHS)
