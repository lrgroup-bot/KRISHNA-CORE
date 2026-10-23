"""Source Coverage, Garudanetra and hardware book telemetry remain factual."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import time
import unittest

from suryadev_book_reader import BookLedger
from suryadev_book_dashboard import book_learning_snapshot
from suryadev_liveops import atomic_json


class UnifiedBookSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_root_does_not_create_ledger(self):
        snapshot = book_learning_snapshot(self.root)
        self.assertEqual(snapshot["indexed"],0)
        self.assertEqual(snapshot["approved"],0)
        self.assertEqual(snapshot["activity"]["state"],"not_started")
        self.assertFalse((self.root/"book-learning.sqlite3").exists())

    def test_laptop_learning_text_visuals_and_acks_counted_separately(self):
        text = self.root / "tech-book.txt"
        text.write_text("first\nsecond\nthird",encoding="utf-8")
        ledger=BookLedger(self.root)
        imported=ledger.import_book(text)
        bid=imported["book_id"]
        first=book_learning_snapshot(self.root)
        self.assertEqual(first["indexed"],1)
        self.assertEqual(first["approved"],0)
        self.assertEqual(first["lines_total"],3)
        self.assertEqual(first["lines_processed"],0)
        self.assertEqual(first["completed"],0)
        with ledger.db:
            ledger.db.execute(
                "CREATE TABLE IF NOT EXISTS book_visuals(book_id TEXT, ordinal INTEGER)")
            ledger.db.execute(
                "INSERT INTO book_visuals VALUES(?,?)",(bid,1))
            ledger.db.execute(
                "CREATE TABLE IF NOT EXISTS book_delivery(book_id TEXT)")
            ledger.db.execute(
                "INSERT INTO book_delivery VALUES(?)",(bid,))
        ledger.read(bid,model="local",max_steps=1,observe=lambda p,m:"read one")
        # Partially processed book is not text-complete even if it has visuals
        # or a Core candidate receipt.
        state=book_learning_snapshot(self.root)
        self.assertEqual(state["reading"],1)
        self.assertEqual(state["completed"],0)
        self.assertEqual(state["lines_processed"],1)
        self.assertEqual(state["visual_items_examined"],1)
        self.assertEqual(state["brahmagyan_candidate_receipts"],1)
        self.assertFalse(state["rishi_verified"])
        ledger.read(bid,model="local",observe=lambda p,m:"read line")
        done=book_learning_snapshot(self.root)
        self.assertEqual(done["completed"],1)
        self.assertEqual(done["lines_processed"],3)
        # A second model may read the same book independently. Live
        # averages and processed-line counts must come from ONE same session.
        with ledger.db:
            ledger.db.execute(
                "UPDATE book_journal SET elapsed_seconds=42 WHERE mode='ollama:local'")
        ledger.read(bid,model="second-local",max_steps=1,
                    observe=lambda p,m:"second model one line")
        with ledger.db:
            ledger.db.execute(
                "UPDATE book_journal SET elapsed_seconds=11 WHERE mode='ollama:second-local'")
        second=book_learning_snapshot(self.root)
        self.assertEqual(second["lines_processed"],1)
        self.assertEqual(second["model_seconds"],11)
        ledger.close()

    def test_in_progress_and_stale_activity_are_different(self):
        now=time.time()
        atomic_json(self.root,"book-continuity-runtime.json",{
            "state":"book_reading_in_progress","book_id":"book-123",
            "title":"Technical book","model":"local","updated_at":now})
        active=book_learning_snapshot(self.root,now=now+30)
        self.assertTrue(active["activity"]["active"])
        self.assertEqual(active["activity"]["title"],"Technical book")
        stale=book_learning_snapshot(self.root,now=now+600)
        self.assertFalse(stale["activity"]["active"])
        self.assertTrue(stale["activity"]["stale"])

    def test_owner_plan_vs_indexed_only(self):
        plan={"schema":"suryadev.book-plan.v1","books":[
            {"path":str(self.root/"one.epub"),"sha256":"a"*64},
            {"path":str(self.root/"two.pdf"),"sha256":"b"*64}]}
        (self.root/"book-plan.json").write_text(json.dumps(plan),encoding="utf-8")
        info=book_learning_snapshot(self.root)
        self.assertEqual(info["approved"],2)
        self.assertEqual(info["indexed"],0)
        self.assertTrue(info["plan_present"])

    def test_dashboard_sources_books_and_telemetry_use_shared_live_data(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/"dashboard.html").read_text(encoding="utf-8")
        main=(root/"dashboard.js").read_text(encoding="utf-8")
        netra=(root/"dashboard-garudanetra.js").read_text(encoding="utf-8")
        books=(root/"dashboard-books.js").read_text(encoding="utf-8")
        srv=(root/"suryadev_extras.py").read_text(encoding="utf-8")
        ops=(root/"suryadev_liveops.py").read_text(encoding="utf-8")
        installer=(root/"install-windows.ps1").read_text(encoding="utf-8")
        self.assertNotIn('id="book-learning"',html)
        self.assertNotIn('href="#book-learning"',html)
        self.assertIn('id="netra-books-running"',html)
        self.assertIn('id="netra-books-lines"',html)
        self.assertIn('id="book-ledger-list"',html)
        self.assertNotIn('id="book-health"',html)
        self.assertIn('id="source-grid"',html)
        self.assertNotIn('source.append(bookCard)',main)
        self.assertIn('book_learning',netra)
        self.assertNotIn('bookHealth.replaceChildren',main)
        self.assertIn('id="book-ledger-list"',html)
        self.assertIn('bookActive',netra)
        self.assertIn('No live work right now:',netra)
        self.assertIn('data.by_source?.website?.done',netra)
        self.assertIn('renderLive(await response.json())',main)
        self.assertIn('window.suryadevRead("/api/books"',books)
        self.assertIn('"book_learning": books',srv)
        self.assertIn('2026-10-23-v7.2-laptop-cpu-guard',srv)
        for feature in ('has_books_in_garudanetra',
                        'has_books_in_source_coverage',
                        'has_books_in_laptop_health'):
            self.assertIn(feature,srv)
        self.assertIn('"book_learning": books',ops)
        self.assertIn("'suryadev_book_dashboard.py'",installer)
        self.assertNotIn("innerHTML",books)


if __name__ == "__main__":
    unittest.main()
