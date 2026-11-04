from __future__ import annotations
import json,re
from pathlib import Path

class RepositorySentinel:
    """Static-only repository preflight. Never imports or executes inspected code."""
    MANIFESTS={"requirements.txt","pyproject.toml","package.json","package-lock.json","pnpm-lock.yaml","yarn.lock","Dockerfile","docker-compose.yml","compose.yaml"}
    SECRET=re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}")
    RISKY=re.compile(r"(?i)(curl|wget).{0,80}(\||-o)|chmod\s+\+x|sudo\s|Invoke-Expression|eval\s*\(|exec\s*\(")
    MODEL=re.compile(r"(?i)(huggingface|hf_hub_download|snapshot_download|ollama\s+pull|from_pretrained)")
    def __init__(self,max_file_bytes=1_000_000): self.max_file_bytes=int(max_file_bytes)
    def inspect(self,root):
        root=Path(root).resolve()
        if not root.is_dir(): raise FileNotFoundError(str(root))
        findings=[]; manifests=[]; ports=set(); scanned=0
        for path in sorted(root.rglob("*")):
            if not path.is_file() or ".git" in path.parts: continue
            rel=str(path.relative_to(root)).replace("\\","/")
            if path.name in self.MANIFESTS: manifests.append(rel)
            try:
                if path.stat().st_size>self.max_file_bytes: continue
                text=path.read_text(encoding="utf-8",errors="replace"); scanned+=1
            except OSError: continue
            for label,rx,severity in (("possible_secret",self.SECRET,"high"),("risky_install_or_execution",self.RISKY,"medium"),("model_or_large_asset_download",self.MODEL,"medium")):
                if rx.search(text): findings.append({"type":label,"severity":severity,"path":rel})
            for m in re.finditer(r"(?i)(?:EXPOSE\s+|localhost:|127\.0\.0\.1:)(\d{2,5})",text):
                ports.add(int(m.group(1)))
        severities={"low":0,"medium":0,"high":0,"critical":0}
        for f in findings: severities[f["severity"]]+=1
        risk="high" if severities["high"] or severities["critical"] else ("medium" if severities["medium"] else "low")
        return {"mode":"STATIC_ONLY","executed_repository_code":False,"root":str(root),"files_scanned":scanned,"manifests":manifests,
                "ports":sorted(ports),"findings":findings,"risk":risk,"required_next":["license review","dependency review","KABACH review","shadow test","owner approval before consequential integration"]}
