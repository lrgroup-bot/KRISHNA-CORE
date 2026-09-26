import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.mobile_runtime_manifest import MobileRuntimeManifest


class MobileRuntimeManifestTests(unittest.TestCase):
    def test_manifest_makes_mobile_v3_the_only_android_authority(self):
        status=MobileRuntimeManifest(
            runtime_root=Path(tempfile.gettempdir())/"krishna-no-runtime"
        ).status()
        self.assertEqual(status["version"],"krishna-mobile-canonical-v1")
        self.assertEqual(status["canonical_android_source"],"mobile_v3")
        self.assertEqual(status["package_id"],"com.krishna.mobile")
        self.assertTrue(status["source_ready"])
        self.assertFalse(status["boundaries"]["dashboard_ui"])
        self.assertTrue(status["boundaries"]["mobile_edge_preprocessing"])
        self.assertEqual(
            status["pc_runtime_companion"]["classification"],
            "COMPATIBILITY_PC_SIDE_NOT_ANDROID_AUTHORITY",
        )
        self.assertFalse(status["migration"]["automatic_delete"])

    def test_manifest_lists_edge_curator_crypto_and_sync(self):
        manifest=MobileRuntimeManifest()
        data=json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
        files=set(data["canonical_files"])
        for name in (
            "MobileEdgeBot.java","HawkeyeEvidenceCuratorBot.java","HawkeyeCrypto.java",
            "HawkeyeBackgroundSync.java","HawkeyeSyncJobService.java",
            "KrishnaPrivateCore.java","HawkeyeMobileVision.java","hawkeye-observer-ui.js",
            "mobile-cloud-client.js"
        ):
            self.assertIn(name,files)
        self.assertTrue(data["boundaries"]["hawkeye_learning_observer"])
        self.assertTrue(data["boundaries"]["local_object_tracking"])
        self.assertTrue(data["boundaries"]["user_browser_custom_tab"])
        self.assertFalse(data["boundaries"]["unknown_face_social_identity_search"])
        self.assertTrue(data["boundaries"]["automatic_private_core_bootstrap"])
        self.assertTrue(data["boundaries"]["zero_code_pairing_request"])
        self.assertTrue(data["boundaries"]["large_media_sync_unmetered_only"])
        self.assertTrue(data["boundaries"]["large_media_same_lan_required"])
        self.assertFalse(data["boundaries"]["cellular_large_media_upload"])
        self.assertTrue(data["boundaries"]["large_media_resumable"])
        self.assertTrue(data["boundaries"]["large_media_sha256_verified"])
        self.assertTrue(data["boundaries"]["mobile_retains_verified_copy_default"])
        self.assertFalse(data["boundaries"]["delete_after_verified_default"])
        self.assertTrue(data["boundaries"]["mobile_direct_free_cloud_chat_session"])
        self.assertFalse(data["boundaries"]["mobile_direct_cloud_permanent_key"])
        self.assertTrue(data["boundaries"]["mobile_direct_cloud_short_lived_token"])
        self.assertFalse(data["boundaries"]["mobile_general_chat_pc_default"])
        self.assertTrue(data["boundaries"]["mobile_private_action_chat_pc_required"])
        self.assertTrue(data["boundaries"]["heavy_optional_capabilities_lazy"])
        self.assertEqual(data["boundaries"]["mobile_pc_poll_interval_foreground_seconds"],30)
        self.assertTrue(data["boundaries"]["mobile_cloud_session_resumption"])
        self.assertFalse(data["boundaries"]["mobile_cloud_token_persisted"])
        self.assertFalse(data["boundaries"]["mobile_cloud_token_broker_per_turn"])


if __name__=="__main__":
    unittest.main()
