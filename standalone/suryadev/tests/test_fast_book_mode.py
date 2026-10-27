"""Fast book mode: fewer LOCAL model calls, unchanged durable line coverage.

No Ollama/network required. Tests prove restart resumes the same journal
instead of restarting, skipping pages, or inventing comprehension.
"""
import tempfile
import unittest
from pathlib import Path

from suryadev_book_reader import BookLedger
from suryadev_book_continuity import approve_book
from suryadev_parallel_books import ParallelBookReader


class FastBookTests(unittest.TestCase):
    def _source(self, root, n, *, width=0):
        source=root/"approved-book.txt"
        source.write_text("\n".join(
            "chapter {:03d} ".format(i) + ("meaning and source evidence " * 12
            if width else "a short verified source line") + " end {:03d}".format(i)
            for i in range(1,n+1)),encoding="utf-8")
        return source

    def test_legacy_20_then_fast_40_resume_exactly_same_model_session(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=self._source(root,100)
            model_prompts=[]
            def observe(prompt, model):
                model_prompts.append(prompt)
                return "Candidate notes only; not verified comprehension."
            ledger=BookLedger(root)
            try:
                bid=ledger.import_book(source)["book_id"]
                legacy=ledger.read(bid,model="local-test",lines_per_step=20,
                                   max_steps=1,observe=observe)
                self.assertEqual(legacy["lines_processed_total"],20)
                first_fast=ledger.read(bid,model="local-test",lines_per_step=20,
                    max_steps=1,observe=observe,fast_mode=True)
                self.assertEqual(first_fast["lines_processed_total"],60)
                self.assertIn("[21|",model_prompts[1])
                self.assertIn("[60|",model_prompts[1])
                self.assertNotIn("[61|",model_prompts[1])
            finally:
                ledger.close()
            # Same book/model journal after process restart, not a new
            # hallucinated progress counter or a second book session.
            reloaded=BookLedger(root)
            try:
                finished=reloaded.read(bid,model="local-test",
                    lines_per_step=20,max_steps=1,observe=observe,fast_mode=True)
                self.assertEqual(finished["lines_processed_total"],100)
                self.assertTrue(finished["reached_end"])
                journal=list(reloaded.db.execute(
                    "SELECT start_ordinal,end_ordinal FROM book_journal "
                    "WHERE book_id=? AND mode=? ORDER BY start_ordinal",
                    (bid,"ollama:local-test")))
                self.assertEqual(journal,[(1,20),(21,60),(61,100)])
                status=reloaded.status(bid)
                reading=status["sessions"]["ollama:local-test"]
                self.assertEqual(reading["model_steps_completed"],3)
                self.assertEqual(reading["recent_checkpoint_count"],3)
                self.assertEqual(reading["recent_checkpoint_lines"],100)
                self.assertIsNotNone(reading["last_committed_at"])
                self.assertGreaterEqual(reading["recent_model_seconds"],0)
                # Timing is model-call-only; neither processing nor timing
                # implies independently verified comprehension.
                self.assertFalse(status["comprehension_verified"])
            finally:
                reloaded.close()

    def test_overlarge_batch_shrinks_without_truncating_a_source_line(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=self._source(root,82,width=1)
            captured=[]
            def observe(prompt, model):
                captured.append(prompt)
                self.assertLessEqual(len(prompt),12000)
                return "Unverified candidate observation"
            ledger=BookLedger(root)
            try:
                bid=ledger.import_book(source)["book_id"]
                receipt=ledger.read(bid,model="local-test",lines_per_step=20,
                    max_steps=100,observe=observe,fast_mode=True)
                self.assertTrue(receipt["reached_end"])
                self.assertGreaterEqual(len(captured),3)
                self.assertEqual(receipt["lines_processed_total"],82)
                rows=list(ledger.db.execute(
                    "SELECT start_ordinal,end_ordinal FROM book_journal "
                    "WHERE book_id=? AND mode=? ORDER BY start_ordinal",
                    (bid,"ollama:local-test")))
                self.assertEqual(rows[0][0],1)
                self.assertEqual(rows[-1][1],82)
                self.assertTrue(any(end-start+1<40 for start,end in rows))
                self.assertEqual(sum(end-start+1 for start,end in rows),82)
                self.assertTrue(all(rows[i][1]+1==rows[i+1][0]
                                    for i in range(len(rows)-1)))
                # Every original source ordinal is represented; never drop a
                # physical line merely to fit Ollama's context.
                self.assertIn("end 082",captured[-1])
            finally:
                ledger.close()

    def test_one_safe_book_slot_stays_single_local_model_in_fast_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            book=self._source(root,85)
            approve_book(root,book,lines_per_step=20)
            observed=[]
            def observe(prompt,model):
                observed.append(prompt)
                return "Unverified notes"
            pool=ParallelBookReader(root,root/"book-plan.json",
                model="local-test",observe=observe,fast_mode=True)
            try:
                self.assertEqual(pool.min_gap_seconds,1.0)
                admitted=pool.tick(capacity={"safe":True,"max_total":2,
                    "reserved_book_slots":1},source_active=0)
                self.assertEqual(admitted["active"],1)
                self.assertTrue(admitted["fast_mode"])
                self.assertEqual(admitted["batch_target_lines"],40)
                for f in tuple(pool.futures):
                    f.result(timeout=5)
                result=pool.tick(capacity={"safe":False,"max_total":0,
                    "reserved_book_slots":0})
                self.assertEqual(result["active"],0)
                self.assertTrue(result["finished"])
                ledger=BookLedger(root)
                try:
                    books=ledger.status()["books"]
                    self.assertEqual(books[0]["sessions"]["ollama:local-test"]["lines_processed"],40)
                finally:
                    ledger.close()
            finally:
                pool.close()


if __name__ == "__main__":
    unittest.main()
