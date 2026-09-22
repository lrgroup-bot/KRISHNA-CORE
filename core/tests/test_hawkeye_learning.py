import tempfile
import unittest
from pathlib import Path

from krishna_core.hawkeye_learning import HawkeyeLearningRuntime


class HawkeyeLearningRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = HawkeyeLearningRuntime(Path(self.tmp.name) / "hawkeye")

    def tearDown(self):
        self.tmp.cleanup()

    def test_daily_missions_cover_five_specialists(self):
        missions = self.runtime.daily_missions()
        self.assertEqual({m["specialist"] for m in missions}, set(self.runtime.SPECIALISTS))
        self.assertTrue(all("do not modify production code" in " ".join(m["rules"]) for m in missions))

    def test_finding_requires_provenance(self):
        with self.assertRaises(ValueError):
            self.runtime.record_finding(
                specialist="perception", title="x", claim="y", source_url=""
            )

    def test_candidate_is_sandbox_only_until_verified(self):
        finding = self.runtime.record_finding(
            specialist="perception", title="Detector benchmark", claim="Candidate improves recall",
            source_url="https://example.org/paper", confidence=0.7
        )
        candidate = self.runtime.propose_candidate(
            specialist="perception", finding_ids=[finding["finding_id"]],
            change_summary="test detector adapter", benchmark_plan=["offline benchmark"],
            rollback_plan="restore previous adapter version",
        )
        self.assertFalse(candidate["production_modified"])
        evaluated = self.runtime.evaluate_candidate(
            candidate["candidate_id"], baseline_score=0.70, candidate_score=0.78,
            security_passed=True, license_passed=True,
        )
        self.assertTrue(evaluated["evaluation"]["eligible_for_promotion_review"])
        self.assertFalse(evaluated["production_modified"])


if __name__ == "__main__":
    unittest.main()
