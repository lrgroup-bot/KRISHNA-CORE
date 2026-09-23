"""Trusted LAN node bootstrap and knowledge synchronization for KRISHNA."""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, shutil, socket

PORT=8771
EXCLUDED={"secrets","credentials","pids","cache","tmp","camera-evidence"}
SENSITIVE_NAMES={
    ".env","credentials.json","secrets.json","secret.json",
    "id_rsa","id_ed25519","authorized_keys",
}
SENSITIVE_SUFFIXES={".key",".pem",".pfx",".p12",".token"}

@dataclass
class NodeManifest:
    node:str; host:str; version:str; files:dict

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def _portable_relative(path):
    rel=Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        return False
    parts=[x.lower() for x in rel.parts]
    if any(x in EXCLUDED for x in parts):
        return False
    name=rel.name.lower()
    if name in SENSITIVE_NAMES or rel.suffix.lower() in SENSITIVE_SUFFIXES:
        return False
    return True

def _contained(root,rel):
    if not _portable_relative(rel):
        raise ValueError(f"unsafe or non-portable path: {rel}")
    root=Path(root).resolve()
    candidate=(root/rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes node root: {rel}") from exc
    return candidate

def portable_manifest(root, version="1"):
    root=Path(root).resolve(); files={}
    for p in root.rglob("*"):
        if p.is_symlink() or not p.is_file():
            continue
        rel=p.relative_to(root)
        if _portable_relative(rel):
            files[rel.as_posix()]=sha256(p)
    return NodeManifest(socket.gethostname(),socket.gethostname(),version,files)

def delta(source, target):
    return [p for p,h in source.files.items() if target.files.get(p)!=h]

def sync_files(source_root,target_root,paths):
    source_root,target_root=Path(source_root).resolve(),Path(target_root).resolve()
    copied=[]
    for rel in paths:
        src=_contained(source_root,rel)
        dst=_contained(target_root,rel)
        if not src.is_file():
            raise FileNotFoundError(str(src))
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        if sha256(src)!=sha256(dst): raise IOError(f"hash verification failed: {rel}")
        copied.append(Path(rel).as_posix())
    return copied

def export_manifest(root,out):
    m=portable_manifest(root); Path(out).write_text(json.dumps(asdict(m),indent=2),encoding="utf-8"); return m

class TrustedNodeBootstrap:
    """Discovery is advisory; pairing/transfer requires explicit trusted-node authorization."""
    def discover_lan(self, candidates):
        found=[]
        for host in candidates:
            try:
                with socket.create_connection((host,PORT),timeout=.2): found.append(host)
            except OSError: pass
        return found
    def plan(self, source_manifest, target_manifest, trusted=False):
        if not trusted: return {"status":"AUTHORIZATION_REQUIRED","copy":[]}
        paths=delta(source_manifest,target_manifest)
        unsafe=[p for p in paths if not _portable_relative(p)]
        if unsafe:
            return {"status":"BLOCKED_UNSAFE_MANIFEST","copy":[],"unsafe":unsafe}
        return {"status":"READY","copy":paths}
