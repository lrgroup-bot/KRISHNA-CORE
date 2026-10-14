import tempfile,unittest
from krishna_core.hawkeye_active_vision import HawkeyeActiveVisionRuntime

class HawkeyeActiveVisionOwnerGateTests(unittest.TestCase):
    def _runtime(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return HawkeyeActiveVisionRuntime(self.tmp.name)

    def test_mobile_recovery_is_proposal_only(self):
        r=self._runtime()
        p=r.escalation_plan({"read":{"complete":False},"mobile_recovery_attempts":0})
        self.assertEqual(p["status"],"propose")
        self.assertTrue(p["owner_approval_required"])
        self.assertEqual(p["route"],"mobile-active-vision")

    def test_optional_model_escalation_is_proposal_only(self):
        r=self._runtime()
        p=r.escalation_plan({"read":{"complete":False,"text":""},"mobile_recovery_attempts":4},installed_engines=["pp_ocr_v6"])
        self.assertEqual(p["status"],"propose")
        self.assertTrue(p["owner_approval_required"])
        self.assertEqual(p["route"],"pp_ocr_v6")

    def test_completed_observation_needs_no_action(self):
        r=self._runtime()
        p=r.escalation_plan({"read":{"complete":True,"confidence":.9}})
        self.assertEqual(p["status"],"complete")
        self.assertEqual(p["route"],"none")

    def test_status_exposes_strict_policy(self):
        s=self._runtime().status()
        self.assertEqual(s["execution_policy"],"PROPOSE_ONLY_UNTIL_OWNER_APPROVAL")
        self.assertTrue(s["owner_approval_required"])
        self.assertNotIn("automatic_recovery",s)

if __name__=="__main__":unittest.main()
