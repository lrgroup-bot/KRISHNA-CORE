import tempfile
import unittest
from pathlib import Path

from krishna_core.durable_queue import DurableQueue
from krishna_core.memory import MemoryStore


class DeepInvariantTests(unittest.TestCase):
    def test_queue_idempotency_replays_same_work(self):
        with tempfile.TemporaryDirectory() as td:
            q=DurableQueue(Path(td)/"q.db")
            a=q.enqueue("observe",{"x":1},mission_id="m1",idempotency_key="same")
            b=q.enqueue("observe",{"x":1},mission_id="m1",idempotency_key="same")
            self.assertEqual(a["queue_id"],b["queue_id"])
            self.assertTrue(b["idempotent_replay"])
            self.assertEqual(len(q.list()),1)
            q.close()

    def test_queue_idempotency_survives_restart(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"q.db"
            q=DurableQueue(db);a=q.enqueue("observe",{"x":1},idempotency_key="restart");q.close()
            q=DurableQueue(db);b=q.enqueue("observe",{"x":1},idempotency_key="restart")
            self.assertEqual(a["queue_id"],b["queue_id"])
            self.assertTrue(b["idempotent_replay"])
            q.close()

    def test_queue_idempotency_rejects_different_work(self):
        with tempfile.TemporaryDirectory() as td:
            q=DurableQueue(Path(td)/"q.db")
            q.enqueue("observe",{"x":1},idempotency_key="conflict")
            with self.assertRaisesRegex(ValueError,"different work"):
                q.enqueue("observe",{"x":2},idempotency_key="conflict")
            q.close()

    def test_raw_verified_memory_write_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            m=MemoryStore(Path(td)/"m.db")
            with self.assertRaisesRegex(ValueError,"knowledge_law_gate"):
                m.learn("KRISHNA","t","claim",verified=True)
            self.assertEqual(m.learnings("KRISHNA",verified_only=True),[])
            m.close()

    def test_gated_verified_memory_write_is_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            m=MemoryStore(Path(td)/"m.db")
            r=m.learn("KRISHNA","t","claim",verified=True,
                      provenance={"knowledge_law_gate":{"allowed":True,"violations":[]}})
            self.assertEqual(r["status"],"verified")
            self.assertEqual(len(m.learnings("KRISHNA",verified_only=True)),1)
            m.close()


if __name__=="__main__":
    unittest.main()
