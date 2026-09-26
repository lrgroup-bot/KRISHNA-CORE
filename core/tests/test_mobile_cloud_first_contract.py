import json
import unittest
from pathlib import Path


class MobileCloudFirstContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[2]
        cls.mobile=cls.repo/"mobile_v3"
        cls.activity=(cls.mobile/"MainActivity.java").read_text(encoding="utf-8")
        cls.router=(cls.mobile/"MobileFreeCloudRouter.java").read_text(encoding="utf-8")
        cls.edge=(cls.mobile/"MobileEdgeBot.java").read_text(encoding="utf-8")
        cls.index=(cls.mobile/"index.html").read_text(encoding="utf-8")
        cls.ui=(cls.mobile/"hawkeye-observer-ui.js").read_text(encoding="utf-8")
        cls.manifest=json.loads((cls.mobile/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))

    def test_direct_mobile_router_is_canonical_and_keystore_backed(self):
        self.assertIn("MobileFreeCloudRouter.java",self.manifest["canonical_files"])
        self.assertTrue(self.manifest["boundaries"]["mobile_general_chat_cloud_first"])
        self.assertTrue(self.manifest["boundaries"]["mobile_openrouter_direct_free"])
        self.assertTrue(self.manifest["boundaries"]["mobile_openrouter_live_zero_price_preflight"])
        self.assertTrue(self.manifest["boundaries"]["mobile_openrouter_key_android_keystore"])
        self.assertIn("AndroidKeyStore",self.router)
        self.assertIn("AES/GCM/NoPadding",self.router)
        self.assertIn("/models",self.router)
        self.assertIn("zero_cost_verified",self.router)
        self.assertIn("automatic_paid_fallback",self.router)

    def test_normal_mobile_send_does_not_require_pc_chat_first(self):
        send=self.index.split("window.send=()=>",1)[1].split("\n\nwindow.listen",1)[0]
        self.assertIn("Krishna.chatWithAttachments",send)
        self.assertNotIn("Krishna.ensureChat",send)

    def test_private_and_action_requests_are_forced_to_pc(self):
        for token in ("PC_ATTACHMENTS","PC_LARGE_CONTEXT","PC_SENSITIVE","PC_PRIVATE_CONTEXT","PC_ACTION"):
            self.assertIn(token,self.router)
        self.assertIn("PRIVATE_CONTEXT",self.router)
        self.assertIn("HOST_ACTION",self.router)

    def test_mobile_chat_falls_back_to_pc_only_after_direct_free_attempt(self):
        block=self.activity.split("@JavascriptInterface public String chat(String m)",1)[1].split("@JavascriptInterface public String attach",1)[0]
        self.assertIn("MobileFreeCloudRouter.routeChat",block)
        self.assertIn("MobileFreeCloudRouter.chat",block)
        self.assertIn("pc_contacted",block)
        self.assertLess(block.index("MobileFreeCloudRouter.chat"),block.index("ensureChat()"))

    def test_hawkeye_direct_cloud_precedes_pc_broker(self):
        block=self.activity.split("@JavascriptInterface public String hawkeyeFreeCloudAnalyze",1)[1].split("@JavascriptInterface public String hawkeyeFreeCloudFinding",1)[0]
        self.assertIn("MobileFreeCloudRouter.analyzeImage",block)
        self.assertIn('call("/api/hawkeye/free-cloud/analyze"',block)
        self.assertLess(block.index("MobileFreeCloudRouter.analyzeImage"),block.index('call("/api/hawkeye/free-cloud/analyze"'))
        self.assertIn("contains_biometrics",block)
        self.assertIn("contains_credentials",block)
        self.assertIn("private_document",block)

    def test_pc_finding_sync_is_rate_limited(self):
        self.assertIn("lastPcFindingSyncAt",self.ui)
        self.assertIn("300000",self.ui)
        self.assertTrue(self.manifest["boundaries"]["mobile_cloud_findings_pc_sync_rate_limited"])

    def test_mobile_edge_contract_calls_pc_escalation_not_default(self):
        self.assertIn("mobile-local-free-cloud-first-selective-pc",self.edge)
        self.assertIn("private-protected-heavy-failure-escalation-only",self.edge)
        self.assertIn("PC_COMPACT_ESCALATION",self.edge)


if __name__=="__main__":
    unittest.main()
