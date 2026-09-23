import json
import unittest
from pathlib import Path


class HawkeyeRequestedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.mobile=cls.root/"mobile_v3"
        cls.index=(cls.mobile/"index.html").read_text(encoding="utf-8")
        cls.ui=(cls.mobile/"hawkeye-observer-ui.js").read_text(encoding="utf-8")
        cls.activity=(cls.mobile/"MainActivity.java").read_text(encoding="utf-8")
        cls.vision=(cls.mobile/"HawkeyeMobileVision.java").read_text(encoding="utf-8")
        cls.observer=(cls.root/"core"/"krishna_core"/"hawkeye_learning_observer.py").read_text(encoding="utf-8")
        cls.runtime=json.loads((cls.mobile/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))
        cls.mobile_ci=(cls.root/".github"/"workflows"/"build-mobile-v3.yml").read_text(encoding="utf-8")
        cls.core_ci=(cls.root/".github"/"workflows"/"test-core.yml").read_text(encoding="utf-8")
        cls.long_ci=(cls.root/".github"/"workflows"/"long-context-regression.yml").read_text(encoding="utf-8")
        cls.windows_ci=(cls.root/".github"/"workflows"/"build-console.yml").read_text(encoding="utf-8")

    def test_01_requested_camera_controls(self):
        for token in ("LEARN","SEARCH","PHOTO+DATA","REC+DATA"):
            self.assertIn(token,self.index)

    def test_02_observer_ui_is_loaded_and_defined(self):
        self.assertIn('<script src="hawkeye-observer-ui.js"></script>',self.index)
        self.assertIn("window.HawkeyeObserverUI=",self.ui)

    def test_03_mlkit_object_detector_is_wired(self):
        self.assertIn("ML_KIT_OBJECT_TRACKER",self.vision)
        self.assertIn("HawkeyeMobileVision.detect",self.activity)
        self.assertIn("com.google.mlkit:object-detection",self.mobile_ci)

    def test_04_tracking_ids_are_returned_and_rendered(self):
        self.assertIn('"tracking_id"',self.vision)
        self.assertIn("item.tracking_id",self.ui)

    def test_05_auto_zoom_is_real_capability_gated(self):
        self.assertIn("autoZoom",self.ui)
        self.assertIn("getCapabilities",self.ui)
        self.assertIn("caps.zoom",self.ui)
        self.assertIn("applyConstraints",self.ui)

    def test_06_live_object_overlay_exists(self):
        self.assertIn("objectOverlay",self.ui)
        self.assertIn("fillText",self.ui)
        self.assertIn("top.confidence",self.ui)

    def test_07_research_uses_android_custom_tabs(self):
        self.assertIn("CustomTabsIntent",self.activity)
        self.assertIn("openResearchQuery",self.activity)

    def test_08_arbitrary_web_pages_do_not_receive_privileged_bridge(self):
        self.assertIn('web.addJavascriptInterface(bridge,"Krishna")',self.activity)
        self.assertIn("shouldOverrideUrlLoading",self.activity)
        self.assertIn("user-default-custom-tab",self.activity)
        self.assertIn('"krishna_js_bridge_exposed",false',self.activity)

    def test_09_capture_is_local_explicit_and_bounded(self):
        self.assertIn("12*1024*1024",self.activity)
        self.assertIn("20*1024*1024",self.activity)
        self.assertIn("setTimeout(stopRecording,8000)",self.ui)
        self.assertIn("KRISHNA/HAWKEYE",self.activity)

    def test_10_capture_metadata_forces_no_raw_cloud_upload(self):
        self.assertIn("raw_cloud_upload:false",self.ui)
        self.assertIn('metadata.put("raw_cloud_upload",false)',self.activity)
        self.assertIn("sanitizeCaptureMetadata",self.activity)

    def test_11_learning_observer_routes_through_universal_brahma_and_rishis(self):
        self.assertIn("self.universal_learning.ingest",self.observer)
        self.assertIn("self.brahma.intake",self.observer)
        self.assertIn("self.council.specialist_team",self.observer)
        self.assertIn('"knowledge_status": "candidate"',self.observer)

    def test_12_learning_observer_stores_distilled_not_raw_media(self):
        self.assertIn('"raw_media_stored_here": False',self.observer)
        self.assertIn('"distilled_finding_only": True',self.observer)

    def test_13_unknown_face_to_social_search_is_disabled(self):
        self.assertIn('"face_to_social_search": False',self.observer)
        self.assertFalse(self.runtime["boundaries"]["unknown_face_social_identity_search"])

    def test_14_allowed_known_identity_research_bases_exist(self):
        self.assertIn('"user_supplied", "enrolled_consented_match"',self.observer)
        self.assertIn("site:linkedin.com/in",self.observer)
        self.assertIn("site:instagram.com",self.observer)

    def test_15_canonical_mobile_runtime_contains_required_assets_and_classes(self):
        files=set(self.runtime["canonical_files"])
        for name in ("index.html","realtime-client.js","hawkeye-observer-ui.js",
                     "HawkeyeMobileVision.java","HawkeyeOfflinePerception.java",
                     "HawkeyeEvidenceCuratorBot.java","HawkeyeEdgeMemory.java",
                     "HawkeyeBackgroundSync.java","HawkeyeSensorFusion.java"):
            self.assertIn(name,files)

    def test_16_android_build_pipeline_compiles_and_emulator_retests(self):
        self.assertIn(":app:assembleDebug",self.mobile_ci)
        self.assertIn("--stacktrace",self.mobile_ci)
        self.assertIn("org.gradle.jvmargs=-Xmx4096m",self.mobile_ci)
        self.assertIn("android-emulator-runner",self.mobile_ci)
        self.assertIn("VERIFY_KRISHNA_APK.py",self.mobile_ci)

    def test_17_core_pipeline_runs_windows_and_linux_tests(self):
        self.assertIn("ubuntu-latest",self.core_ci)
        self.assertIn("windows-latest",self.core_ci)
        self.assertIn("python -m unittest discover -s tests -v",self.core_ci)

    def test_18_long_context_pipeline_runs_regression_suite(self):
        self.assertIn("tests.test_long_context",self.long_ci)
        self.assertIn("python -m py_compile",self.long_ci)

    def test_19_windows_executable_pipeline_has_clean_launch_restart_retest(self):
        self.assertIn("Build KRISHNA Windows App",self.windows_ci)
        self.assertIn("Clean EXE launch-restart retest",self.windows_ci)
        self.assertIn('Path("dist/KRISHNA.exe")',self.windows_ci)


if __name__=="__main__":
    unittest.main()
