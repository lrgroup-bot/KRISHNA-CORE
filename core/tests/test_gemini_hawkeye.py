import os
import unittest
from unittest.mock import patch

from krishna_core.gemini_hawkeye import GeminiHawkeyeBridge


class GeminiHawkeyeBridgeTests(unittest.TestCase):
    def make(self):
        return GeminiHawkeyeBridge(gateway=None,timeout=5)

    def test_status_keeps_permanent_credential_on_pc(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret","KRISHNA_GEMINI_MODEL":"gemini-3.8-flash"},clear=False):
            row=self.make().status()
        self.assertTrue(row["configured"])
        self.assertEqual(row["credential_location"],"KRISHNA_PC_ONLY")
        self.assertFalse(row["mobile_permanent_key"])
        self.assertTrue(row["hard_zero_credit"])
        self.assertFalse(row["inference_allowed"])

    def test_selected_keyframe_requires_explicit_cloud_approval(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret"},clear=False):
            bridge=self.make()
            with self.assertRaises(PermissionError):
                bridge.analyze_image(
                    b"jpeg","image/jpeg","inspect",
                    {"selected_keyframe":True,"cloud_approved":False},
                )

    def test_sensitive_keyframe_is_blocked_before_network(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret"},clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request") as req:
                with self.assertRaises(PermissionError):
                    bridge.analyze_image(
                        b"jpeg","image/jpeg","inspect",
                        {"selected_keyframe":True,"cloud_approved":True,"contains_biometrics":True},
                    )
                req.assert_not_called()

    def test_selected_non_sensitive_keyframe_is_blocked_without_zero_credit_proof(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret","KRISHNA_GEMINI_MODEL":"gemini-3.8-flash"},clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request") as req:
                with self.assertRaisesRegex(PermissionError,"hard zero-credit policy"):
                    bridge.analyze_image(
                        b"jpeg","image/jpeg","inspect",
                        {"selected_keyframe":True,"cloud_approved":True},
                    )
                req.assert_not_called()

    def test_live_token_is_blocked_without_zero_credit_proof(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret","KRISHNA_GEMINI_LIVE_MODEL":"gemini-3.8-live"},clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request") as req:
                with self.assertRaisesRegex(PermissionError,"hard zero-credit policy"):
                    bridge.mint_live_token({"cloud_approved":True,"user_explicit":True})
                req.assert_not_called()

    def test_live_token_blocks_sensitive_scene(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret"},clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request") as req:
                with self.assertRaises(PermissionError):
                    bridge.mint_live_token({
                        "cloud_approved":True,
                        "user_explicit":True,
                        "contains_credentials":True,
                    })
                req.assert_not_called()


if __name__=="__main__":
    unittest.main()
