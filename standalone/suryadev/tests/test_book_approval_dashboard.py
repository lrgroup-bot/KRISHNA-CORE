"""Book owner-approval, fail-closed updates, and the local read-only UI contract."""
from pathlib import Path
import json
import tempfile
import unittest

from suryadev_book_continuity import approve_book, read_book_plan
from suryadev_book_reader import BookLedger


class ApprovedBookPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.first=self.root/"volume-1.txt"
        self.first.write_text("Original volume one\nSecond line",encoding="utf-8")
        self.second=self.root/"volume-2.txt"
        self.second.write_text("A new approved book",encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_owner_approval_records_source_sha_then_preserves_plan(self):
        first=approve_book(self.root,self.first,lines_per_step=2)
        self.assertEqual(first["status"],"approved")
        plan=read_book_plan(first["plan"])
        self.assertEqual(len(plan["books"]),1)
        self.assertEqual(plan["lines_per_step"],2)
        again=approve_book(self.root,self.first)
        self.assertEqual(again["status"],"already_approved")
        second=approve_book(self.root,self.second)
        self.assertEqual(second["approved_books"],2)
        self.assertEqual(len(read_book_plan(first["plan"])["books"]),2)
        backups=list(self.root.glob("book-plan.backup-*.json"))
        self.assertEqual(len(backups),1)
        self.assertEqual(len(json.loads(backups[0].read_text())["books"]),1)

    def test_edited_approved_book_denied_without_importing_new_content(self):
        first=approve_book(self.root,self.first)
        self.first.write_text("changed after the original owner approval",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"previously approved book changed"):
            approve_book(self.root,self.first)
        ledger=BookLedger(self.root)
        ids=ledger.status()["books"]
        self.assertEqual(len(ids),1)
        self.assertEqual(ids[0]["book_id"],first["book_id"])
        ledger.close()
        self.assertEqual(len(read_book_plan(first["plan"])["books"]),1)

    def test_exact_source_line_search_remains_cited_and_never_fakes_learning(self):
        approved=approve_book(self.root,self.first)
        ledger=BookLedger(self.root)
        match=ledger.search("Original volume",limit=10)
        self.assertEqual(match["returned"],1)
        row=match["matches"][0]
        self.assertEqual(row["source_line"],"Original volume one")
        self.assertEqual(row["line_in_section"],1)
        self.assertEqual(row["book_id"],approved["book_id"])
        self.assertIsNone(row["ai_reading_mode"])
        self.assertEqual(len(row["line_sha256"]),64)
        self.assertFalse(row["comprehension_verified"])
        self.assertEqual(ledger.search("' OR 1=1 --")["returned"],0)
        with self.assertRaisesRegex(ValueError,"2..120"):
            ledger.search("")
        ledger.close()

    def test_existing_approval_unmodified_if_new_book_is_invalid(self):
        first=approve_book(self.root,self.first)
        malformed=self.root/"corrupt.epub"
        malformed.write_bytes(b"not an epub")
        with self.assertRaises(Exception):
            approve_book(self.root,malformed)
        self.assertEqual(len(read_book_plan(first["plan"])["books"]),1)


class BookDashboardContractTests(unittest.TestCase):
    def test_books_integrated_in_garudanetra_and_escaped(self):
        source=Path(__file__).resolve().parents[1]
        html=(source/"dashboard.html").read_text(encoding="utf-8")
        js=(source/"dashboard-books.js").read_text(encoding="utf-8")
        css=(source/"dashboard-books.css").read_text(encoding="utf-8")
        server=(source/"suryadev_extras.py").read_text(encoding="utf-8")
        installer=(source/"install-windows.ps1").read_text(encoding="utf-8")
        for token in ("id=\"garudanetra\"","id=\"book-ledger-list\"",
                      "id=\"netra-books-running\"",
                      'src="/dashboard-books.js"',
                      'href="/dashboard-books.css"'):
            self.assertIn(token,html)
        self.assertNotIn('id="book-learning"',html)
        self.assertNotIn('href="#book-learning"',html)
        self.assertNotIn('id="book-health"',html)
        self.assertIn('id="source-grid"',html)
        for token in ('window.suryadevRead("/api/books"','textContent','replaceChildren'):
            self.assertIn(token,js)
        self.assertNotIn("innerHTML",js)
        self.assertIn(".books-grid",css)
        for token in ('route.path == "/api/books"','"/dashboard-books.js"',
                      '"/dashboard-books.css"'):
            self.assertIn(token,server)
        for token in ("'suryadev_book_reader.py'","'suryadev_book_handoff.py'",
                      "'suryadev_book_continuity.py'","'suryadev_book_visuals.py'",
                      "'dashboard-books.js'","'dashboard-books.css'"):
            self.assertIn(token,installer)
        self.assertIn('"--sync-book-handoff"',server)
        self.assertIn('"--book-visual-model"',server)
        self.assertIn('"book-approve"',server)
        self.assertIn('"book-visuals"',server)
        self.assertIn('route.path == "/api/book-search"',server)
        self.assertIn('id="book-search-form"',html)
        self.assertIn('window.suryadevRead("/api/book-search?q="',js)
        self.assertIn('"book-search"',server)


if __name__=="__main__":
    unittest.main()
