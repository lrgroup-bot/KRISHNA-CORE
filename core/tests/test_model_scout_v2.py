import tempfile
import unittest
from pathlib import Path

from krishna_core.model_scout import ModelCandidate, ModelScout


class ModelScoutV2Tests(unittest.TestCase):
    def test_recommend_only_returns_benchmarked_accepted_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"scout.json")
            rejected=scout.evaluate(ModelCandidate("local/no-bench",quality=0.99))
            self.assertFalse(rejected["accepted"])
            accepted=scout.evaluate(ModelCandidate(
                "local/bench",task="coding",quality=0.9,latency_ms=250,
                ram_bytes=1024**3,vram_bytes=512*1024**2,benchmark_ref="bench-001"
            ))
            self.assertTrue(accepted["accepted"])
            rows=scout.recommend("coding",max_ram_bytes=2*1024**3)
            self.assertEqual([x["model_id"] for x in rows],["local/bench"])

    def test_cloud_label_never_grants_billing_authority(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"scout.json")
            scout.evaluate(ModelCandidate(
                "cloud/free-labelled",source="cloud",local_capable=False,
                cloud_zero_cost_verified=True,quality=1.0,benchmark_ref="bench-cloud"
            ))
            status=scout.status()
            self.assertFalse(status["cloud_billing_authority"])
            self.assertEqual(status["cloud_spend_limit_usd"],0.0)


if __name__=="__main__":
    unittest.main()
