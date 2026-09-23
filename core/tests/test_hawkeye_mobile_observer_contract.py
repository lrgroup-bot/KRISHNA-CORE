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

    def test_lens_style_rich_perception_is_local(self):
        vision=(self.mobile/"HawkeyeMobileVision.java").read_text(encoding="utf-8")
        for token in ("ML_KIT_LOCAL_RICH","TextRecognition","BarcodeScanning","PoseDetection","SubjectSegmentation"):
            self.assertIn(token,vision)
        self.assertIn('"identity","UNKNOWN"',vision)
        self.assertIn('"biometric_web_search",false',vision)
        self.assertIn("hawkeyeRichPerception",self.activity)
        self.assertIn("richPerception",self.ui)
        self.assertIn("recommended_next_scan",self.ui)
        self.assertIn("FaceLandmark",vision)
        self.assertIn('"landmarks",landmarks',vision)
        self.assertIn("toggleTargetLock",self.ui)
        self.assertIn("lockedTrackingId",self.ui)
        self.assertIn('id="cameraLock"',self.index)
        self.assertIn("state.rich&&state.rich.ocr",self.ui)

    def test_gemini_mobile_uses_pc_credential_and_ephemeral_live_token(self):
        pc=(self.repo/"core"/"krishna_core"/"gemini_hawkeye.py").read_text(encoding="utf-8")
        self.assertIn("x-goog-api-key",pc)
        self.assertIn("KRISHNA_PC_ONLY",pc)
        self.assertIn("auth_tokens",pc)
        self.assertIn("hawkeyeGeminiAnalyze",self.activity)
        self.assertIn("hawkeyeGeminiLiveToken",self.activity)
        self.assertIn("BidiGenerateContentConstrained",self.ui)
        self.assertIn("selected_keyframe:true",self.ui)
        mobile=self.activity+"\n"+self.ui+"\n"+self.index
        self.assertNotIn("x-goog-api-key",mobile)
        self.assertNotIn("GEMINI_API_KEY",mobile)
        self.assertNotIn("AIza",mobile)

    def test_google_lens_is_not_required_for_hawkeye_capture(self):
        runtime=(self.mobile/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8")
        self.assertIn('"google_lens_required": false',runtime)
        self.assertIn('"lens_style_capture_inside_hawkeye": true',runtime)
        self.assertIn("openResearchQuery",self.activity)
        self.assertIn("TextRecognition", (self.mobile/"HawkeyeMobileVision.java").read_text(encoding="utf-8"))

    def test_apk_build_includes_required_dependencies_and_assets(self):
        self.assertIn("androidx.browser:browser:1.8.0",self.workflow)
        self.assertIn("com.google.mlkit:object-detection:17.0.2",self.workflow)
        self.assertIn("com.google.mlkit:text-recognition:16.0.1",self.workflow)
        self.assertIn("com.google.mlkit:text-recognition-devanagari:16.0.1",self.workflow)
        self.assertIn("com.google.mlkit:barcode-scanning:17.3.0",self.workflow)
        self.assertIn("com.google.mlkit:pose-detection:18.0.0-beta5",self.workflow)
        self.assertIn("play-services-mlkit-subject-segmentation:16.0.0-beta1",self.workflow)
        self.assertIn("hawkeye-observer-ui.js",self.workflow)
        self.assertIn("KRISHNA-v3.8-HAWKEYE-Observer-APK",self.workflow)


if __name__=="__main__":
    unittest.main()
