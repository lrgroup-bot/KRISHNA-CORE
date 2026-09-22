from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class VideoAvatarProvider:
    provider_id: str
    name: str
    repo: str | None
    license: str
    mode: str
    free_local: bool
    entrypoints: tuple[str, ...]
    strengths: tuple[str, ...]
    limitations: tuple[str, ...]
    min_vram_gb: int | None = None
    tested_platform: str = "unknown"
    commercial_note: str = ""

    def public(self) -> dict:
        row=asdict(self)
        row["entrypoints"]=list(self.entrypoints)
        row["strengths"]=list(self.strengths)
        row["limitations"]=list(self.limitations)
        return row


class VideoAvatarFabric:
    """Local-first talking-video provider registry for KRISHNA.

    This intentionally reproduces the *workflow class* of hosted avatar studios
    (identity/reference -> motion/audio -> lip sync -> rendered video) without
    copying proprietary service code, weights, prompts, or private endpoints.
    """

    VERSION="video-avatar-v1"
    ROOT_RELATIVE=Path("tools")/"avatar-video"

    PROVIDERS=(
        VideoAvatarProvider(
            provider_id="musetalk",
            name="MuseTalk 1.5",
            repo="https://github.com/TMElyralab/MuseTalk.git",
            license="MIT",
            mode="realtime_lipsync",
            free_local=True,
            entrypoints=("scripts/realtime_inference.py","app.py"),
            strengths=("real-time lip-sync","Windows inference path","multilingual audio input","commercial code/model use allowed by upstream"),
            limitations=("primarily edits the face region","identity details can drift","single-frame pipeline can jitter"),
            tested_platform="Windows/Linux",
        ),
        VideoAvatarProvider(
            provider_id="liveportrait",
            name="LivePortrait",
            repo="https://github.com/KlingAIResearch/LivePortrait.git",
            license="MIT code; bundled InsightFace models have separate non-commercial terms",
            mode="portrait_motion_transfer",
            free_local=True,
            entrypoints=("inference.py","app.py"),
            strengths=("portrait motion transfer","expression/pose control","video-to-video portrait driving","privacy-preserving motion templates"),
            limitations=("needs a driving video/template for motion","replace bundled InsightFace detection models for fully commercial deployment"),
            tested_platform="Windows/Linux/macOS",
            commercial_note="Upstream code is MIT, but the bundled InsightFace models are non-commercial; use a commercially compatible detector for commercial deployment.",
        ),
        VideoAvatarProvider(
            provider_id="echomimic_v3",
            name="EchoMimicV3 Flash",
            repo="https://github.com/antgroup/echomimic_v3.git",
            license="Apache-2.0",
            mode="audio_driven_body_video",
            free_local=True,
            entrypoints=("infer_flash.py","app.py","app_mm.py"),
            strengths=("image+audio directly to talking video","body and face motion","8-step Flash path","up to 768x768 upstream"),
            limitations=("heavy GPU workload","official quick-start is Linux/CUDA focused","not a low-latency chat renderer on modest GPUs"),
            min_vram_gb=12,
            tested_platform="Linux/CUDA",
        ),
        VideoAvatarProvider(
            provider_id="wan_animate_2",
            name="Wan-Animate-2",
            repo="https://github.com/Wan-Video/Wan-Animate-2.git",
            license="Apache-2.0",
            mode="cinematic_character_animation",
            free_local=True,
            entrypoints=("infer/wan_animate_2_gradio.py","infer/wan_animate_2_gradio_distillation.py"),
            strengths=("single-image character animation","body/expression transfer","character replacement","cinematic motion quality"),
            limitations=("14B-class model family is compute-heavy","best used as an offline/cinematic provider, not the always-on KRISHNA chat face"),
            tested_platform="Linux/CUDA",
        ),
        VideoAvatarProvider(
            provider_id="higgsfield",
            name="Higgsfield API",
            repo=None,
            license="proprietary hosted service",
            mode="cloud_video_generation",
            free_local=False,
            entrypoints=(),
            strengths=("hosted image-to-video","hosted lipsync studio","multiple commercial video-model integrations"),
            limitations=("not free/local","requires credentials and network","proprietary implementation cannot be copied into KRISHNA"),
            tested_platform="cloud",
            commercial_note="Optional connector only; never a KRISHNA local/free dependency.",
        ),
    )

    def __init__(self, runtime_root: Path):
        self.runtime_root=Path(runtime_root)
        self.root=self.runtime_root/self.ROOT_RELATIVE

    @classmethod
    def provider(cls, provider_id: str) -> VideoAvatarProvider:
        key=str(provider_id or "").strip().lower()
        for row in cls.PROVIDERS:
            if row.provider_id==key:
                return row
        raise KeyError(provider_id)

    def provider_root(self, provider_id: str) -> Path:
        return self.root/provider_id

    def environment_root(self, provider_id: str) -> Path:
        return self.root/"envs"/provider_id

    def runtime_status(self, provider_id: str) -> dict:
        key=str(provider_id or "").strip().lower()
        row=self.provider(key)
        source=self.installed(key) if row.free_local else False
        if not row.free_local:
            return {"source_installed":False,"environment_ready":False,"weights_ready":False,"runtime_ready":False}
        env_python=self.environment_root(key)/"Scripts"/"python.exe"
        if key=="musetalk":
            required=(
                self.provider_root(key)/"models"/"musetalkV15"/"unet.pth",
                self.provider_root(key)/"models"/"musetalkV15"/"musetalk.json",
                self.provider_root(key)/"models"/"sd-vae"/"diffusion_pytorch_model.bin",
                self.provider_root(key)/"models"/"whisper"/"pytorch_model.bin",
                self.provider_root(key)/"models"/"dwpose"/"dw-ll_ucoco_384.pth",
            )
        elif key=="liveportrait":
            required=(self.provider_root(key)/"pretrained_weights",)
        else:
            required=()
        weights=bool(required) and all(x.exists() for x in required)
        env_ready=env_python.is_file()
        return {
            "source_installed":source,
            "environment_ready":env_ready,
            "environment_python":str(env_python),
            "weights_ready":weights,
            "runtime_ready":bool(source and env_ready and weights),
        }

    def installed(self, provider_id: str) -> bool:
        row=self.provider(provider_id)
        if not row.free_local:
            return False
        base=self.provider_root(provider_id)
        return base.is_dir() and any((base/p).is_file() for p in row.entrypoints)

    def status(self) -> dict:
        rows=[]
        for provider in self.PROVIDERS:
            row=provider.public()
            row["installed"]=self.installed(provider.provider_id) if provider.free_local else False
            row["install_root"]=str(self.provider_root(provider.provider_id)) if provider.free_local else None
            row["runtime"]=self.runtime_status(provider.provider_id)
            rows.append(row)
        return {
            "version":self.VERSION,
            "policy":"local/free providers first; hosted proprietary providers are optional connectors only",
            "workflow":["identity/reference","motion/audio","lip-sync","render","verification"],
            "providers":rows,
            "recommended":{
                "live_chat_lipsync":"musetalk",
                "portrait_motion":"liveportrait",
                "high_quality_audio_body":"echomimic_v3",
                "cinematic_body_motion":"wan_animate_2",
            },
        }

    def recommend(self, goal: str="", vram_gb: float | None=None) -> dict:
        text=str(goal or "").lower()
        if any(x in text for x in ("cinematic","full body","body motion","character replacement","driving video")):
            provider="wan_animate_2"
        elif any(x in text for x in ("half body","audio body","image and audio","talking video","higgsfield")):
            provider="echomimic_v3" if vram_gb is None or vram_gb>=12 else "musetalk"
        elif any(x in text for x in ("motion transfer","expression","pose","portrait motion")):
            provider="liveportrait"
        else:
            provider="musetalk"
        row=self.provider(provider).public()
        row["installed"]=self.installed(provider)
        row["reason"]="Selected by KRISHNA's local-first video-avatar routing policy."
        if row.get("min_vram_gb") and vram_gb is not None and vram_gb<row["min_vram_gb"]:
            row["hardware_warning"]=f"Provider upstream guidance needs about {row['min_vram_gb']} GB VRAM for the referenced path."
        return row

    def generation_contract(self, provider_id: str) -> dict:
        row=self.provider(provider_id)
        if provider_id=="musetalk":
            inputs=("avatar_image_or_video","audio_wav")
            output="lip-synced MP4"
        elif provider_id=="liveportrait":
            inputs=("source_portrait","driving_video_or_template")
            output="motion-driven MP4"
        elif provider_id=="echomimic_v3":
            inputs=("source_image","audio_wav","prompt")
            output="audio-driven body/portrait MP4"
        elif provider_id=="wan_animate_2":
            inputs=("source_character_image","driving_video","prompt")
            output="cinematic character-animation MP4"
        else:
            inputs=("image_or_video","prompt_or_audio","credentials")
            output="hosted generated video"
        return {
            "provider":row.public(),
            "inputs":list(inputs),
            "output":output,
            "execution":"local subprocess adapter" if row.free_local else "optional external connector",
            "privacy":"local assets remain on the KRISHNA PC" if row.free_local else "assets leave the KRISHNA PC when the owner explicitly uses the hosted provider",
        }
