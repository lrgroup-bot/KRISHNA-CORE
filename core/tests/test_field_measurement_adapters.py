import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.field_measurement_adapters import (
    FieldMeasurementAdapters,
    GnssRtkAdapter,
    DepthMeasurementAdapter,
)


class FieldMeasurementAdapterTests(unittest.TestCase):
    def test_gnss_rtk_normalizes_real_supplied_fix_without_fabricating_accuracy(self):
        out=GnssRtkAdapter().normalize({
            "lat":20.2961,"lon":85.8245,"fix_type":"rtk_fixed","device_id":"receiver-1"
        })
        self.assertEqual(out["evidence_state"],"MEASURED")
        self.assertTrue(out["rtk_fixed"])
        self.assertIsNone(out["accuracy_m"])
        self.assertTrue(any("accuracy" in x for x in out["limitations"]))
        self.assertTrue(out["fingerprint"])

    def test_gnss_rejects_impossible_coordinate(self):
        with self.assertRaises(ValueError):
            GnssRtkAdapter().normalize({"lat":120,"lon":85})

    def test_depth_keeps_missing_calibration_visible(self):
        out=DepthMeasurementAdapter().normalize(
            [{"depth_m":1.0},{"depth_m":2.0},{"depth_m":3.0}],
            device_id="depth-1",
        )
        self.assertEqual(out["sample_count"],3)
        self.assertEqual(out["summary"]["median_m"],2.0)
        self.assertFalse(out["survey_grade"])
        self.assertTrue(any("calibration" in x for x in out["limitations"]))

    def test_no_depth_samples_remain_unknown(self):
        out=DepthMeasurementAdapter().normalize([])
        self.assertEqual(out["evidence_state"],"UNKNOWN")
        self.assertIsNone(out["summary"])

    def test_non_finite_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            GnssRtkAdapter().normalize({"lat":20.2961,"lon":85.8245,"captured_at":float("nan")})
        with self.assertRaises(ValueError):
            DepthMeasurementAdapter().normalize([{"depth_m":1.0,"confidence":float("inf")}])
        with self.assertRaises(ValueError):
            DepthMeasurementAdapter().normalize([{"depth_m":1.0}],captured_at=float("nan"))

    def test_photogrammetry_never_reports_configured_without_real_executable(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ,{"KRISHNA_PHOTOGRAMMETRY_CMD":str(Path(d)/"missing.exe")},clear=False):
                adapters=FieldMeasurementAdapters(Path(d)/"state")
                self.assertFalse(adapters.status()["photogrammetry"]["configured"])
                with self.assertRaises(RuntimeError):
                    adapters.photogrammetry.run(d,str(Path(d)/"out"))


if __name__=="__main__":
    unittest.main()
