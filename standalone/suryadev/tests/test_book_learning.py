"""Full-book sequential reader: no skipped lines, no lookahead, durable checkpoint."""
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

from suryadev_book_reader import BookLedger, HtmlLines, _parse_xml, file_sha256


def make_epub(path):
    container = '''<?xml version="1.0"?>
    <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles><rootfile full-path="OPS/content.opf"/></rootfiles></container>'''
    opf = '''<package xmlns="http://www.idpf.org/2007/opf">
    <manifest><item id="ch1" href="one.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="two.xhtml" media-type="application/xhtml+xml"/></manifest>
    <spine><itemref idref="ch1"/><itemref idref="ch2"/></spine></package>'''
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("META-INF/container.xml", container)
        z.writestr("OPS/content.opf", opf)
        z.writestr("OPS/one.xhtml", "<html><body><h1>Chapter One</h1><p>Alpha</p>"
                   "<script>DROP ALL DATA</script><p>Beta</p></body></html>")
        z.writestr("OPS/two.xhtml", "<html><body><h1>Chapter Two</h1>"
                   "<p>Gamma &amp; Delta</p></body></html>")


class BookLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = BookLedger(self.root)

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def test_txt_first_to_last_every_line_and_resume_one_at_a_time(self):
        path = self.root / "owned.txt"
        path.write_text("first line\nsecond line\nthird line",encoding="utf-8")
        obj = self.ledger.import_book(path,title="Test Book")
        self.assertEqual(obj["lines_total"],3)
        self.assertEqual(self.ledger.import_book(path)["book_id"],obj["book_id"])
        prompts = []
        def model(prompt, name):
            prompts.append(prompt)
            return "Read and explain one line"
        partial = self.ledger.read(obj["book_id"],model="local-test",
                                   max_steps=1,observe=model)
        self.assertFalse(partial["reached_end"])
        self.assertEqual(partial["lines_processed_total"],1)
        self.assertEqual(len(prompts),1)
        self.assertIn("first line",prompts[0])
        self.assertNotIn("second line",prompts[0])
        self.ledger.close()
        self.ledger=BookLedger(self.root)
        finished = self.ledger.read(obj["book_id"],model="local-test",
                                    observe=model)
        self.assertTrue(finished["reached_end"])
        self.assertEqual(finished["lines_processed_total"],3)
        self.assertEqual(len(prompts),3)
        self.assertIn("second line",prompts[1])
        self.assertNotIn("third line",prompts[1])
        self.assertIn("third line",prompts[2])
        self.assertFalse(finished["comprehension_verified"])
        self.assertEqual(self.ledger.read(obj["book_id"],model="local-test",
                                          observe=model)["steps_committed_this_run"],0)
        self.assertEqual(self.ledger.verify(obj["book_id"])["indexed_lines_verified"],3)

    def test_error_cannot_advance_reading_and_retry_at_exact_line(self):
        path=self.root/"error.txt";path.write_text("zero\none\ntwo",encoding="utf-8")
        bid=self.ledger.import_book(path)["book_id"]
        count=[0]
        def intermittent(prompt, model):
            count[0]+=1
            if count[0] == 2:
                raise RuntimeError("Ollama busy")
            return "source considered"
        with self.assertRaisesRegex(RuntimeError,"Ollama busy"):
            self.ledger.read(bid,model="local",observe=intermittent)
        status=self.ledger.status(bid)["sessions"]["ollama:local"]
        self.assertEqual(status["lines_processed"],1)
        self.assertIn("Ollama busy",status["last_error"])
        end=self.ledger.read(bid,model="local",observe=intermittent)
        self.assertTrue(end["reached_end"])
        self.assertEqual(end["steps_committed_this_run"],2)
        self.assertEqual(self.ledger.verify(bid)["indexed_lines_verified"],3)

    def test_preview_mode_does_not_create_false_model_success(self):
        path=self.root/"preview.md"
        path.write_text("# First\n\nLast",encoding="utf-8")
        bid=self.ledger.import_book(path)["book_id"]
        with patch("suryadev.summarize",side_effect=AssertionError("model must not run")):
            record=self.ledger.read(bid,use_ollama=False,lines_per_step=2)
        self.assertTrue(record["reached_end"])
        self.assertEqual(record["mode"],"extractive_record_only")
        self.assertNotIn("ollama:gemma3:4b",self.ledger.status(bid)["sessions"])
        self.assertEqual(self.ledger.db.execute(
            "SELECT count(*) FROM book_journal WHERE mode='extractive_record_only'").fetchone()[0],2)

    def test_epub_spine_chapters_not_reordered_or_omitted(self):
        path=self.root/"novel.epub";make_epub(path)
        obj=self.ledger.import_book(path)
        rows=self.ledger.db.execute(
            "SELECT section,text FROM book_lines WHERE book_id=? ORDER BY ordinal",
            (obj["book_id"],)).fetchall()
        source="\n".join(t for _,t in rows)
        self.assertTrue(source.index("Chapter One")<source.index("Alpha")<
                        source.index("Beta")<source.index("Chapter Two")<
                        source.index("Gamma & Delta"))
        self.assertNotIn("DROP ALL DATA",source)
        self.assertTrue(all(rows[i][0].startswith("chapter 1") for i in range(
            next(j for j,r in enumerate(rows) if "chapter 2" in r[0]))))
        self.assertEqual(self.ledger.verify(obj["book_id"])["indexed_lines_verified"],
                         obj["lines_total"])

    def test_epub_includes_supplemental_nonlinear_spine_appendix(self):
        path=self.root/"with-appendix.epub"
        with zipfile.ZipFile(path,"w") as z:
            z.writestr("META-INF/container.xml",
                '<container><rootfile full-path="OPS/book.opf"/></container>')
            z.writestr("OPS/book.opf",
                '<package><manifest><item id="primary" href="p.xhtml" media-type="application/xhtml+xml"/>'
                '<item id="notes" href="notes.xhtml" media-type="application/xhtml+xml"/></manifest>'
                '<spine><itemref idref="notes" linear="no"/><itemref idref="primary"/></spine></package>')
            z.writestr("OPS/p.xhtml","<html><body><p>Main text</p></body></html>")
            z.writestr("OPS/notes.xhtml","<html><body><p>Important appendix</p></body></html>")
        bid=self.ledger.import_book(path)["book_id"]
        rows=[x[0] for x in self.ledger.db.execute(
            "SELECT text FROM book_lines WHERE book_id=? ORDER BY ordinal",(bid,))]
        self.assertIn("Main text",rows)
        self.assertIn("Important appendix",rows)
        self.assertLess(rows.index("Main text"),rows.index("Important appendix"))
        self.assertEqual(self.ledger.verify(bid)["indexed_lines_verified"],len(rows))

    def test_source_changes_after_reading_detected_in_verification(self):
        path=self.root/"changed.txt"
        path.write_text("original reference",encoding="utf-8")
        bid=self.ledger.import_book(path)["book_id"]
        self.ledger.read(bid,use_ollama=False)
        path.write_text("changed reference",encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"Original book file"):
            self.ledger.verify(bid)

    def test_malformed_epub_has_no_partial_committed_book(self):
        path=self.root/"bad.epub"
        with zipfile.ZipFile(path,"w") as z:
            z.writestr("META-INF/container.xml",'<container><rootfile full-path="OPS/book.opf"/></container>')
            z.writestr("OPS/book.opf",'<package><manifest></manifest><spine><itemref idref="absent"/></spine></package>')
        with self.assertRaisesRegex(ValueError,"Missing EPUB spine reference"):
            self.ledger.import_book(path)
        self.assertEqual(self.ledger.status()["books"],[])
        with self.assertRaisesRegex(ValueError,"DTD/ENTITY"):
            _parse_xml(b'<!DOCTYPE x [<!ENTITY ex SYSTEM "file:///secret">]><x>&ex;</x>')

    def test_pdf_all_pages_and_ocr_last_page_before_complete(self):
        file=self.root/"owned.pdf";file.write_bytes(b"%PDF-test")
        class PDF:
            is_encrypted=False
            def __init__(self,*args,**kwargs):
                self.pages=[types.SimpleNamespace(extract_text=lambda:"a\nb"),
                            types.SimpleNamespace(extract_text=lambda:"")]
        with patch.dict(sys.modules,{"pypdf":types.SimpleNamespace(PdfReader=PDF)}):
            with self.assertRaisesRegex(ValueError,"page 2 needs local OCR"):
                self.ledger.import_book(file)
            self.assertEqual(self.ledger.status()["books"],[])
            obj=self.ledger.import_book(
                file,ocr=lambda p,page:"scanned image line" if page==2 else "")
        rows=self.ledger.db.execute(
            "SELECT page_number,line_in_section,text FROM book_lines WHERE book_id=? "
            "ORDER BY ordinal",(obj["book_id"],)).fetchall()
        self.assertEqual(rows,[(1,1,"a"),(1,2,"b"),(2,1,"scanned image line")])

    def test_detect_line_tampering_and_no_false_evidence_verification(self):
        file=self.root/"owned.txt";file.write_text("truth",encoding="utf-8")
        bid=self.ledger.import_book(file)["book_id"]
        self.ledger.read(bid,use_ollama=False)
        with self.ledger.db:
            self.ledger.db.execute(
                "UPDATE book_lines SET text='incorrect' WHERE book_id=?",(bid,))
        with self.assertRaisesRegex(RuntimeError,"corrupt line"):
            self.ledger.verify(bid)

    def test_installer_and_cli_ship_book_reader(self):
        source=Path(__file__).resolve().parents[1]
        installer=(source/"install-windows.ps1").read_text(encoding="utf-8")
        extra=(source/"suryadev_extras.py").read_text(encoding="utf-8")
        self.assertIn("'suryadev_book_reader.py'",installer)
        for command in ("book-import","book-read","book-status","book-verify"):
            self.assertIn('"'+command+'"',extra)


if __name__=="__main__":
    unittest.main()
