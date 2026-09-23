import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.mobile_runtime_manifest import MobileRuntimeManifest


class MobileRuntimeManifestTests(unittest.TestCase):
    def test_manifest_makes_mobile_v3_the_only_android_authority(self):
        root=Path(__file__).resolve().parents[2]
        status=MobileRuntimeManifest(root,Path(tempfile.gettempdir())/"krishna-no-runtime").status()
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
        root=Path(__file__).resolve().parents[2]
        data=json.loads((root/"mobile_v3"/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))
        files=set(data["canonical_files"])
        for name in (
            "MobileEdgeBot.java","HawkeyeEvidenceCuratorBot.java","HawkeyeCrypto.java",
            "HawkeyeBackgroundSync.java","HawkeyeSyncJobService.java"
        ):
            self.assertIn(name,files)


if __name__=="__main__":
    unittest.main()
