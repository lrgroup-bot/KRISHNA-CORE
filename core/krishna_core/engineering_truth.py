from __future__ import annotations
from pathlib import Path
import json,shutil,subprocess
class LSPTruth:
    SERVERS={"python":["pyright","--outputjson"],"typescript":["tsc","--noEmit"],"dart":["dart","analyze"],"rust":["cargo","check","--message-format=json"],"go":["go","vet","./..."]}
    def plan(self,language):
        cmd=self.SERVERS.get(str(language).lower());return {"language":language,"command":cmd,"available":bool(cmd and shutil.which(cmd[0]))}
    def run(self,language,root,timeout=180):
        p=self.plan(language)
        if not p["available"]:return {**p,"ok":False,"reason":"analyzer_unavailable"}
        proc=subprocess.run(p["command"],cwd=str(Path(root).resolve()),capture_output=True,text=True,timeout=timeout,shell=False)
        return {**p,"ok":proc.returncode==0,"exit_code":proc.returncode,"stdout":proc.stdout[-30000:],"stderr":proc.stderr[-30000:]}
class DAPTruth:
    """Fail-closed debugger contract. Adapter execution must be explicitly configured per language."""
    def plan(self,language,root,breakpoints=()):
        return {"language":language,"root":str(Path(root).resolve()),"breakpoints":list(breakpoints),"mode":"read-runtime-evidence","mutating":False,"ready":False,"reason":"pinned DAP adapter required"}
