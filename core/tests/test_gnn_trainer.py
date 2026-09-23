import unittest

from krishna_core.gnn_trainer import LocalGNNTrainer


class FakeBackend:
    def __init__(self,available=True): self._available=available
    def available(self): return self._available


class FakeDataset:
    def __init__(self,count): self.rows=[{"x":i} for i in range(count)]
    def load(self): return list(self.rows)


class GNNTrainerTests(unittest.TestCase):
    def test_unconfigured_trainer_fails_honestly_without_notimplemented_stub(self):
        trainer=LocalGNNTrainer(FakeBackend(True),FakeDataset(60))
        out=trainer.train(min_examples=50)
        self.assertFalse(out["trained"])
        self.assertEqual(out["status"],"ADAPTER_REQUIRED")
        self.assertFalse(out["production_claim"])

    def test_explicit_local_trainer_returns_candidate_only(self):
        runtime=LocalGNNTrainer(FakeBackend(True),FakeDataset(60))
        out=runtime.train(
            min_examples=50,
            schema={"features":["x"],"target":"y"},
            trainer=lambda rows,schema:{"trained":True,"examples":len(rows),"schema":schema},
        )
        self.assertTrue(out["trained"])
        self.assertEqual(out["status"],"TRAINED_CANDIDATE")
        self.assertTrue(out["verification_required"])
        self.assertFalse(out["production_claim"])

    def test_readiness_blocks_missing_backend_or_data(self):
        self.assertFalse(LocalGNNTrainer(FakeBackend(False),FakeDataset(60)).readiness()["ready"])
        self.assertFalse(LocalGNNTrainer(FakeBackend(True),FakeDataset(5)).readiness(50)["ready"])


if __name__=="__main__":
    unittest.main()
