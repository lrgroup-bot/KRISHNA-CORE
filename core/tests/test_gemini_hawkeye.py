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

    def test_selected_non_sensitive_keyframe_can_use_gemini(self):
        response={"candidates":[{"content":{"parts":[{"text":"Observed: control panel."}]}}]}
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret","KRISHNA_GEMINI_MODEL":"gemini-3.8-flash"},clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request",return_value=response) as req:
                row=bridge.analyze_image(
                    b"jpeg","image/jpeg","inspect",
                    {"selected_keyframe":True,"cloud_approved":True},
                )
        self.assertEqual(row["provider"],"google-gemini")
        self.assertEqual(row["model"],"gemini-3.8-flash")
        self.assertTrue(row["selected_keyframe_cloud_upload"])
        self.assertFalse(row["continuous_raw_camera_upload"])
        self.assertIn("control panel",row["analysis"])
        self.assertIn(":generateContent",req.call_args.args[0])

    def test_live_token_is_one_use_and_short_lived(self):
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-secret","KRISHNA_GEMINI_LIVE_MODEL":"gemini-3.8-live","KRISHNA_GEMINI_FREE_ONLY":"1"},clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request",return_value={"name":"ephemeral-token"}) as req:
                row=bridge.mint_live_token({"cloud_approved":True,"user_explicit":True})
        self.assertEqual(row["token"],"ephemeral-token")
        self.assertEqual(row["uses"],1)
        self.assertEqual(row["live_model"],"gemini-3.8-live")
        self.assertFalse(row["permanent_key_exposed"])
        payload=req.call_args.args[2]
        self.assertEqual(payload["uses"],1)
        self.assertEqual(payload["liveConnectConstraints"]["model"],"models/gemini-3.8-live")
        self.assertEqual(payload["liveConnectConstraints"]["config"]["responseModalities"],["AUDIO"])
        self.assertIn("outputAudioTranscription",payload["liveConnectConstraints"]["config"])

    def test_mobile_chat_token_is_text_only_and_free_only(self):
        with patch.dict(os.environ,{
            "GEMINI_API_KEY":"test-secret",
            "KRISHNA_GEMINI_FREE_ONLY":"1",
            "KRISHNA_GEMINI_LIVE_TEXT_MODEL":"gemini-3.8-live",
        },clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request",return_value={"name":"chat-token"}) as req:
                row=bridge.mint_live_token({
                    "cloud_approved":True,"user_explicit":True,"purpose":"chat",
                })
        self.assertEqual(row["purpose"],"chat")
        self.assertEqual(row["response_modalities"],["AUDIO"])
        self.assertTrue(row["free_only"])
        payload=req.call_args.args[2]
        config=payload["liveConnectConstraints"]["config"]
        self.assertEqual(config["responseModalities"],["AUDIO"])
        self.assertIn("outputAudioTranscription",config)

    def test_mobile_live_session_rejects_non_free_profile(self):
        with patch.dict(os.environ,{
            "GEMINI_API_KEY":"test-secret","KRISHNA_GEMINI_FREE_ONLY":"0",
        },clear=False):
            bridge=self.make()
            with patch.object(bridge,"_request") as req:
                with self.assertRaises(PermissionError):
                    bridge.mint_live_token({
                        "cloud_approved":True,"user_explicit":True,"purpose":"chat",
                    })
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
