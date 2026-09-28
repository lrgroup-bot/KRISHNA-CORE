import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


class KrishnaMobileAPKReleaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow=(ROOT/".github"/"workflows"/"build-mobile-v3.yml").read_text(encoding="utf-8")
        cls.release=(ROOT/"mobile_v3"/"APK_RELEASE.md").read_text(encoding="utf-8")

    def test_one_canonical_apk_name_is_built_audited_and_emulator_tested(self):
        self.assertIn("dist/KRISHNA-Mobile.apk",self.workflow)
        self.assertIn('apk=Path("dist/KRISHNA-Mobile.apk")',self.workflow)
        self.assertIn("VERIFY_KRISHNA_APK.py dist/KRISHNA-Mobile.apk com.krishna.mobile",self.workflow)
        self.assertNotIn("KRISHNA-v3.9-Production-Candidate.apk",self.workflow)

    def test_release_artifact_contains_apk_checksum_and_build_manifest(self):
        self.assertIn("name: KRISHNA-Mobile-APK",self.workflow)
        self.assertIn("dist/KRISHNA-Mobile.apk.sha256",self.workflow)
        self.assertIn("dist/KRISHNA-Mobile-build.json",self.workflow)
        self.assertIn("if-no-files-found: error",self.workflow)
        self.assertIn("VERIFY_KRISHNA_MOBILE_SCREENSHOT.py",self.workflow)

    def test_release_document_keeps_download_outside_source_checkout(self):
        self.assertIn(r"E:\KRISHNA-Mobile\KRISHNA-Mobile.apk",self.release)
        self.assertIn("debug-signed private test APK",self.release)
        self.assertIn("Compare the SHA-256",self.release)


if __name__=="__main__":
    unittest.main()
