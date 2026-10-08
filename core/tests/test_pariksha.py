import unittest
from krishna_core.pariksha import *

class ParikshaTests(unittest.TestCase):
    def test_perfect_capability_is_100_not_fake_iq(self):
        r=capability_report({k:1 for k in ABILITIES})
        self.assertEqual(r["kcci"],100.0);self.assertIsNone(r["human_iq_equivalent"])
    def test_missing_abilities_cannot_score_perfect(self):
        self.assertLess(capability_report({"reasoning":1})["kcci"],100)
    def test_mastery_raises_difficulty(self):
        self.assertGreater(next_difficulty(.5,1),.5)
    def test_failure_lowers_difficulty(self):
        self.assertLess(next_difficulty(.5,.2),.5)
    def test_seen_exam_item_is_blocked(self):
        h=item_fingerprint("secret item")
        self.assertFalse(contamination_gate(prompt_hash=h,previous_exam_hashes=[h])["allowed"])
    def test_overconfidence_is_fingerprinted(self):
        self.assertTrue(error_fingerprint(ability="reasoning",failure_type="logic",confidence=.95,correct=False)["overconfident"])
    def test_cognitive_immune_system_fails_weak_claim(self):
        r=immune_review("x",evidence_families=1,contradictions=1,stale=True,reality_checked=False)
        self.assertFalse(r["passed"]);self.assertGreaterEqual(len(r["attacks"]),4)
    def test_profiles_are_data_isolated(self):
        self.assertNotEqual(PROFILES["KRISHNA"]["isolation"],PROFILES["LR_GROUP"]["isolation"])
        self.assertNotEqual(PROFILES["KRISHNA"]["examiner"],PROFILES["LR_GROUP"]["examiner"])

if __name__=="__main__":unittest.main()
