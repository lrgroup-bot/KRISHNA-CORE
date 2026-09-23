import tempfile
import unittest
from pathlib import Path

from krishna_core.model_scout import ModelCandidate, ModelScout


class ModelScoutTests(unittest.TestCase):
    def test_candidate_requires_benchmark_before_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"models.json")
            row=scout.evaluate(ModelCandidate(
                "local/test",quality=0.9,latency_ms=100,ram_bytes=1024,benchmark_ref=""
            ))
            self.assertFalse(row["accepted"])
            self.assertEqual(row["decision"],"REJECT_OR_HOLD")

    def test_good_local_benchmarked_candidate_can_be_promoted(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"models.json")
            row=scout.evaluate(ModelCandidate(
                "local/test",quality=0.9,latency_ms=100,ram_bytes=1024,
                benchmark_ref="bench-001",local_capable=True
            ))
            self.assertTrue(row["accepted"])
            self.assertEqual(len(scout.active()),1)

    def test_duplicate_candidate_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"models.json")
            row=scout.evaluate(ModelCandidate(
                "local/duplicate",quality=1.0,benchmark_ref="bench-002",duplicate_of="local/base"
            ))
            self.assertFalse(row["accepted"])
            self.assertLess(row["score"],0)

    def test_cloud_free_label_never_changes_zero_cost_policy(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"models.json")
            row=scout.evaluate(ModelCandidate(
                "cloud/candidate",source="cloud",local_capable=False,
                cloud_zero_cost_verified=True,quality=1.0,benchmark_ref="bench-003"
            ))
            self.assertFalse(row["accepted"])
            self.assertIn("billing verification",row["cloud_policy"])


if __name__=="__main__":
    unittest.main()
