"""SURYDEV approved book collector must never substitute indexing for learned knowledge."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from suryadev_book_continuity import approve_book, BookEvidenceCollector
from suryadev_book_reader import BookLedger

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.book=self.root/"owned.txt"
        self.book.write_text("First evidence line\nSecond evidence line\nThird evidence line",
                             encoding="utf-8")
        self.approved=approve_book(self.root,self.book)
        self.plan=self.root/"book-plan.json"
    def tearDown(self):
        self.tmp.cleanup()

    def test_collect_without_ollama_or_invented_understanding(self):
        collector=BookEvidenceCollector(self.root,self.plan)
        with patch("suryadev.summarize",side_effect=AssertionError("ollama must not run")):
            receipt=collector.tick(available=True)
        self.assertEqual(receipt["state"],"indexed_evidence_only")
        self.assertEqual(receipt["model_calls"],0)
        self.assertEqual(receipt["lines_indexed"],3)
        self.assertFalse(receipt["knowledge_verified"])
        self.assertFalse(receipt["brahmagyan_acknowledged"])
        ledger=BookLedger(self.root)
        try:
            status=ledger.status(receipt["book_id"])
            self.assertEqual(status["sessions"],{})
        finally:
            ledger.close()
        self.assertIsNone(collector.tick(available=True))
        resumed=BookEvidenceCollector(self.root,self.plan)
        self.assertTrue(resumed.tick(available=True)["already_indexed"])

    def test_modified_book_refuses_collection_without_overwriting_index(self):
        collector=BookEvidenceCollector(self.root,self.plan)
        self.book.write_text("changed bytes",encoding="utf-8")
        receipt=collector.tick(available=True)
        self.assertEqual(receipt["state"],"collection_failed")
        self.assertIn("SHA-256 changed",receipt["error"])
        self.assertEqual(receipt["model_calls"],0)

    def test_no_capacity_means_no_collection(self):
        collector=BookEvidenceCollector(self.root,self.plan)
        self.assertIsNone(collector.tick(available=False))
        self.assertIsNotNone(collector.tick(available=True))

if __name__=="__main__":
    unittest.main()
