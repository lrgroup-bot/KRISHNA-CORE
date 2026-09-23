import tempfile
import time
import unittest
from pathlib import Path

from krishna_core.model_scout import ModelCandidate, ModelScout, ZeroCostPolicy

class ModelScoutTests(unittest.TestCase):
    def test_zero_cost_guard_blocks_paid_and_exhausted_cloud(self):
        p=ZeroCostPolicy()
        self.assertTrue(p.cloud_allowed("groq",confirmed_free=True,estimated_cost_usd=0))
        self.assertFalse(p.cloud_allowed("groq",confirmed_free=False,estimated_cost_usd=0))
        self.assertFalse(p.cloud_allowed("groq",confirmed_free=True,estimated_cost_usd=0.01))
        p.mark_exhausted("groq",time.time()+3600)
        self.assertFalse(p.cloud_allowed("groq",confirmed_free=True))
        p.mark_free_available("groq")
        self.assertTrue(p.cloud_allowed("groq",confirmed_free=True))

    def test_scout_rejects_duplicate_and_promotes_useful_local_model(self):
        with tempfile.TemporaryDirectory() as d:
            s=ModelScout(Path(d)/"models.json")
            good=s.evaluate(ModelCandidate("useful","huggingface","vision",quality=.9,latency_ms=500,ram_bytes=2*1024**3))
            self.assertTrue(good["accepted"])
            dup=s.evaluate(ModelCandidate("duplicate","huggingface","vision",quality=.99,duplicate_of="useful"))
            self.assertFalse(dup["accepted"])
            self.assertEqual(s.status()["active"],1)

if __name__=="__main__":
    unittest.main()
