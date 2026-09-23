from __future__ import annotations

"""Canonical KRISHNA Mobile source/runtime identity.

The Android client and the PC-side companion have different roles. This module
prevents either one from being mistaken for a second canonical phone product.
It is read-only: retirement/deletion of compatibility data is never automatic.
"""

from pathlib import Path
import hashlib
import json
import os


class MobileRuntimeManifest:
    VERSION="krishna-mobile-canonical-v1"

    def __init__(self, repo_root=None, runtime_root=None):
        self.repo_root=Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.runtime_root=Path(runtime_root or os.getenv("KRISHNA_RUNTIME_ROOT") or r"E:\Krishna-The GOD")

    @property
    def manifest_path(self):
        return self.repo_root/"mobile_v3"/"CANONICAL_RUNTIME.json"

    def load(self):
        data=json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if data.get("schema")!=1 or data.get("version")!=self.VERSION:
            raise ValueError("unsupported KRISHNA mobile canonical runtime manifest")
        return data

    @staticmethod
    def _digest(path):
        h=hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda:fh.read(1024*1024),b""):h.update(chunk)
        return h.hexdigest()

    def status(self):
        data=self.load()
        source=self.repo_root/data["canonical_android_source"]
        files=[]
        missing=[]
        for name in data.get("canonical_files") or []:
            path=source/name
            if path.is_file():
                files.append({"name":name,"sha256":self._digest(path),"bytes":path.stat().st_size})
            else:
                missing.append(name)
        workflow=self.repo_root/data["build_workflow"]
        companion=self.runtime_root/"mobile"/"companion"
        return {
            "component":"KRISHNA Mobile Runtime Manifest",
            "version":self.VERSION,
            "canonical_android_source":data["canonical_android_source"],
            "package_id":data["package_id"],
            "ui_role":data["ui_role"],
            "source_files":files,
            "missing_source_files":missing,
            "source_ready":source.is_dir() and workflow.is_file() and not missing,
            "build_workflow":data["build_workflow"],
            "build_workflow_present":workflow.is_file(),
            "artifact_name":data.get("artifact_name"),
            "boundaries":dict(data.get("boundaries") or {}),
            "pc_runtime_companion":{
                **dict(data.get("pc_runtime_companion") or {}),
                "present":companion.exists(),
                "resolved_path":str(companion),
                "classification":"COMPATIBILITY_PC_SIDE_NOT_ANDROID_AUTHORITY",
            },
            "migration":{
                "automatic_delete":False,
                "retirement_gate":(data.get("pc_runtime_companion") or {}).get("retirement_gate"),
                "required_acceptance":[
                    "real Android APK clean install and relaunch",
                    "secure pairing and reconnect",
                    "same KRISHNA conversation/session",
                    "camera/audio permission and evidence capture",
                    "encrypted offline evidence then selective sync",
                    "PC retained acknowledgement before phone evidence deletion",
                    "completion notification delivery",
                ],
            },
            "authority_rule":"mobile_v3 is the only canonical Android source; PC companion is not a second mobile UI/source",
        }
