import unittest
from pathlib import Path


class HawkeyeMobileObserverContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[2]
        cls.mobile=(cls.repo/"mobile_v3")
        cls.index=(cls.mobile/"index.html").read_text(encoding="utf-8")
        cls.ui=(cls.mobile/"hawkeye-observer-ui.js").read_text(encoding="utf-8")
        cls.activity=(cls.mobile/"MainActivity.java").read_text(encoding="utf-8")
        cls.workflow=(cls.repo/".github"/"workflows"/"build-mobile-v3.yml").read_text(encoding="utf-8")

    def test_camera_hud_exposes_requested_controls(self):
        for token in ("LEARN","SEARCH","PHOTO+DATA","REC+DATA","hawkeye-observer-ui.js"):
            self.assertIn(token,self.index)

    def test_local_object_layer_and_auto_zoom_are_wired(self):
        self.assertIn("hawkeyeDetectObjects",self.activity)
        self.assertIn("HawkeyeMobileVision.detect",self.activity)
        self.assertIn("ML_KIT_OBJECT_TRACKER",(self.mobile/"HawkeyeMobileVision.java").read_text(encoding="utf-8"))
        self.assertIn("autoZoom",self.ui)
        self.assertIn("applyConstraints",self.ui)
        self.assertIn("objectOverlay",self.ui)

    def test_research_uses_user_browser_custom_tab_without_bridge(self):
        self.assertIn("CustomTabsIntent",self.activity)
        self.assertIn("user-default-custom-tab",self.activity)
        self.assertIn('"krishna_js_bridge_exposed",false',self.activity)
        self.assertIn("openResearchQuery",self.ui)

    def test_capture_is_explicit_and_local(self):
        self.assertIn("saveHawkeyeCapture",self.activity)
        self.assertIn("KRISHNA/HAWKEYE",self.activity)
        self.assertIn("raw_cloud_upload:false",self.ui)
        self.assertIn("photo()",self.ui)
        self.assertIn("record()",self.ui)

    def test_apk_build_includes_required_dependencies_and_assets(self):
        self.assertIn("androidx.browser:browser:1.10.0",self.workflow)
        self.assertIn("com.google.mlkit:object-detection:17.0.2",self.workflow)
        self.assertIn("hawkeye-observer-ui.js",self.workflow)
        self.assertIn("KRISHNA-v3.8-HAWKEYE-Observer-APK",self.workflow)


if __name__=="__main__":
    unittest.main()
