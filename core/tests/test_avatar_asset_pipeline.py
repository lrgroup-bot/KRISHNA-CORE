import json
import struct
import tempfile
import unittest
from pathlib import Path

from krishna_core.avatar_asset_pipeline import (
    ARKIT_52, OCULUS_15, TALKINGHEAD_BONES, AvatarAssetInspector,
)


def write_glb(path: Path, document: dict):
    raw=json.dumps(document,separators=(",",":")).encode("utf-8")
    raw+=b" " * ((4-len(raw)%4)%4)
    total=12+8+len(raw)
    path.write_bytes(struct.pack("<4sII",b"glTF",2,total)+struct.pack("<II",len(raw),0x4E4F534A)+raw)


class AvatarAssetPipelineTests(unittest.TestCase):
    def test_ready_asset_requires_full_body_fingers_arkit_and_visemes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);asset=root/"krishna.glb"
            document={
                "asset":{"version":"2.0","generator":"unit-test"},
                "nodes":[{"name":"mixamorig"+name} for name in TALKINGHEAD_BONES],
                "skins":[{"joints":list(range(len(TALKINGHEAD_BONES)))}],
                "meshes":[{"extras":{"targetNames":list(ARKIT_52)+list(OCULUS_15)},
                           "primitives":[{"targets":[{} for _ in range(len(ARKIT_52)+len(OCULUS_15))]}]}],
                "animations":[{"name":"idle"},{"name":"flute"}],
            }
            write_glb(asset,document)
            report=AvatarAssetInspector(root/"audit.json").inspect(asset)
            self.assertTrue(report["ready"])
            self.assertEqual(report["stage"],"production-ready")
            self.assertTrue(report["body"]["ready"])
            self.assertTrue(report["face"]["arkit"]["ready"])
            self.assertTrue(report["face"]["oculus_visemes"]["ready"])
            self.assertEqual(report["animation_count"],2)
            self.assertTrue((root/"audit.json").is_file())

    def test_unrigged_asset_is_never_reported_ready(self):
        with tempfile.TemporaryDirectory() as td:
            asset=Path(td)/"plain.glb"
            write_glb(asset,{"asset":{"version":"2.0"},"nodes":[{"name":"Mesh"}],"meshes":[{}]})
            report=AvatarAssetInspector().inspect(asset)
            self.assertFalse(report["ready"])
            self.assertEqual(report["stage"],"unrigged")
            self.assertIn("no glTF skin/armature binding detected",report["issues"])

    def test_missing_fingers_fails_talkinghead_body_gate(self):
        with tempfile.TemporaryDirectory() as td:
            asset=Path(td)/"body.glb"
            core=[x for x in TALKINGHEAD_BONES if "HandThumb" not in x and "HandIndex" not in x and
                  "HandMiddle" not in x and "HandRing" not in x and "HandPinky" not in x]
            write_glb(asset,{
                "asset":{"version":"2.0"},
                "nodes":[{"name":x} for x in core],
                "skins":[{"joints":list(range(len(core)))}],
                "meshes":[{"extras":{"targetNames":list(ARKIT_52)+list(OCULUS_15)},
                           "primitives":[{"targets":[{} for _ in range(len(ARKIT_52)+len(OCULUS_15))]}]}],
            })
            report=AvatarAssetInspector().inspect(asset)
            self.assertFalse(report["body"]["ready"])
            self.assertFalse(report["ready"])
            self.assertTrue(any("HandThumb" in x for x in report["body"]["missing_core_bones"]))

    def test_named_nodes_not_bound_to_skin_are_not_a_valid_body_rig(self):
        with tempfile.TemporaryDirectory() as td:
            asset=Path(td)/"fake-rig.glb"
            nodes=[{"name":x} for x in TALKINGHEAD_BONES]+[{"name":"OnlyJoint"}]
            target_names=list(ARKIT_52)+list(OCULUS_15)
            write_glb(asset,{
                "asset":{"version":"2.0"},
                "nodes":nodes,
                "skins":[{"joints":[len(nodes)-1]}],
                "meshes":[{"extras":{"targetNames":target_names},
                           "primitives":[{"targets":[{} for _ in target_names]}]}],
            })
            report=AvatarAssetInspector().inspect(asset)
            self.assertFalse(report["body"]["ready"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["skin_joint_count"],1)

    def test_facial_target_names_without_morph_slots_are_not_a_face_rig(self):
        with tempfile.TemporaryDirectory() as td:
            asset=Path(td)/"fake-face.glb"
            write_glb(asset,{
                "asset":{"version":"2.0"},
                "nodes":[{"name":x} for x in TALKINGHEAD_BONES],
                "skins":[{"joints":list(range(len(TALKINGHEAD_BONES)))}],
                "meshes":[{"extras":{"targetNames":list(ARKIT_52)+list(OCULUS_15)}}],
            })
            report=AvatarAssetInspector().inspect(asset)
            self.assertFalse(report["face"]["ready"])
            self.assertFalse(report["ready"])
            self.assertEqual(report["morph_target_count"],0)

    def test_invalid_glb_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            asset=Path(td)/"broken.glb";asset.write_bytes(b"not-a-glb")
            report=AvatarAssetInspector().inspect(asset)
            self.assertFalse(report["ready"])
            self.assertEqual(report["stage"],"invalid")
            self.assertTrue(report["issues"])


if __name__=="__main__":
    unittest.main()
