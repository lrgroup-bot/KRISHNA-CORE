import unittest
from krishna_core.hawkeye_industrial_perception import (
    HawkeyeIndustrialOCRPolicy,HawkeyeEquipmentChangeVerifier,
    HawkeyeSensorPoseEvidence,HawkeyeReconstructionRouter,
)

class HawkeyeIndustrialPerceptionTests(unittest.TestCase):
    def test_low_quality_recovers_before_ocr(self):
        p=HawkeyeIndustrialOCRPolicy.plan(quality=.2,industrial=True)
        self.assertEqual(p["route"],"mobile_recovery")
    def test_industrial_text_uses_ppocr(self):
        p=HawkeyeIndustrialOCRPolicy.plan(quality=.9,industrial=True)
        self.assertEqual(p["route"],"pp_ocr_v6_tiny_or_small")
    def test_change_requires_viewpoint_verification(self):
        out=HawkeyeEquipmentChangeVerifier.compare(
            {"led":"green","confidence":.9},{"led":"red","confidence":.8},viewpoint_compatible=False)
        self.assertTrue(out["changed"]);self.assertTrue(out["verification_required"]);self.assertLess(out["confidence"],.8)
    def test_sensor_pose_does_not_claim_metric_without_scale(self):
        out=HawkeyeSensorPoseEvidence.normalize({"gyro":[1,2,3],"quaternion":[0,0,0,1]},depth={"source":"monocular","scale_known":False})
        self.assertTrue(out["fusion_ready"]);self.assertFalse(out["metric_claim_allowed"])
    def test_reconstruction_stays_external(self):
        out=HawkeyeReconstructionRouter.plan(live=True,imu=True)
        self.assertFalse(out["core_copy"]);self.assertEqual(out["boundary"],"external process/API")

if __name__=="__main__":unittest.main()
