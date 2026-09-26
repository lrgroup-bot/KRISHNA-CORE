import json
import unittest
from pathlib import Path


class MobileDirectFreeCloudContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]

    def test_mobile_client_is_direct_session_not_pc_per_turn(self):
        js=(self.root/"mobile_v3"/"mobile-cloud-client.js").read_text(encoding="utf-8")
        self.assertIn("mobileFreeCloudSession",js)
        self.assertIn("BidiGenerateContentConstrained",js)
        self.assertIn("outputAudioTranscription",js)
        self.assertNotIn("localStorage",js)
        self.assertNotIn("GEMINI_API_KEY",js)
        self.assertNotIn("chatWithAttachments",js)

    def test_private_and_action_chat_still_has_pc_fallback(self):
        html=(self.root/"mobile_v3"/"index.html").read_text(encoding="utf-8")
        self.assertIn("mobileCloud.eligible",html)
        self.assertIn("Krishna.chatWithAttachments",html)
        self.assertIn("if(!cloud.audio_played)speak(text)",html)

    def test_server_and_remote_policy_expose_only_short_lived_session(self):
        server=(self.root/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        remote=(self.root/"core"/"krishna_core"/"remote_access.py").read_text(encoding="utf-8")
        self.assertIn('/api/mobile/free-cloud/session',server)
        self.assertIn('/api/mobile/free-cloud/status',server)
        self.assertIn('/api/mobile/free-cloud/session',remote)
        self.assertIn('"permanent_key_on_mobile":False',server)
        self.assertIn('"paid_fallback":False',server)

    def test_manifest_keeps_free_only_and_pc_private_escalation(self):
        data=json.loads((self.root/"mobile_v3"/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))
        self.assertEqual(data["model_policy"]["mobile_cloud_mode"],"verified-free-only")
        self.assertFalse(data["model_policy"]["automatic_paid_fallback"])
        self.assertFalse(data["boundaries"]["mobile_general_chat_pc_default"])
        self.assertTrue(data["boundaries"]["mobile_private_action_chat_pc_required"])


if __name__=="__main__":
    unittest.main()
