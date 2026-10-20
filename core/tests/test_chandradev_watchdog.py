import unittest
from krishna_core.chandradev_watchdog import *
class ChandradevWatchdogTests(unittest.TestCase):
 def test_suryadev_unresolved_physical_problem_escalates(self):
  self.assertTrue(should_escalate(suryadev_resolved=False,physical_visibility_needed=True))
 def test_error_fix_requires_visual_and_deterministic_retest(self):
  self.assertEqual(visual_repair_verdict(before_issues=["blank screen"],after_issues=[],deterministic_tests_passed=True)["state"],"PASSED")
  self.assertEqual(visual_repair_verdict(before_issues=["blank"],after_issues=["still blank"],deterministic_tests_passed=True)["state"],"RETEST_REQUIRED")
 def test_bad_camera_cannot_claim_observation(self):
  h=camera_health(frame_age_seconds=1,blur_score=.1,expected_view=False)
  self.assertFalse(h["claim_observation"])
 def test_raw_media_deleted_only_after_verified_distillation(self):
  self.assertFalse(media_disposition(distilled=True,distillation_verified=False)["delete_raw"])
  self.assertTrue(media_disposition(distilled=True,distillation_verified=True)["delete_raw"])
 def test_incident_hold_prevents_deletion(self):
  self.assertFalse(media_disposition(distilled=True,distillation_verified=True,incident_hold=True)["delete_raw"])
 def test_evidence_window_is_bounded(self):
  w=evidence_window(event_at=1000,pre_seconds=999,post_seconds=999)
  self.assertEqual(w["pre_seconds"],120);self.assertEqual(w["post_seconds"],300)
 def test_watchdog_is_privacy_bounded(self):
  self.assertFalse(WATCHDOG_POLICY["raw_media_to_gyan"])
  self.assertEqual(WATCHDOG_POLICY["owner_private_space_default"],"never_upload")
if __name__=="__main__":unittest.main()
