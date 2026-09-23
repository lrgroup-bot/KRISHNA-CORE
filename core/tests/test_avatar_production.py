import json
import struct
import tempfile
import unittest
from pathlib import Path

from krishna_core.avatar_asset_pipeline import ARKIT_52, OCULUS_15, TALKINGHEAD_BONES
from krishna_core.avatar_production import AvatarProductionPipeline, REQUIRED_CLIPS


def write_glb(path: Path, document: dict):
    raw=json.dumps(document,separators=(",",":")).encode("utf-8")
    raw+=b" " * ((4-len(raw)%4)%4)
    total=12+8+len(raw)
    path.write_bytes(struct.pack("<4sII",b"glTF",2,total)+struct.pack("<II",len(raw),0x4E4F534A)+raw)


class AvatarProductionPipelineTests(unittest.TestCase):
    def test_plan_keeps_raw_identity_out_of_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"source.glb"
            write_glb(source,{"asset":{"version":"2.0"}})
            pipe=AvatarProductionPipeline(root)
            plan=pipe.plan(source,root/"out.glb",identity_ref="private-face-reference")
            job=pipe.write_job(plan)
            payload=json.loads(job.read_text(encoding="utf-8"))
            self.assertTrue(payload["identity_fingerprint"])
            self.assertNotIn("private-face-reference",job.read_text(encoding="utf-8"))
            self.assertFalse(payload["privacy"]["cloud_upload_allowed"])

    def test_full_rig_requires_required_animation_pack(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);asset=root/"krishna.glb"
            target_names=list(ARKIT_52)+list(OCULUS_15)
            doc={
                "asset":{"version":"2.0"},
                "nodes":[{"name":x} for x in TALKINGHEAD_BONES],
                "skins":[{"joints":list(range(len(TALKINGHEAD_BONES)))}],
                "meshes":[{"extras":{"targetNames":target_names},
                           "primitives":[{"targets":[{} for _ in target_names]}]}],
                "animations":[{"name":x} for x in REQUIRED_CLIPS],
            }
            write_glb(asset,doc)
            out=AvatarProductionPipeline(root).validate_output(asset)
            self.assertTrue(out["ready"])
            self.assertEqual(out["missing_animation_clips"],[])

    def test_missing_animation_prevents_production_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);asset=root/"krishna.glb"
            target_names=list(ARKIT_52)+list(OCULUS_15)
            doc={
                "asset":{"version":"2.0"},
                "nodes":[{"name":x} for x in TALKINGHEAD_BONES],
                "skins":[{"joints":list(range(len(TALKINGHEAD_BONES)))}],
                "meshes":[{"extras":{"targetNames":target_names},
                           "primitives":[{"targets":[{} for _ in target_names]}]}],
                "animations":[{"name":"idle"}],
            }
            write_glb(asset,doc)
            out=AvatarProductionPipeline(root).validate_output(asset)
            self.assertFalse(out["ready"])
            self.assertIn("walk",out["missing_animation_clips"])


if __name__=="__main__":
    unittest.main()
