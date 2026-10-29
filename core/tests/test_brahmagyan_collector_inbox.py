"""SURYADEV fleet evidence remains unverified in BRAHMAGYAN until Rishi review."""
import tempfile
import unittest
from pathlib import Path

from krishna_core.brahmagyan import BrahmagyanRuntime


class Memory:
    def audit(self,*a,**kw): pass

class CollectorInboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.brain=BrahmagyanRuntime(self.root,object(),Memory())
        self.receipt={
            "task_id":"fleet-"+("1"*28),
            "device_id":"suryadev-01",
            "rishi_id":"kanada",
            "source_url":"https://docs.python.org/3/library/asyncio.html",
            "evidence_sha256":"a"*64,"received_at":1000.0,
            "kind":"website","mission_id":"python-async","topic":"asyncio"
        }
    def tearDown(self): self.temp.cleanup()

    def test_candidate_is_durable_idempotent_and_never_mastered(self):
        first=self.brain.intake_suryadev_collection(self.receipt)
        self.assertTrue(first["recorded"])
        self.assertFalse(first["idempotent"])
        self.assertEqual(first["candidate"]["knowledge_status"],"collected_unverified")
        self.assertFalse(first["candidate"]["comprehension_verified"])
        again=self.brain.intake_suryadev_collection(dict(self.receipt))
        self.assertTrue(again["idempotent"])
        persisted=BrahmagyanRuntime(self.root,object(),Memory())
        self.assertEqual(persisted.collector_candidates()["total"],1)
        self.assertEqual(persisted.status()["collector_candidates"],1)
        self.assertEqual(persisted.status()["claims"],0)

    def test_conflicting_source_same_task_fails_closed(self):
        self.brain.intake_suryadev_collection(self.receipt)
        with self.assertRaisesRegex(RuntimeError,"conflicting"):
            self.brain.intake_suryadev_collection({**self.receipt,"evidence_sha256":"b"*64})
        self.assertEqual(self.brain.collector_candidates()["total"],1)

    def test_invalid_or_unregistered_attribution_rejected(self):
        for updates in [
            {"device_id":"unknown"},
            {"rishi_id":"imaginary-scholar"},
            {"evidence_sha256":"bad"},
            {"source_url":"http://127.0.0.1/internal"},
        ]:
            with self.subTest(updates=updates):
                with self.assertRaises((ValueError, KeyError)):
                    self.brain.intake_suryadev_collection({**self.receipt,**updates})
        self.assertEqual(self.brain.collector_candidates()["total"],0)


if __name__=="__main__":
    unittest.main()
