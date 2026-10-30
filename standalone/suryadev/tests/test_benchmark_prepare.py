"""Opt-in 13-source trial does not invent authorization or run uncontrolled fetches."""
import io
from pathlib import Path
import tempfile
import unittest

from suryadev_benchmark_prepare import BOOKS, PDFS, VIDEOS, WEBSITES, download_book, DenyRedirect

class Response(io.BytesIO):
    status=200
    headers={"Content-Type":"application/pdf","Content-Length":"1029"}
    def __init__(self):
        super().__init__(b"%PDF-"+b"x"*1024)

class DownloadFixtureTests(unittest.TestCase):
    def test_fixed_catalogue_exact_count(self):
        self.assertEqual((len(BOOKS),len(PDFS),len(WEBSITES),len(VIDEOS)),
                         (5,3,2,3))
        self.assertEqual(len({entry[2] for entry in BOOKS}),5)
        self.assertTrue(all(u.startswith("https://") for u in PDFS+WEBSITES+VIDEOS))
        self.assertTrue(all(u.startswith("https://") for _,_,u in BOOKS))

    def test_explicit_book_allowlist_and_no_unapproved_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"trial.pdf"
            with self.assertRaisesRegex(ValueError,"not approved"):
                download_book("https://unknown.example/evil.pdf",target)
            self.assertFalse(target.exists())

    def test_approved_book_bytes_validated_and_cached(self):
        class Opener:
            count=0
            def open(self,*args,**kwargs):
                self.count+=1
                return Response()
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"sample.pdf"
            opener=Opener()
            returned=download_book(BOOKS[0][2],target,opener=opener)
            self.assertEqual(returned,target)
            self.assertEqual(target.read_bytes()[:5],b"%PDF-")
            returned=download_book(BOOKS[0][2],target,opener=opener)
            self.assertEqual(opener.count,1)
            self.assertFalse(any(Path(tmp).glob("*.partial-*")))

    def test_existing_non_pdf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"sample.pdf"
            target.write_bytes(b"<html>"+b"x"*2000)
            with self.assertRaisesRegex(ValueError,"not a PDF"):
                download_book(BOOKS[0][2],target)

    def test_redirects_not_followed(self):
        req=DenyRedirect().redirect_request(None,None,302,"Found",{},
                                            "https://unapproved.example/file.pdf")
        self.assertIsNone(req)

if __name__=="__main__":
    unittest.main()
