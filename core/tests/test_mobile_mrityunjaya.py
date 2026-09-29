import json
import unittest
from pathlib import Path


class MobileMrityunjayaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.mobile=cls.root/"mobile_v3"
        cls.healer=(cls.mobile/"MrityunjayaMobileHealer.java").read_text(encoding="utf-8")
        cls.activity=(cls.mobile/"MainActivity.java").read_text(encoding="utf-8")
        cls.index=(cls.mobile/"index.html").read_text(encoding="utf-8")
        cls.runtime=json.loads((cls.mobile/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))

    def test_healer_is_runtime_only_and_non_mutating(self):
        boundaries=self.runtime["boundaries"]
        self.assertTrue(boundaries["mobile_mrityunjaya_auto_healer"])
        self.assertEqual(boundaries["mobile_auto_heal_scope"],"runtime-only")
        self.assertFalse(boundaries["mobile_healer_source_mutation"])
        self.assertFalse(boundaries["mobile_healer_apk_mutation"])
        self.assertFalse(boundaries["mobile_healer_security_policy_mutation"])
        self.assertFalse(boundaries["mobile_healer_credential_mutation"])
        self.assertIn('"source_mutation",false',self.healer)
        self.assertIn('"apk_mutation",false',self.healer)

    def test_bounded_circuit_breaker_prevents_repair_loops(self):
        self.assertIn("MAX_HEALS_PER_WINDOW=4",self.healer)
        self.assertIn("CIRCUIT_BREAK_MS=120000L",self.healer)
        self.assertIn('"SAFE_MODE"',self.healer)
        self.assertIn("Repeated recovery loop blocked",self.healer)

    def test_native_crash_and_webview_renderer_are_recoverable(self):
        self.assertIn("pending_native_crash",self.healer)
        self.assertIn("Thread.setDefaultUncaughtExceptionHandler",self.healer)
        self.assertIn("onRenderProcessGone",self.activity)
        self.assertIn('"webview-renderer"',self.activity)
        self.assertIn("recreate();",self.activity)

    def test_ui_watchdog_and_javascript_recovery_are_present(self):
        self.assertIn("runMobileHealthWatch",self.activity)
        self.assertIn("10000L",self.activity)
        self.assertIn('"javascript-runtime"',self.activity)
        self.assertIn("window.onerror",self.index)
        self.assertIn("window.onunhandledrejection",self.index)
        self.assertIn("Krishna.mrityunjayaFault",self.index)

    def test_camera_recovery_respects_permission_boundary(self):
        self.assertIn("camera-session",self.index)
        self.assertIn("notallowed|permission|denied|securityerror",self.index.lower())
        self.assertIn("window.mrityunjayaRecover",self.index)
        self.assertIn("Camera session restarted and live stream verified",self.index)

    def test_private_core_recovery_requires_repeated_failure_and_rate_limit(self):
        self.assertIn("coreFailureStreak>=2",self.activity)
        self.assertIn("30000L",self.activity)
        self.assertIn("KrishnaPrivateCore.discoverLan",self.activity)
        self.assertIn("Private Core link rediscovered",self.activity)

    def test_ui_is_hidden_when_healthy(self):
        self.assertEqual(self.runtime["boundaries"]["mobile_healer_ui"],"hidden-unless-recovering")
        self.assertIn('id="mrityunjayaChip"',self.index)
        self.assertIn(".mrityunjayaChip{",self.index)
        self.assertIn("opacity:0",self.index)
        self.assertIn("MRUTYUNJAYA · ",self.index)

    def test_android_studio_test_hooks_exist_without_main_ui_button(self):
        self.assertIn("mrityunjayaStatus",self.activity)
        self.assertIn("mrityunjayaTest",self.activity)
        self.assertIn("mrityunjayaResetVolatileState",self.activity)
        self.assertNotIn('id="mrityunjayaQuick"',self.index)
        self.assertNotIn(">MRUTYUNJAYA</button>",self.index)

    def test_canonical_files_include_mobile_healer(self):
        self.assertIn("MrityunjayaMobileHealer.java",self.runtime["canonical_files"])


if __name__=="__main__":
    unittest.main()
