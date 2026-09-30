import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


class AvatarRuntimeHardeningContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        cls.web=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8")
        cls.prepare=(ROOT/"scripts"/"PREPARE_KRISHNA_AVATAR.ps1").read_text(encoding="utf-8")
        cls.accept=(ROOT/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        cls.mobile=(ROOT/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8")
        cls.mobile_index=(ROOT/"mobile_v3"/"index.html").read_text(encoding="utf-8")

    def test_server_promotes_only_complete_production_asset(self):
        self.assertIn('production.get("production_ready")',self.server)
        self.assertIn('"active_asset":active_report',self.server)
        self.assertIn('"active_compatible":bool(active_report.get("ready"))',self.server)
        self.assertIn('"active_ready":bool(active_report.get("production_ready"))',self.server)
        self.assertIn('"viseme_lipsync":False',self.server)

    def test_desktop_opens_assistant_without_avatar_stage(self):
        self.assertIn('id="assistantOm"',self.web)
        self.assertIn('onclick="toggleKrishnaPopup(true)"',self.web)
        self.assertNotIn('id="krishnaAvatar"',self.web)
        self.assertNotIn("avatarState(",self.web)

    def test_prepare_and_acceptance_use_full_production_readiness(self):
        self.assertIn("$Audit.production_ready",self.prepare)
        self.assertIn("$verify.production_ready",self.prepare)
        self.assertIn("$sourceAudit.production_ready",self.prepare)
        self.assertIn("$existingProduction.production_ready",self.prepare)
        self.assertIn("$avatar.asset_pipeline.active_ready",self.accept)
        self.assertIn("$avatar.asset_pipeline.active_asset",self.accept)

    def test_mobile_does_not_sync_avatar_on_launch(self):
        self.assertNotIn("avatarSyncAsync",self.mobile)

    def test_mobile_does_not_boot_avatar_renderer(self):
        self.assertFalse((ROOT/"mobile_v3"/"avatar-renderer.js").exists())
        self.assertNotIn("avatar-renderer.js",self.mobile_index)
        self.assertNotIn("showKrishnaFallback",self.mobile_index)


if __name__=="__main__":
    unittest.main()
