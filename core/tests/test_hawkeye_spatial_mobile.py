import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

class HawkeyeSpatialMobileContractTests(unittest.TestCase):
    def test_mobile_imu_sensor_fusion_is_canonical_and_keyless(self):
        sensor=(ROOT/"mobile_v3"/"HawkeyeSensorFusion.java").read_text(encoding="utf-8")
        activity=(ROOT/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8")
        runtime=json.loads((ROOT/"mobile_v3"/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))
        self.assertIn("ANDROID_SENSOR_MANAGER",sensor)
        self.assertIn('"api_key_required",false',sensor)
        self.assertIn('"pose_authority",false',sensor)
        self.assertIn('"survey_grade",false',sensor)
        self.assertIn("hawkeyeSensorSnapshot",activity)
        self.assertIn("HawkeyeSensorFusion.java",runtime["canonical_files"])
        self.assertTrue(runtime["boundaries"]["local_imu_sensor_fusion"])
        self.assertFalse(runtime["boundaries"]["imu_is_slam_pose"])
        self.assertTrue(runtime["boundaries"]["depth_requires_real_device_evidence"])

    def test_capture_paths_include_spatial_handoff_without_fake_depth(self):
        observer=(ROOT/"mobile_v3"/"hawkeye-observer-ui.js").read_text(encoding="utf-8")
        index=(ROOT/"mobile_v3"/"index.html").read_text(encoding="utf-8")
        for text in (observer,index):
            self.assertIn("sensor_fusion",text)
            self.assertIn("spatial_handoff",text)
            self.assertIn("slam_pose_claimed:false",text)
            self.assertIn("depth_claimed:false",text)
            self.assertIn("survey_grade:false",text)

if __name__=="__main__":
    unittest.main()
