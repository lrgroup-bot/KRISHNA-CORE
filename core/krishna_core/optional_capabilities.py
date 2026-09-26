from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
from urllib.parse import urlparse


class DotsCapabilityRegistry:
    def status(self):
        return {
            "dots3_note":{
                "license":"Apache-2.0","local_enabled":False,"automatic_download":False,
                "reason":"280B total / 16B activated; heavyweight server-class provider",
                "activation":"verified-free OpenAI-compatible endpoint or future large compute node only",
            },
            "dots_mocr":{
                "local_enabled":False,"automatic_download":False,
                "activation":"license/model agreement review then benchmark as HAWKEYE document provider",
            },
            "dots_tts":{
                "license":"Apache-2.0 repository/checkpoints per upstream","local_enabled":False,
                "automatic_download":False,"activation":"voice benchmark against Indic providers before enabling",
            },
        }


class StemkitAdapter:
    ALLOWED={
        "columnStats","descriptives","leastSquaresLine","oneSampleTTest",
        "spearmanCorrelation","kruskalWallis","welchAnova","recommendTest",
        "parseXvg","parsePDB","structureStats","radiusOfGyration",
    }

    def __init__(self, node="node"):
        self.node=node

    def status(self):
        return {
            "provider":"stemkit-core","node_available":bool(shutil.which(self.node)),
            "package":"stemkit-core","lazy":True,"daemon":False,"free":True,
            "allowed_functions":sorted(self.ALLOWED),
        }

    def call(self, function, args):
        fn=str(function or "")
        if fn not in self.ALLOWED:
            raise PermissionError("STEMKit function is not allowlisted")
        if not shutil.which(self.node):
            raise RuntimeError("Node.js is unavailable")
        script=(
            "import * as s from 'stemkit-core';"
            "const fn=process.argv[1],args=JSON.parse(process.argv[2]);"
            "if(typeof s[fn]!=='function')throw new Error('function unavailable');"
            "const out=await s[fn](...args);console.log(JSON.stringify(out));"
        )
        p=subprocess.run(
            [self.node,"--input-type=module","-e",script,fn,json.dumps(list(args or []))],
            capture_output=True,text=True,timeout=30,shell=False,
        )
        if p.returncode:
            raise RuntimeError((p.stderr or p.stdout)[-3000:])
        return json.loads(p.stdout)


class StrixSandboxAdapter:
    """Authorized local candidate verification only; never an Internet target scanner."""

    def status(self):
        return {
            "provider":"strix","enabled":str(os.getenv("KRISHNA_STRIX_ENABLED","0")).lower() in {"1","true","yes","on"},
            "docker_available":bool(shutil.which("docker")),"external_targets":False,
            "candidate_only":True,"network_default":"deny","lazy":True,
        }

    @staticmethod
    def _target_allowed(target, candidate_root=None):
        value=str(target or "").strip()
        if not value:return False
        parsed=urlparse(value)
        if parsed.scheme in {"http","https"}:
            return parsed.hostname in {"127.0.0.1","localhost","::1"}
        path=Path(value).resolve()
        if candidate_root is None:return False
        root=Path(candidate_root).resolve()
        try:path.relative_to(root);return True
        except ValueError:return False

    def plan(self,target,*,candidate_root=None):
        if not self._target_allowed(target,candidate_root):
            raise PermissionError("Strix is restricted to an authorized local candidate root or localhost target")
        return {
            "provider":"strix","target":str(target),"authorized_scope":"local-candidate-only",
            "network_external":False,"execution":"lazy-disabled-until-explicitly-enabled",
            "repair_flow":["KABACH finding","candidate reproduction","Strix validation","Mrityunjay repair","regression retest"],
        }
