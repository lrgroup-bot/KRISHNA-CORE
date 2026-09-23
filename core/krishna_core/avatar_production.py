from __future__ import annotations

"""Production pipeline boundary for KRISHNA's private rigged child avatar.

The pipeline never fabricates identity or silently claims that a sprite is a rigged
character. A locally configured worker (normally Blender) receives one generated
JSON job manifest, writes a GLB, and the GLB must then pass AvatarAssetInspector.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import os
import shlex
import subprocess
import time
import uuid

from .avatar_asset_pipeline import AvatarAssetInspector


REQUIRED_CLIPS = (
    "idle","listen","think","talk","walk","wave","smile","flute","dhyan",
    "sleep","wake","work","wisdom","playful","protection",
)


@dataclass(frozen=True)
class AvatarProductionPlan:
    job_id: str
    source_asset: str
    output_glb: str
    required_clips: tuple[str, ...]
    identity_fingerprint: str | None
    worker_configured: bool


class AvatarProductionPipeline:
    ENV = "KRISHNA_AVATAR_RIG_WORKER_CMD"
    VERSION = "avatar-production-v1"

    def __init__(self, runtime_root: str | Path):
        self.root = Path(runtime_root).resolve()
        self.jobs = self.root / "avatar" / "production-jobs"
        self.jobs.mkdir(parents=True, exist_ok=True)

    def _command(self) -> list[str]:
        raw = str(os.getenv(self.ENV) or "").strip()
        if not raw:
            return []
        argv = shlex.split(raw, posix=(os.name != "nt"))
        if not argv:
            return []
        exe = Path(argv[0]).expanduser()
        if not exe.is_absolute() or not exe.is_file():
            return []
        return [str(exe), *argv[1:]]

    @staticmethod
    def _fingerprint_identity(value: str | bytes | None) -> str | None:
        if value in (None, "", b""):
            return None
        raw = value if isinstance(value, bytes) else str(value).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def plan(self, source_asset: str | Path, output_glb: str | Path, *,
             identity_ref: str | bytes | None = None,
             required_clips=REQUIRED_CLIPS) -> AvatarProductionPlan:
        src = Path(source_asset).resolve()
        out = Path(output_glb).resolve()
        if not src.is_file():
            raise FileNotFoundError(str(src))
        if out.suffix.lower() != ".glb":
            raise ValueError("avatar output must be a .glb file")
        clips = tuple(dict.fromkeys(str(x).strip().lower() for x in required_clips if str(x).strip()))
        if not clips:
            raise ValueError("at least one required animation clip is required")
        return AvatarProductionPlan(
            job_id="AVATAR-" + uuid.uuid4().hex[:20],
            source_asset=str(src),
            output_glb=str(out),
            required_clips=clips,
            identity_fingerprint=self._fingerprint_identity(identity_ref),
            worker_configured=bool(self._command()),
        )

    def write_job(self, plan: AvatarProductionPlan) -> Path:
        payload = {
            "schema": "krishna.avatar-production-job.v1",
            "version": self.VERSION,
            **asdict(plan),
            "requirements": {
                "body": "Mixamo-compatible body including finger bones",
                "face": "ARKit 52 + Oculus 15 visemes",
                "format": "glTF 2.0 binary GLB",
                "preserve_identity": True,
            },
            "privacy": {
                "raw_identity_reference_in_manifest": False,
                "identity_fingerprint_only": bool(plan.identity_fingerprint),
                "cloud_upload_allowed": False,
            },
            "requested_at": time.time(),
        }
        path = self.jobs / f"{plan.job_id}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def validate_output(self, path: str | Path, required_clips=REQUIRED_CLIPS) -> dict:
        report = AvatarAssetInspector().inspect(path)
        present = {str(x).strip().lower() for x in report.get("animation_names") or []}
        required = {str(x).strip().lower() for x in required_clips if str(x).strip()}
        missing = sorted(required - present)
        ready = bool(report.get("ready")) and not missing
        return {
            "ready": ready,
            "asset": report,
            "required_clips": sorted(required),
            "missing_animation_clips": missing,
            "stage": "production-ready" if ready else "production-incomplete",
            "verification_required": True,
        }

    def run(self, source_asset: str | Path, output_glb: str | Path, *,
            identity_ref: str | bytes | None = None,
            required_clips=REQUIRED_CLIPS, timeout=7200) -> dict:
        argv = self._command()
        if not argv:
            raise RuntimeError(
                "avatar rig worker is not configured; set KRISHNA_AVATAR_RIG_WORKER_CMD "
                "to an absolute local worker executable"
            )
        plan = self.plan(source_asset, output_glb, identity_ref=identity_ref, required_clips=required_clips)
        job_file = self.write_job(plan)
        started = time.time()
        proc = subprocess.run(
            [*argv, str(job_file)], capture_output=True, text=True, shell=False,
            timeout=max(30, int(timeout)),
        )
        if proc.returncode:
            raise RuntimeError("avatar rig worker failed: " + (proc.stderr or proc.stdout or "")[-1200:])
        out = Path(plan.output_glb)
        if not out.is_file():
            raise RuntimeError("avatar rig worker completed without producing the requested GLB")
        validation = self.validate_output(out, required_clips=plan.required_clips)
        result = {
            "job_id": plan.job_id,
            "completed": True,
            "duration_s": round(time.time() - started, 3),
            "output_glb": str(out),
            "stdout_tail": (proc.stdout or "")[-3000:],
            "stderr_tail": (proc.stderr or "")[-3000:],
            "validation": validation,
            "verified": bool(validation["ready"]),
        }
        (self.jobs / f"{plan.job_id}-result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result

    def status(self) -> dict:
        argv = self._command()
        return {
            "component": "KRISHNA Avatar Production Pipeline",
            "version": self.VERSION,
            "worker_configured": bool(argv),
            "worker_executable": argv[0] if argv else None,
            "required_clips": list(REQUIRED_CLIPS),
            "cloud_upload": False,
            "ready_for_private_asset": True,
            "production_verified": False,
            "verification_rule": "generated GLB must pass body, ARKit, viseme and required-animation inspection",
        }
