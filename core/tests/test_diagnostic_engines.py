from __future__ import annotations
import unittest

from krishna_core.diagnostic_engines import DiagnosticEngineRegistry

class DiagnosticEngineTests(unittest.TestCase):
    def test_electronics_uses_only_supplied_measurements_and_ranges(self):
        r=DiagnosticEngineRegistry()
        out=r.evaluate({
            "measurements":[{"name":"TP5","value":4.1,"unit":"V"}],
            "expected_ranges":{"TP5":{"min":4.8,"max":5.2,"unit":"V"}},
        },goal="diagnose pcb voltage",modality="image")
        self.assertEqual(out["selected"],"electronics")
        finding=out["result"]["findings"][0]
        self.assertEqual(finding["evidence_state"],"MEASURED")
        self.assertEqual(finding["status"],"below_expected_range")

    def test_vehicle_is_read_only_and_preserves_dtc_as_observation(self):
        r=DiagnosticEngineRegistry()
        out=r.evaluate({"dtcs":["P0301"],"vehicle_telemetry":{"rpm":850}},goal="vehicle obd diagnosis")
        self.assertEqual(out["selected"],"vehicle")
        self.assertFalse(out["result"]["provider_status"]["auto_transmit"])
        self.assertFalse(out["result"]["provider_status"]["ecu_programming"])
        self.assertEqual(out["result"]["observations"][0]["code"],"P0301")

    def test_acoustic_requires_baseline_for_measured_change(self):
        r=DiagnosticEngineRegistry()
        out=r.evaluate({
            "acoustic_baseline":{"rms":0.2,"peak_1_hz":120.0},
            "acoustic_features":{"rms":0.5,"peak_1_hz":125.0},
        },goal="bearing vibration",modality="audio")
        self.assertEqual(out["selected"],"acoustic")
        self.assertEqual(out["result"]["evidence_state"],"MEASURED")
        self.assertTrue(out["result"]["feature_changes"])

if __name__=="__main__":
    unittest.main()
