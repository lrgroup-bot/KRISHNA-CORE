from pathlib import Path
import tempfile
import unittest

from krishna_core.video_avatar import VideoAvatarFabric


class VideoAvatarFabricTests(unittest.TestCase):
    def test_catalog_is_local_first_and_higgsfield_is_optional_only(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=VideoAvatarFabric(Path(td))
            status=fabric.status()
            rows={x["provider_id"]:x for x in status["providers"]}
            self.assertTrue(rows["musetalk"]["free_local"])
            self.assertTrue(rows["liveportrait"]["free_local"])
            self.assertTrue(rows["echomimic_v3"]["free_local"])
            self.assertTrue(rows["wan_animate_2"]["free_local"])
            self.assertFalse(rows["higgsfield"]["free_local"])
            self.assertEqual(rows["higgsfield"]["repo"],None)
            self.assertIn("optional",rows["higgsfield"]["commercial_note"].lower())
            self.assertEqual(status["recommended"]["live_chat_lipsync"],"musetalk")
            self.assertEqual(status["recommended"]["high_quality_audio_body"],"echomimic_v3")

    def test_installed_requires_real_entrypoint(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=VideoAvatarFabric(Path(td))
            root=fabric.provider_root("musetalk")
            root.mkdir(parents=True)
            self.assertFalse(fabric.installed("musetalk"))
            entry=root/"scripts"/"realtime_inference.py"
            entry.parent.mkdir(parents=True)
            entry.write_text("# test",encoding="utf-8")
            self.assertTrue(fabric.installed("musetalk"))

    def test_runtime_status_requires_source_environment_and_weights(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=VideoAvatarFabric(Path(td))
            source=fabric.provider_root("musetalk")
            entry=source/"scripts"/"realtime_inference.py"
            entry.parent.mkdir(parents=True)
            entry.write_text("# test",encoding="utf-8")
            env_python=fabric.environment_root("musetalk")/"Scripts"/"python.exe"
            env_python.parent.mkdir(parents=True)
            env_python.write_bytes(b"")
            for rel in (
                "models/musetalkV15/unet.pth",
                "models/musetalkV15/musetalk.json",
                "models/sd-vae/diffusion_pytorch_model.bin",
                "models/whisper/pytorch_model.bin",
                "models/dwpose/dw-ll_ucoco_384.pth",
            ):
                p=source/rel
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(b"x")
            runtime=fabric.runtime_status("musetalk")
            self.assertTrue(runtime["source_installed"])
            self.assertTrue(runtime["environment_ready"])
            self.assertTrue(runtime["weights_ready"])
            self.assertTrue(runtime["runtime_ready"])

    def test_higgsfield_style_goal_never_routes_to_higgsfield_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=VideoAvatarFabric(Path(td))
            row=fabric.recommend("make a Higgsfield style talking video",vram_gb=16)
            self.assertEqual(row["provider_id"],"echomimic_v3")
            self.assertTrue(row["free_local"])

    def test_low_vram_talking_video_falls_back_to_musetalk(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=VideoAvatarFabric(Path(td))
            row=fabric.recommend("image and audio talking video",vram_gb=8)
            self.assertEqual(row["provider_id"],"musetalk")

    def test_generation_contracts_are_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=VideoAvatarFabric(Path(td))
            echo=fabric.generation_contract("echomimic_v3")
            self.assertEqual(echo["inputs"],["source_image","audio_wav","prompt"])
            self.assertEqual(echo["execution"],"local subprocess adapter")
            self.assertIn("KRISHNA PC",echo["privacy"])


class VideoAvatarInstallerContractTests(unittest.TestCase):
    def test_installer_is_e_drive_local_and_does_not_auto_download_weights(self):
        root=Path(__file__).resolve().parents[2]
        text=(root/"scripts"/"INSTALL_VIDEO_AVATAR_ENGINES.ps1").read_text(encoding="utf-8-sig")
        for repo in (
            "TMElyralab/MuseTalk.git",
            "KlingAIResearch/LivePortrait.git",
            "antgroup/echomimic_v3.git",
            "Wan-Video/Wan-Animate-2.git",
        ):
            self.assertIn(repo,text)
        self.assertIn('E:\\Krishna-The GOD',text)
        self.assertIn("weights are intentionally NOT auto-downloaded",text)
        self.assertIn("higgsfield_dependency=$false",text)


if __name__=="__main__":
    unittest.main()
