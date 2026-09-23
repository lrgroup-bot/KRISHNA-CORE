import tempfile
import unittest
from pathlib import Path

from krishna_core.model_scout import ModelCandidate, ModelScout


class ModelScoutV2Tests(unittest.TestCase):
    def test_scout_promotes_useful_local_candidate_and_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"models.json")
            good=scout.evaluate(ModelCandidate(
                "local-vision","local","vision","Apache-2.0",
                local_capable=True,quality=.91,latency_ms=450,
                ram_bytes=2*1024**3,vram_bytes=1024**3,
            ))
            self.assertTrue(good["accepted"])
            dup=scout.evaluate(ModelCandidate(
                "local-vision-copy","local","vision","Apache-2.0",
                local_capable=True,quality=.99,duplicate_of="local-vision",
            ))
            self.assertFalse(dup["accepted"])
            rec=scout.recommend("vision",max_ram_bytes=4*1024**3,max_vram_bytes=2*1024**3)
            self.assertEqual(rec[0]["model_id"],"local-vision")

    def test_scout_never_has_install_or_cloud_billing_authority(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"models.json")
            status=scout.status()
            self.assertFalse(status["cloud_billing_authority"])
            self.assertEqual(status["download_policy"],"no automatic downloads")


if __name__=="__main__":
    unittest.main()
