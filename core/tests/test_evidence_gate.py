import unittest

from krishna_core.evidence_gate import (
    Decision, EvidenceReceipt, WorkState, classify_step, decide,
)


class EvidenceGateTests(unittest.TestCase):
    def test_execution_is_not_done(self):
        r = EvidenceReceipt("repair.api").execute(rollback_point="abc123")
        self.assertEqual(r.state, WorkState.EXECUTED)
        self.assertFalse(r.independently_verified)
        with self.assertRaises(ValueError):
            r.verify()

    def test_independent_evidence_unlocks_verified_then_observed(self):
        r = EvidenceReceipt("repair.ui").execute(rollback_point="abc123")
        r.add_evidence("mrityunjay", "self-report", True)
        with self.assertRaises(ValueError):
            r.verify()
        r.add_evidence("chandradev", "visual-check", True, independent=True)
        r.verify().observe({"healthy": True})
        self.assertEqual(r.state, WorkState.OBSERVED)

    def test_decision_abstains_and_preserves_owner_gate(self):
        self.assertEqual(decide(evidence_complete=False, authorized=True, verification_passed=True), Decision.GATHER_EVIDENCE)
        self.assertEqual(decide(evidence_complete=True, authorized=False, verification_passed=True), Decision.REJECT)
        self.assertEqual(decide(evidence_complete=True, authorized=True, verification_passed=True, consequential=True), Decision.ASK_OWNER)
        self.assertEqual(decide(evidence_complete=True, authorized=True, verification_passed=False), Decision.ROLLBACK)
        self.assertEqual(decide(evidence_complete=True, authorized=True, verification_passed=True), Decision.PROCEED)

    def test_boundary_classification(self):
        self.assertEqual(classify_step(deterministic=True), "EXACT")
        self.assertEqual(classify_step(), "JUDGMENT")
        self.assertEqual(classify_step(generative=True), "GENERATIVE")


if __name__ == "__main__":
    unittest.main()
