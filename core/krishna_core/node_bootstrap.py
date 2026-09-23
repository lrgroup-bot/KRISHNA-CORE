"""Trusted LAN node bootstrap and knowledge synchronization for KRISHNA."""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, shutil, socket

PORT=8771
EXCLUDED={"secrets","credentials","pids","cache","tmp","camera-evidence"}

@dataclass
class NodeManifest:
    node:str; host:str; version:str; files:dict

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def portable_manifest(root, version="1"):
    root=Path(root); files={}
    for p in root.rglob("*"):
        if p.is_file() and not any(x.lower() in EXCLUDED for x in p.parts):
            files[str(p.relative_to(root))]=sha256(p)
    return NodeManifest(socket.gethostname(),socket.gethostname(),version,files)

def delta(source, target):
    return [p for p,h in source.files.items() if target.files.get(p)!=h]

def sync_files(source_root,target_root,paths):
    source_root,target_root=Path(source_root),Path(target_root)
    copied=[]
    for rel in paths:
        src=source_root/rel; dst=target_root/rel; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
        if sha256(src)!=sha256(dst): raise IOError(f"hash verification failed: {rel}")
        copied.append(rel)
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
        return {"status":"READY","copy":delta(source_manifest,target_manifest)}
