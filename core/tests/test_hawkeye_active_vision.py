import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.hawkeye_active_vision import HawkeyeActiveVisionRuntime


class HawkeyeActiveVisionRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.runtime=HawkeyeActiveVisionRuntime(Path(self.tmp.name)/"active")

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, **overrides):
        packet={
            "session_id":"s1",
            "target":{"key":"track:7","source":"AUTO","tracking_id":7,"label":"box","bbox":[.2,.2,.4,.4]},
            "read":{"state":"READING","complete":False,"confidence":.3,"samples":2,"details":{},"text":"","barcodes":[]},
            "quality":{"score":.6,"brightness":100,"detail":.4,"lowLight":False},
            "mobile_recovery_attempts":0,
            "pointing_available":True,
            "depth_available":False,
            "electronics_mode":False,
        }
        packet.update(overrides)
        return packet

    def test_mobile_recovery_always_precedes_heavy_models(self):
        out=self.runtime.escalation_plan(
            self.packet(),
            installed_engines=["pp_ocr_v6","mobile_sam","florence2","grounding_dino"],
        )
        self.assertEqual(out["route"],"mobile-active-vision")
        self.assertEqual(out["status"],"retry-mobile")

    def test_complete_read_never_escalates(self):
        packet=self.packet(read={
            "state":"COMPLETE","complete":True,"confidence":.9,"samples":2,
            "details":{"model":"X1"},"text":"Model X1","barcodes":["12345"],
        })
        out=self.runtime.escalation_plan(packet,installed_engines=["florence2"])
        self.assertEqual(out["status"],"complete")
        self.assertEqual(out["route"],"none")

    def test_ppocr_is_only_used_after_bounded_mobile_recovery(self):
        out=self.runtime.escalation_plan(
            self.packet(mobile_recovery_attempts=4),
            installed_engines=["pp_ocr_v6"],
        )
        self.assertEqual(out["route"],"pp_ocr_v6")

    def test_point_segmentation_follows_ocr_when_target_is_ambiguous(self):
        packet=self.packet(
            mobile_recovery_attempts=4,
            read={"state":"READING","complete":False,"confidence":.2,"samples":4,
                  "details":{},"text":"some readable label text","barcodes":[]},
        )
        out=self.runtime.escalation_plan(packet,installed_engines=["mobile_sam"])
        self.assertEqual(out["route"],"mobile_sam")

    def test_depth_and_pc_semantic_routes_are_capability_gated(self):
        depth=self.runtime.escalation_plan(
            self.packet(mobile_recovery_attempts=4,depth_available=True,
                        read={"state":"READING","complete":False,"confidence":.2,"samples":4,
                              "details":{},"text":"some readable label text","barcodes":[]}),
            installed_engines=[],
        )
        self.assertEqual(depth["route"],"depth_3d_pointing")
        pc=self.runtime.escalation_plan(
            self.packet(mobile_recovery_attempts=4,pointing_available=False,
                        read={"state":"READING","complete":False,"confidence":.2,"samples":4,
                              "details":{},"text":"some readable label text","barcodes":[]}),
            installed_engines=["florence2"],
        )
        self.assertEqual(pc["route"],"florence2")

    def test_fallback_uses_existing_hawkeye_and_never_requires_paid_service(self):
        out=self.runtime.escalation_plan(
            self.packet(mobile_recovery_attempts=4,pointing_available=False,
                        read={"state":"READING","complete":False,"confidence":.2,"samples":4,
                              "details":{},"text":"some readable label text","barcodes":[]}),
            installed_engines=[],
        )
        self.assertEqual(out["route"],"existing-hawkeye-vision")
        status=self.runtime.status()
        self.assertFalse(status["paid_dependency_required"])
        self.assertFalse(status["movement_instruction_default"])

    def test_record_is_distilled_json_not_raw_media(self):
        packet=self.packet(mobile_recovery_attempts=4)
        plan=self.runtime.escalation_plan(packet)
        row=self.runtime.record(packet,plan)
        self.assertIn("packet",row)
        saved=self.runtime.ledger.read_text(encoding="utf-8")
        self.assertIn("hawkeye.active-vision.packet.v1",saved)
        self.assertNotIn("data_b64",saved)


class HawkeyeActiveVisionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.mobile=cls.root/"mobile_v3"
        cls.kernel=(cls.mobile/"hawkeye-active-vision.js").read_text(encoding="utf-8")
        cls.ui=(cls.mobile/"hawkeye-observer-ui.js").read_text(encoding="utf-8")
        cls.vision=(cls.mobile/"HawkeyeMobileVision.java").read_text(encoding="utf-8")
        cls.activity=(cls.mobile/"MainActivity.java").read_text(encoding="utf-8")
        cls.index=(cls.mobile/"index.html").read_text(encoding="utf-8")
        cls.runtime=json.loads((cls.mobile/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))

    def test_pointed_target_has_priority_over_explicit_lock(self):
        self.assertLess(self.kernel.index("if(ray){"),self.kernel.index("if(lockedTrackingId"))

    def test_fast_cadences_are_subsecond(self):
        self.assertIn("setInterval(detect,260)",self.ui)
        self.assertIn("setInterval(handPerception,280)",self.ui)
        self.assertIn("setInterval(activeVisionTick,300)",self.ui)

    def test_target_only_read_bridge_is_real_and_potential_barcodes_are_enabled(self):
        self.assertIn("hawkeyeReadTarget",self.activity)
        self.assertIn("analyzeReadTarget",self.vision)
        self.assertIn("enableAllPotentialBarcodes",self.vision)
        self.assertIn("potential_barcode_count",self.vision)

    def test_unreadable_recovery_is_automatic(self):
        self.assertIn('"mode","automatic"',self.vision)
        self.assertNotIn("Move closer and hold steady",self.vision)
        self.assertNotIn("Move slightly back or recenter",self.vision)
        self.assertIn("applyActiveCameraPlan",self.ui)
        self.assertTrue(self.runtime["boundaries"]["automatic_target_crop_reading"])

    def test_green_read_complete_ui_is_hard_contract(self):
        self.assertIn("READ COMPLETE",self.ui)
        self.assertIn(".cameraLayer.av-complete .activeVisionFrame",self.index)
        self.assertIn("border:4px solid #43f59b",self.index)

    def test_canonical_runtime_declares_active_vision(self):
        boundaries=self.runtime["boundaries"]
        self.assertTrue(boundaries["hawkeye_active_vision_kernel"])
        self.assertTrue(boundaries["continuous_point_target_selection"])
        self.assertTrue(boundaries["pointed_target_priority"])
        self.assertTrue(boundaries["automatic_unreadable_recovery"])
        self.assertTrue(boundaries["full_green_read_complete_border"])
        self.assertFalse(boundaries["movement_instruction_default"])
        self.assertIn("hawkeye-active-vision.js",self.runtime["canonical_files"])
        self.assertIn("HawkeyeCameraProfiler.java",self.runtime["canonical_files"])
        self.assertTrue(boundaries["native_read_only_camera_profile"])


if __name__=="__main__":
    unittest.main()
