import tempfile
import unittest
from pathlib import Path

from krishna_core.hawkeye_diagnostic import HawkeyeDiagnosticRuntime
from krishna_core.hawkeye_reference import HawkeyeReferenceRegistry


class HawkeyeDiagnosticRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = HawkeyeDiagnosticRuntime(Path(self.tmp.name) / "diagnostic")

    def tearDown(self):
        self.tmp.cleanup()

    def test_activation(self):
        self.assertTrue(self.runtime.should_activate("show circuit signal flow on this motherboard"))
        self.assertTrue(self.runtime.should_activate("diagnose this truck CAN fault"))
        self.assertTrue(self.runtime.should_activate("check this bearing sound fault"))
        self.assertFalse(self.runtime.should_activate("inspect quarry road geometry"))
        self.assertFalse(self.runtime.should_activate("can you inspect the dashboard layout"))

    def test_camera_only_flow_stays_inferred(self):
        raw = '{"device_type":"PCB","analysis":"Visible power section","confidence":0.82,"evidence_state":"OBSERVED","components":[{"id":"j1","label":"DC input","kind":"connector","bbox":[0.1,0.2,0.2,0.2],"confidence":0.9},{"id":"u1","label":"Regulator","kind":"IC","bbox":[0.5,0.4,0.2,0.2],"confidence":0.8}],"flows":[{"from":"j1","to":"u1","label":"power","evidence_state":"MEASURED","confidence":0.7}],"test_points":[],"warnings":[],"needs_reference":false,"reference_type":"none"}'
        out = self.runtime.record_model_result("s1", raw, goal="show circuit flow")
        self.assertEqual(out["diagram_mode"], "visual-inference")
        self.assertTrue(out["needs_reference"])
        self.assertEqual(out["flows"][0]["evidence_state"], "INFERRED")
        self.assertEqual(out["overlay"]["schema"], "hawkeye.diagnostic-overlay.v1")

    def test_reference_aligned_mode(self):
        raw = '{"device_type":"PCB","analysis":"Boardview aligned","confidence":0.9,"evidence_state":"OBSERVED","components":[],"flows":[],"test_points":[],"warnings":[],"needs_reference":false,"reference_type":"boardview"}'
        out = self.runtime.record_model_result("s2", raw, sensor_context={"boardview_verified": True})
        self.assertEqual(out["diagram_mode"], "reference-aligned")
        self.assertFalse(out["needs_reference"])

    def test_bbox_and_invalid_flow(self):
        raw = '{"device_type":"PCB","analysis":"x","confidence":1.2,"evidence_state":"OBSERVED","components":[{"id":"c1","label":"A","kind":"IC","bbox":[0.9,0.9,0.8,0.8],"confidence":2}],"flows":[{"from":"c1","to":"missing","label":"signal","confidence":1}],"test_points":[],"warnings":[]}'
        out = self.runtime.record_model_result("s3", raw)
        self.assertEqual(out["components"][0]["bbox"], [0.9, 0.9, 0.1, 0.1])
        self.assertEqual(out["components"][0]["confidence"], 1.0)
        self.assertEqual(out["flows"], [])

    def test_verified_reference_overrides_visual_inference(self):
        refs = HawkeyeReferenceRegistry(Path(self.tmp.name) / "refs")
        refs.register("board1", "boardview", {"components": [
            {"id": "A", "x": 0.0, "y": 0.0},
            {"id": "B", "x": 1.0, "y": 0.0},
            {"id": "C", "x": 0.0, "y": 1.0},
        ], "nets": [{"from": "A", "to": "B", "label": "VCC"}]}, verified=True)
        self.runtime.bind_reference_registry(refs)
        raw = '{"device_type":"PCB","analysis":"camera inference","confidence":0.6,"evidence_state":"OBSERVED","components":[],"flows":[],"test_points":[],"warnings":[],"needs_reference":true,"reference_type":"boardview"}'
        out = self.runtime.record_model_result("ref1", raw, goal="diagnose PCB", sensor_context={
            "reference_id": "board1",
            "reference_anchors": [
                {"reference": [0, 0], "image": [0.1, 0.2]},
                {"reference": [1, 0], "image": [0.9, 0.2]},
                {"reference": [0, 1], "image": [0.1, 0.8]},
            ],
        })
        self.assertEqual(out["diagram_mode"], "reference-aligned")
        self.assertFalse(out["needs_reference"])
        self.assertEqual(out["reference_id"], "board1")
        self.assertEqual(out["flows"][0]["label"], "VCC")
        self.assertLess(out["registration_rms"], 1e-8)

    def test_specialist_worker_routing(self):
        self.assertEqual(self.runtime._worker_specialty("bearing noise diagnosis", "audio"), "AcousticDiagnosticWorker")
        self.assertEqual(self.runtime._worker_specialty("truck CAN bus ECU fault", "image"), "VehicleDiagnosticWorker")
        self.assertEqual(self.runtime._worker_specialty("PCB voltage regulator fault", "image"), "ElectronicsDiagnosticWorker")
        self.assertIsNone(self.runtime._worker_specialty("inspect quarry slope", "image"))
        self.assertEqual(self.runtime.maybe_dispatch_worker("s-no-worker", {"confidence": 0.2}, goal="PCB fault"), {"status": "not_needed"})

    def test_high_voltage_warning_and_persistence(self):
        raw = '{"device_type":"EV inverter","analysis":"Possible 800V DC bus","confidence":0.4,"evidence_state":"INFERRED","components":[],"flows":[],"test_points":[],"warnings":[]}'
        out = self.runtime.record_model_result("s4", raw, goal="inspect HV battery inverter")
        self.assertTrue(any("hazardous voltage" in x.lower() for x in out["warnings"]))
        self.assertFalse(out["safety"]["energized_high_voltage_probe"])
        self.assertEqual(self.runtime.get_session("s4")["specialist"], "HAWKEYE DIAGNOSTIC")


if __name__ == "__main__":
    unittest.main()
