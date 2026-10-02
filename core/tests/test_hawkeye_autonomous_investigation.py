import tempfile,unittest
from pathlib import Path
from krishna_core.hawkeye_autonomous_investigation import HawkeyeOwnerDiscussion,HawkeyeActiveInvestigator,HawkeyeSpatialEpisodeMemory,HawkeyeMultiSensorFusion

class HawkeyeAutonomousInvestigationTests(unittest.TestCase):
    def test_owner_gated_capability_waits(self):
        with tempfile.TemporaryDirectory() as td:
            d=HawkeyeOwnerDiscussion(td);p=d.propose("Add depth sensor","Better metric geometry",["Use phone depth","Skip"],category="new_sensor")
            self.assertTrue(p["owner_approval_required"]);self.assertEqual(p["status"],"PENDING")
            self.assertEqual(d.decide(p["proposal_id"],True)["status"],"APPROVED")
    def test_safe_recovery_and_physical_request_separated(self):
        p=HawkeyeActiveInvestigator.recommend({"quality":.2,"occluded":True})
        self.assertEqual(p["automatic"][0]["action"],"improve_image")
        self.assertEqual(p["discussion"][0]["action"],"new_viewpoint")
    def test_episode_excludes_identity_kind(self):
        with tempfile.TemporaryDirectory() as td:
            m=HawkeyeSpatialEpisodeMemory(td);e=m.record("workshop",objects=[{"kind":"machine","label":"motor"},{"kind":"face_identity","label":"x"}])
            self.assertEqual(len(e["objects"]),1);self.assertEqual(e["objects"][0]["kind"],"machine")
    def test_fusion_does_not_claim_measurement(self):
        x=HawkeyeMultiSensorFusion.fuse([{"source":"camera","confidence":.8,"quality":.9},{"source":"depth","confidence":.9,"quality":.8}])
        self.assertGreater(x["confidence"],.7);self.assertFalse(x["measured_claim"])

if __name__=="__main__":unittest.main()
