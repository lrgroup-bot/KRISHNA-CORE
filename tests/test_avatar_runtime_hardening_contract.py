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
        cls.renderer=(ROOT/"mobile_v3"/"avatar-renderer.js").read_text(encoding="utf-8")

    def test_server_promotes_only_complete_production_asset(self):
        self.assertIn('production.get("production_ready")',self.server)
        self.assertIn('"active_asset":active_report',self.server)
        self.assertIn('"active_compatible":bool(active_report.get("ready"))',self.server)
        self.assertIn('"active_ready":bool(active_report.get("production_ready"))',self.server)
        self.assertIn('"viseme_lipsync":False',self.server)

    def test_desktop_uses_active_asset_and_real_viseme_target_updates(self):
        self.assertIn("a.asset_pipeline?.active_asset",self.web)
        self.assertIn("head.mtAvatar?.[key]",self.web)
        self.assertNotIn("head.setValue(key,value,40)",self.web)
        self.assertIn("__krishnaMotionNames",self.web)
        self.assertIn("getMotionNames",self.web)

    def test_prepare_and_acceptance_use_full_production_readiness(self):
        self.assertIn("$Audit.production_ready",self.prepare)
        self.assertIn("$verify.production_ready",self.prepare)
        self.assertIn("$sourceAudit.production_ready",self.prepare)
        self.assertIn("$existingProduction.production_ready",self.prepare)
        self.assertIn("$avatar.asset_pipeline.active_ready",self.accept)
        self.assertIn("$avatar.asset_pipeline.active_asset",self.accept)

    def test_mobile_sync_validates_glb_v2_and_preserves_previous_avatar(self):
        self.assertIn("avatar GLB header is incomplete",self.mobile)
        self.assertIn("avatar GLB version",self.mobile)
        self.assertIn("declared length does not match downloaded bytes",self.mobile)
        self.assertIn("krishna.production.glb.bak",self.mobile)
        self.assertIn("previous avatar restored",self.mobile)

    def test_mobile_renderer_fails_to_visible_fallback_on_webgl_loss(self):
        self.assertIn("webglcontextlost",self.renderer)
        self.assertIn("disposeRenderer()",self.renderer)
        self.assertIn("window.showKrishnaFallback?.(reason)",self.renderer)


if __name__=="__main__":
    unittest.main()
