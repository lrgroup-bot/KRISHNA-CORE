from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import subprocess


@dataclass(frozen=True)
class IntegrationSpec:
    integration_id:str
    upstream:str
    license:str
    mode:str
    default_enabled:bool
    resident:bool
    paid_fallback:bool
    owner:str
    notes:str=""
    def as_dict(self):return asdict(self)


class LoadReliefIntegrationCatalog:
    VERSION="load-relief-integrations-v1"
    SPECS=(
        IntegrationSpec("openjev","Zefan-Cai/Open-Jev","MIT","optional-local-or-remote-system-one",True,False,False,"KRISHNA"),
        IntegrationSpec("deepseek-harness-patterns","deepseek-ai/deepseek-harness","MIT","architecture-patterns-only",True,False,False,"KRISHNA"),
        IntegrationSpec("dots3-note","studio-dots-ai/dots3-note-prev","Apache-2.0","remote-or-future-server-provider",True,False,False,"Model Scout","280B total / 16B active; never auto-load locally"),
        IntegrationSpec("dots-tts","studio-dots-ai/dots.tts","Apache-2.0","optional-voice-provider",False,False,False,"Voice Fabric"),
        IntegrationSpec("dots-mocr","studio-dots-ai/dots.mocr","license-review-required","optional-document-vision-provider",False,False,False,"HAWKEYE","commercial activation requires model-license review"),
        IntegrationSpec("stemkit","LD-Shell/stemkit","MIT","on-demand-node-science-tool",True,False,False,"BRAHMAGYAN"),
        IntegrationSpec("strix","usestrix/strix","Apache-2.0","authorized-sandbox-worker",False,False,False,"KABACH/Mrityunjay","external targets denied by default"),
        IntegrationSpec("daily-stock-analysis","ZhuLinsen/daily_stock_analysis","MIT","isolated-kuber-adapter",False,False,False,"KUBER"),
        IntegrationSpec("eromify-patterns","eromify/eromify-workflow","no-license-detected","workflow-patterns-only",True,False,False,"Creator Fabric","do not copy source or enable paid services"),
        IntegrationSpec("google-maps-scraper-patterns","gosom/google-maps-scraper","MIT","job-patterns-only",True,False,False,"VANIK-NETRA","Google bulk business ingestion remains blocked"),
    )

    def list(self):return [x.as_dict() for x in self.SPECS]
    def status(self):
        return {
            "component":"KRISHNA Load-Relief Integration Catalog",
            "version":self.VERSION,
            "integrations":self.list(),
            "automatic_paid_fallback":False,
            "heavy_resident_services":0,
        }


class StemkitOnDemand:
    """Cold subprocess adapter. Does not keep Node or STEMKit resident."""

    def __init__(self, node="node", module_root=None):
        self.node=node
        self.module_root=Path(module_root).resolve() if module_root else None

    def status(self):
        return {
            "configured":bool(self.module_root and self.module_root.exists()),
            "module_root":str(self.module_root) if self.module_root else None,
            "resident":False,
            "paid":False,
        }

    def run_module(self,module,operation,payload,timeout=30):
        if not self.module_root or not self.module_root.exists():
            raise RuntimeError("STEMKit is not installed/configured")
        allowed={"units","statistics","curve-fitting","structure","data-cleaning","latex","bibtex","xvg-parser"}
        if module not in allowed:raise PermissionError("STEMKit module not allowlisted")
        script=f"""
import * as mod from {json.dumps(str((self.module_root/'src/core'/f'{module}.js').as_uri()))};
const op=process.argv[1], input=JSON.parse(process.argv[2]);
if(typeof mod[op] !== 'function') throw new Error('operation not exported');
const out=await mod[op](...(Array.isArray(input)?input:[input]));
process.stdout.write(JSON.stringify(out));
"""
        p=subprocess.run(
            [self.node,"--input-type=module","-e",script,str(operation),json.dumps(payload)],
            capture_output=True,text=True,timeout=max(1,min(int(timeout),60)),shell=False,
        )
        if p.returncode:raise RuntimeError((p.stderr or "STEMKit failed")[-4000:])
        return json.loads(p.stdout)


class StrixSandboxContract:
    """Produces a bounded defensive execution contract; does not run Strix itself."""

    def plan(self,target,*,candidate_root=None,external=False,approved=False):
        if external and not approved:
            raise PermissionError("external Strix target requires explicit owner approval")
        if not external and not candidate_root:
            raise ValueError("local Strix validation requires a candidate/staging root")
        return {
            "worker":"strix",
            "target":str(target),
            "candidate_root":str(candidate_root or ""),
            "external":bool(external),
            "owner_approved":bool(approved),
            "network":"deny-by-default" if not external else "target-only",
            "filesystem":"candidate-only",
            "promotion":False,
            "authority":"KABACH/Mrityunjay verification required before any promotion",
        }
