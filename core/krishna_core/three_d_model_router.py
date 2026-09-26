from __future__ import annotations

"""KRISHNA free-first 3D model/rig/animation capability router.

The router does not download models or call paid services on its own. It only plans
and dispatches to explicitly configured local workers or approved zero-cost test
adapters. Hardware, license and spend gates are fail-closed.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import shutil
import subprocess
import time


@dataclass(frozen=True)
class ThreeDProvider:
    provider_id: str
    stage: str
    purpose: str
    license: str
    min_vram_gb: float
    local: bool
    free: bool
    commercial_use: str
    command_env: str | None = None
    executable_hint: str | None = None
    notes: str = ""

    def as_dict(self):
        return asdict(self)


class ThreeDModelRouter:
    VERSION = "krishna-3d-router-v1"

    PROVIDERS = (
        ThreeDProvider("blender","pipeline","mesh cleanup, baking, rig/animation assembly and GLB export","GPL-3.0",0,True,True,"allowed","KRISHNA_BLENDER_CMD","blender"),
        ThreeDProvider("instant-meshes","retopology","automatic quad-oriented retopology","BSD-3-Clause",0,True,True,"allowed","KRISHNA_INSTANT_MESHES_CMD","Instant Meshes"),
        ThreeDProvider("remi-blender","retopology","Blender repair, retopo, UV and texture rebake helper","open-source",0,True,True,"review upstream license","KRISHNA_REMI_CMD",None),
        ThreeDProvider("openfacefx","face","offline viseme/facial animation to glTF/GLB","MIT",0,True,True,"allowed","KRISHNA_OPENFACEFX_CMD",None),
        ThreeDProvider("offline-lipsync","face","offline speech/phoneme to Blender shape-key animation","open-source",0,True,True,"review upstream license","KRISHNA_LIPSYNC_CMD",None),
        ThreeDProvider("triposr","generation","single-image to 3D mesh","MIT",6,True,True,"allowed","KRISHNA_TRIPOSR_CMD",None),
        ThreeDProvider("hunyuan3d-2mini","generation","single-image shape generation","Tencent Hunyuan Community License",6,True,True,"license review required for commercial distribution","KRISHNA_HUNYUAN3D2MINI_CMD",None),
        ThreeDProvider("stable-fast-3d","generation","fast textured GLB generation with remesh support","Stability AI Community License",6,True,True,"license review required","KRISHNA_SF3D_CMD",None),
        ThreeDProvider("triposg","generation","high-fidelity image to geometry/GLB","MIT",8,True,True,"allowed","KRISHNA_TRIPOSG_CMD",None),
        ThreeDProvider("partcrafter","parts","semantic multi-part 3D generation","MIT",8,True,True,"allowed","KRISHNA_PARTCRAFTER_CMD",None),
        ThreeDProvider("unirig","rigging","automatic skeleton and skin-weight prediction","MIT",8,True,True,"allowed","KRISHNA_UNIRIG_CMD",None),
        ThreeDProvider("spar3d","generation","single-image 3D with editable point-cloud stage","Stability AI Community License",7,True,True,"license review required","KRISHNA_SPAR3D_CMD",None),
        ThreeDProvider("skintokens","rigging","TokenRig/SkinTokens skeleton + skin weights","MIT",14,True,True,"allowed","KRISHNA_SKINTOKENS_CMD",None),
        ThreeDProvider("puppeteer","animation","rigging and video-guided character animation","Apache-2.0",4.2,True,True,"verify component licenses for chosen pipeline","KRISHNA_PUPPETEER_CMD",None),
        ThreeDProvider("anytop","animation","motion generation for arbitrary skeleton topologies","MIT",8,True,True,"allowed","KRISHNA_ANYTOP_CMD",None),
        ThreeDProvider("anigen","animation","image to animatable mesh/skeleton/skinning research pipeline","mixed",18,True,True,"research/non-commercial component restrictions; blocked for commercial use","KRISHNA_ANIGEN_CMD",None),
        ThreeDProvider("pixal3d","generation","high-detail multi-view PBR GLB generation","MIT",24,True,True,"allowed","KRISHNA_PIXAL3D_CMD",None,"low-VRAM mode is experimental and not used for automatic eligibility"),
        ThreeDProvider("trellis2","generation","high-quality PBR 3D asset generation","MIT",24,True,True,"allowed","KRISHNA_TRELLIS2_CMD",None),
        ThreeDProvider("tripo-p2-free-credit","cloud-test","Tripo P2 native-quad experiment using explicit free promotional allowance only","proprietary",0,False,False,"test only; no automatic execution","KRISHNA_TRIPO_P2_TEST_CMD",None),
        ThreeDProvider("tripo-h31-free-credit","cloud-test","Tripo H3.1 detail/reference experiment using explicit free promotional allowance only","proprietary",0,False,False,"test only; no automatic execution","KRISHNA_TRIPO_H31_TEST_CMD",None),
        ThreeDProvider("tripo-paid-api","cloud-paid","Tripo paid API","proprietary",0,False,False,"hard blocked by zero-spend policy",None,None),
    )

    STAGE_ORDER = ("generation","parts","retopology","rigging","animation","face","pipeline")

    def __init__(self, *, zero_spend=None):
        self.zero_spend = zero_spend

    @staticmethod
    def _configured_command(provider: ThreeDProvider) -> str | None:
        if not provider.command_env:
            return None
        raw = str(os.getenv(provider.command_env) or "").strip()
        if raw:
            first = raw.split()[0].strip('"')
            p = Path(first).expanduser()
            if p.is_absolute() and p.exists():
                return raw
        if provider.executable_hint:
            found = shutil.which(provider.executable_hint)
            if found:
                return found
        return None

    @staticmethod
    def detect_vram_gb() -> float | None:
        override = str(os.getenv("KRISHNA_GPU_VRAM_GB") or "").strip()
        if override:
            try:
                return max(0.0, float(override))
            except ValueError:
                pass
        smi = shutil.which("nvidia-smi")
        if not smi:
            return None
        try:
            proc = subprocess.run(
                [smi, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, shell=False,
            )
            if proc.returncode:
                return None
            rows=[]
            for line in (proc.stdout or "").splitlines():
                try: rows.append(float(line.strip())/1024.0)
                except ValueError: pass
            return max(rows) if rows else None
        except Exception:
            return None

    def _spend_allowed(self, provider: ThreeDProvider) -> tuple[bool,str]:
        if provider.provider_id == "tripo-paid-api" or provider.stage == "cloud-paid":
            if self.zero_spend is not None:
                decision=self.zero_spend.decide("paid_api")
                return bool(decision.get("allowed")), str(decision.get("reason") or "paid API blocked")
            return False,"paid API blocked by KRISHNA zero-spend policy"
        if provider.stage == "cloud-test":
            return False,"cloud promotional/free-credit providers are test-only and require explicit owner action; never automatic"
        return True,"local/free capability"

    def provider_status(self, provider_id: str, *, vram_gb: float | None = None) -> dict:
        provider=next((x for x in self.PROVIDERS if x.provider_id==provider_id),None)
        if provider is None:
            raise KeyError(provider_id)
        if vram_gb is None:
            vram_gb=self.detect_vram_gb()
        spend_ok,spend_reason=self._spend_allowed(provider)
        command=self._configured_command(provider)
        hardware_ok=(provider.min_vram_gb<=0 or (vram_gb is not None and vram_gb>=provider.min_vram_gb))
        configured=bool(command) if provider.local else False
        auto_eligible=bool(provider.local and provider.free and spend_ok and hardware_ok and configured)
        blockers=[]
        if not provider.local: blockers.append("not a local provider")
        if not provider.free: blockers.append("not zero-cost")
        if not spend_ok: blockers.append(spend_reason)
        if provider.min_vram_gb>0 and not hardware_ok:
            blockers.append(
                "GPU VRAM unknown" if vram_gb is None
                else f"requires >= {provider.min_vram_gb:g} GB VRAM; detected {vram_gb:.1f} GB"
            )
        if provider.local and not configured:
            blockers.append(f"worker not configured ({provider.command_env})")
        return {
            **provider.as_dict(),
            "detected_vram_gb": vram_gb,
            "configured": configured,
            "command": command,
            "hardware_ok": hardware_ok,
            "spend_ok": spend_ok,
            "automatic_eligible": auto_eligible,
            "blockers": blockers,
        }

    def catalog(self, *, vram_gb: float | None = None) -> list[dict]:
        return [self.provider_status(x.provider_id,vram_gb=vram_gb) for x in self.PROVIDERS]

    def plan(self, *, goal="production_avatar", vram_gb: float | None = None,
             include_parts=True, include_animation=True, include_face=True) -> dict:
        if vram_gb is None:
            vram_gb=self.detect_vram_gb()
        rows=self.catalog(vram_gb=vram_gb)

        def choose(stage, preferred):
            stage_rows=[x for x in rows if x["stage"]==stage and x["automatic_eligible"]]
            by_id={x["provider_id"]:x for x in stage_rows}
            for pid in preferred:
                if pid in by_id:return by_id[pid]
            return stage_rows[0] if stage_rows else None

        generation=choose("generation",("pixal3d","triposg","hunyuan3d-2mini","stable-fast-3d","triposr","spar3d"))
        parts=choose("parts",("partcrafter",)) if include_parts else None
        retopo=choose("retopology",("instant-meshes","remi-blender"))
        rig=choose("rigging",("skintokens","unirig"))
        animation=choose("animation",("puppeteer","anytop")) if include_animation else None
        face=choose("face",("openfacefx","offline-lipsync")) if include_face else None
        blender=choose("pipeline",("blender",))

        selected=[x for x in (generation,parts,retopo,rig,animation,face,blender) if x]
        missing=[]
        if not generation:missing.append("generation")
        if not retopo:missing.append("retopology")
        if not rig:missing.append("rigging")
        if include_animation and not animation:missing.append("animation")
        if include_face and not face:missing.append("face")
        if not blender:missing.append("pipeline")

        current_4gb_mode=(vram_gb is not None and vram_gb<6)
        return {
            "component":"KRISHNA Free 3D Model Router",
            "version":self.VERSION,
            "goal":str(goal),
            "detected_vram_gb":vram_gb,
            "selected":[x["provider_id"] for x in selected],
            "stages":{
                "generation":generation,
                "parts":parts,
                "retopology":retopo,
                "rigging":rig,
                "animation":animation,
                "face":face,
                "pipeline":blender,
            },
            "missing_stages":missing,
            "ready":not missing,
            "current_low_vram_mode":current_4gb_mode,
            "low_vram_recommendation":(
                "Use Blender/Instant Meshes/OpenFaceFX locally now; defer 6GB+ generation/rigging workers to stronger GPU node."
                if current_4gb_mode else None
            ),
            "cloud_test_providers":[
                x["provider_id"] for x in rows if x["stage"]=="cloud-test"
            ],
            "paid_providers_blocked":[
                x["provider_id"] for x in rows if x["stage"]=="cloud-paid"
            ],
            "policy":{
                "local_first":True,
                "free_first":True,
                "automatic_paid_cloud":False,
                "promotional_credit_auto_use":False,
                "private_identity_cloud_upload":False,
                "license_gate":True,
                "hardware_gate":True,
            },
            "checked_at":time.time(),
        }

    def status(self) -> dict:
        vram=self.detect_vram_gb()
        rows=self.catalog(vram_gb=vram)
        return {
            "component":"KRISHNA Free 3D Model Router",
            "version":self.VERSION,
            "detected_vram_gb":vram,
            "providers":rows,
            "automatic_eligible":[x["provider_id"] for x in rows if x["automatic_eligible"]],
            "configured_local":[x["provider_id"] for x in rows if x["local"] and x["configured"]],
            "paid_blocked":[x["provider_id"] for x in rows if x["stage"]=="cloud-paid"],
            "cloud_free_credit_test_only":[x["provider_id"] for x in rows if x["stage"]=="cloud-test"],
            "ready":True,
        }
