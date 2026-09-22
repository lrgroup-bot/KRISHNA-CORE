from __future__ import annotations

import hashlib
import json
import struct
import time
from pathlib import Path


ARKIT_52 = (
    "eyeBlinkLeft","eyeBlinkRight","eyeLookDownLeft","eyeLookDownRight",
    "eyeLookInLeft","eyeLookInRight","eyeLookOutLeft","eyeLookOutRight",
    "eyeLookUpLeft","eyeLookUpRight","eyeSquintLeft","eyeSquintRight",
    "eyeWideLeft","eyeWideRight","jawForward","jawLeft","jawRight","jawOpen",
    "mouthClose","mouthFunnel","mouthPucker","mouthLeft","mouthRight",
    "mouthSmileLeft","mouthSmileRight","mouthFrownLeft","mouthFrownRight",
    "mouthDimpleLeft","mouthDimpleRight","mouthStretchLeft","mouthStretchRight",
    "mouthRollLower","mouthRollUpper","mouthShrugLower","mouthShrugUpper",
    "mouthPressLeft","mouthPressRight","mouthLowerDownLeft","mouthLowerDownRight",
    "mouthUpperUpLeft","mouthUpperUpRight","browDownLeft","browDownRight",
    "browInnerUp","browOuterUpLeft","browOuterUpRight","cheekPuff",
    "cheekSquintLeft","cheekSquintRight","noseSneerLeft","noseSneerRight","tongueOut",
)

OCULUS_15 = (
    "viseme_sil","viseme_PP","viseme_FF","viseme_TH","viseme_DD",
    "viseme_kk","viseme_CH","viseme_SS","viseme_nn","viseme_RR",
    "viseme_aa","viseme_E","viseme_I","viseme_O","viseme_U",
)

# TalkingHead accepts a Mixamo-compatible hierarchy. This list is intentionally a
# conservative core-body compatibility gate; finger and auxiliary hair bones may
# be present in addition to these.
MIXAMO_CORE = (
    "Hips","Spine","Spine1","Spine2","Neck","Head",
    "LeftShoulder","LeftArm","LeftForeArm","LeftHand",
    "RightShoulder","RightArm","RightForeArm","RightHand",
    "LeftUpLeg","LeftLeg","LeftFoot","LeftToeBase",
    "RightUpLeg","RightLeg","RightFoot","RightToeBase",
)


def _clean_bone_name(name: str) -> str:
    value=str(name or "")
    for prefix in ("mixamorig:", "mixamorig", "MixamoRig:", "MixamoRig"):
        if value.startswith(prefix):
            value=value[len(prefix):]
            break
    return value


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _glb_json(path: Path) -> dict:
    with path.open("rb") as stream:
        header=stream.read(12)
        if len(header)!=12:
            raise ValueError("GLB header is incomplete")
        magic,version,total=struct.unpack("<4sII",header)
        if magic!=b"glTF":
            raise ValueError("asset is not a binary glTF/GLB file")
        if version!=2:
            raise ValueError(f"unsupported GLB version {version}; expected 2")
        actual=path.stat().st_size
        if total!=actual:
            raise ValueError(f"GLB declared length {total} does not match file size {actual}")
        while stream.tell()<total:
            raw=stream.read(8)
            if len(raw)!=8:
                raise ValueError("GLB chunk header is incomplete")
            length,kind=struct.unpack("<II",raw)
            payload=stream.read(length)
            if len(payload)!=length:
                raise ValueError("GLB chunk payload is incomplete")
            if kind==0x4E4F534A:  # JSON
                return json.loads(payload.rstrip(b" \t\r\n\x00").decode("utf-8"))
    raise ValueError("GLB JSON chunk not found")


def _target_names(document: dict) -> set[str]:
    names=set()
    for mesh in document.get("meshes") or []:
        extras=mesh.get("extras") or {}
        for name in extras.get("targetNames") or []:
            if name:
                names.add(str(name))
    # Some exporters place target names in primitive extras.
    for mesh in document.get("meshes") or []:
        for primitive in mesh.get("primitives") or []:
            extras=primitive.get("extras") or {}
            for name in extras.get("targetNames") or []:
                if name:
                    names.add(str(name))
    return names


class AvatarAssetInspector:
    """Zero-dependency GLB compatibility inspector for KRISHNA's private avatar.

    The original private asset is never modified. This class reads GLB metadata and
    reports whether the current asset has the body rig and face channels expected by
    the local TalkingHead runtime.
    """

    def __init__(self, report_path: str | Path | None = None):
        self.report_path=Path(report_path).resolve() if report_path else None
        self._cache_key=None
        self._cache=None

    def inspect(self, path: str | Path) -> dict:
        asset=Path(path).resolve()
        if not asset.is_file():
            return {
                "available":False,"path":str(asset),"ready":False,"stage":"missing",
                "issues":["private KRISHNA GLB is not installed"],
                "checked_at":time.time(),
            }
        stat=asset.stat()
        key=(str(asset),stat.st_mtime_ns,stat.st_size)
        if key==self._cache_key and self._cache is not None:
            return dict(self._cache)
        try:
            doc=_glb_json(asset)
            node_names=[str(x.get("name") or "") for x in (doc.get("nodes") or []) if x.get("name")]
            normalized={_clean_bone_name(x) for x in node_names}
            morphs=_target_names(doc)
            skins=doc.get("skins") or []
            animations=doc.get("animations") or []
            animation_names=[str(x.get("name") or f"animation-{i+1}") for i,x in enumerate(animations)]
            missing_bones=[x for x in MIXAMO_CORE if x not in normalized]
            missing_arkit=[x for x in ARKIT_52 if x not in morphs]
            missing_visemes=[x for x in OCULUS_15 if x not in morphs]
            body_ready=bool(skins) and not missing_bones
            face_arkit_ready=not missing_arkit
            face_viseme_ready=not missing_visemes
            face_ready=face_arkit_ready and face_viseme_ready
            ready=body_ready and face_ready
            if ready:
                stage="production-ready"
            elif not skins:
                stage="unrigged"
            elif not body_ready:
                stage="body-rig-incomplete"
            elif not morphs:
                stage="facial-rig-missing"
            else:
                stage="facial-rig-incomplete"
            issues=[]
            if not skins:issues.append("no glTF skin/armature binding detected")
            if missing_bones:issues.append(f"{len(missing_bones)} core Mixamo-compatible bones missing")
            if not morphs:issues.append("no named facial morph targets detected")
            elif missing_arkit:issues.append(f"{len(missing_arkit)} ARKit blend shapes missing")
            if missing_visemes:issues.append(f"{len(missing_visemes)} Oculus viseme shapes missing")
            result={
                "available":True,
                "path":str(asset),
                "sha256":_sha256(asset),
                "size_bytes":stat.st_size,
                "glb_version":2,
                "generator":str((doc.get("asset") or {}).get("generator") or ""),
                "skin_count":len(skins),
                "animation_count":len(animations),
                "animation_names":animation_names[:100],
                "node_count":len(doc.get("nodes") or []),
                "mesh_count":len(doc.get("meshes") or []),
                "morph_target_count":len(morphs),
                "morph_targets":sorted(morphs),
                "body":{"ready":body_ready,"missing_core_bones":missing_bones,"required_core_bones":list(MIXAMO_CORE)},
                "face":{
                    "ready":face_ready,
                    "arkit":{"ready":face_arkit_ready,"present":len(ARKIT_52)-len(missing_arkit),"required":len(ARKIT_52),"missing":missing_arkit},
                    "oculus_visemes":{"ready":face_viseme_ready,"present":len(OCULUS_15)-len(missing_visemes),"required":len(OCULUS_15),"missing":missing_visemes},
                },
                "talkinghead":{"ready":ready,"requires":"Mixamo-compatible body + ARKit 52 + Oculus 15"},
                "ready":ready,
                "stage":stage,
                "issues":issues,
                "policy":"inspection only; source GLB is never modified",
                "checked_at":time.time(),
            }
        except Exception as exc:
            result={
                "available":True,"path":str(asset),"ready":False,"stage":"invalid",
                "issues":[f"{type(exc).__name__}: {exc}"],"checked_at":time.time(),
            }
        self._cache_key=key;self._cache=result
        if self.report_path:
            try:
                self.report_path.parent.mkdir(parents=True,exist_ok=True)
                tmp=self.report_path.with_suffix(self.report_path.suffix+".tmp")
                tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
                tmp.replace(self.report_path)
            except OSError:
                pass
        return dict(result)


def inspect_avatar(path: str | Path, report_path: str | Path | None = None) -> dict:
    return AvatarAssetInspector(report_path).inspect(path)
