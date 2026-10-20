"""End-to-end contract tests for three source types, evidence, and six-hour feed."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_feeder import read_plan, feed_once, feed_links, allowed_source
from suryadev_ingest import caption_cues, caption_report, ingest_pdf, ingest_youtube
from suryadev_summary import summarize_all
from suryadev_task_details import task_detail


VTT = """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello welcome

00:00:05.000 --> 00:00:10.000
This is the second lesson

00:00:10.000 --> 00:00:20.000
And the third lesson
"""


class FakePDFReader:
    is_encrypted = False
    def __init__(self, data, strict=True):
        assert data.read(5) == b"%PDF-"
        self.pages = [types.SimpleNamespace(extract_text=lambda: "First page content"),
                      types.SimpleNamespace(extract_text=lambda: "Second page content")]


class PipelineTests(unittest.TestCase):
    def test_captions_are_timestamped_but_not_full_video_verified(self):
        cues = caption_cues(VTT)
        self.assertEqual(len(cues), 3)
        report = caption_report(cues, 20)
        self.assertEqual(report["last_cue_seconds"], 20)
        self.assertTrue(report["last_cue_near_duration_end"])
        self.assertFalse(report["full_video_visuals_verified"])
        self.assertFalse(report["full_audio_coverage_verified"])

    @patch("suryadev.validate_url", return_value="https://example.com/paper.pdf")
    @patch("suryadev_ingest.build_opener")
    def test_pdf_extracts_all_pages(self, opener, validate):
        class Response:
            headers = {"Content-Encoding":"identity", "Content-Length":"23"}
            def read(self, _size): return b"%PDF- fake PDF payload"
            def __enter__(self): return self
            def __exit__(self, *_): return False
        opener.return_value.open.return_value = Response()
        with patch.dict(sys.modules, {"pypdf":types.SimpleNamespace(PdfReader=FakePDFReader)}):
            title, text, report = ingest_pdf("https://example.com/paper.pdf")
        self.assertIn("[PDF page 1/2]", text)
        self.assertIn("[PDF page 2/2]", text)
        self.assertEqual(report["pages_extracted"], 2)
        self.assertFalse(report["full_document_visuals_verified"])

    @patch("suryadev.validate_url", return_value="https://example.com/paper.pdf")
    @patch("suryadev_ingest.build_opener")
    def test_scanned_pdf_fails_not_marked_complete(self, opener, validate):
        class Response:
            headers = {"Content-Encoding":"identity"}
            def read(self, _size): return b"%PDF- fake PDF payload"
            def __enter__(self): return self
            def __exit__(self, *_): return False
        opener.return_value.open.return_value = Response()
        class Reader(FakePDFReader):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.pages[1] = types.SimpleNamespace(extract_text=lambda: "")
        with patch.dict(sys.modules, {"pypdf":types.SimpleNamespace(PdfReader=Reader)}):
            with self.assertRaisesRegex(ValueError, "page text missing"):
                ingest_pdf("https://example.com/paper.pdf")

    def test_youtube_caption_ingest_reports_timeline_only(self):
        class Downloader:
            def __init__(self, options): self.options=options
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, url, download):
                folder = Path(self.options["outtmpl"]).parent
                (folder / "abcdefghijk.en.vtt").write_text(VTT, encoding="utf-8")
                return {"id":"abcdefghijk", "duration":20, "title":"Test learning video"}
        with patch.dict(sys.modules, {"yt_dlp":types.SimpleNamespace(YoutubeDL=Downloader)}):
            title, text, report = ingest_youtube("https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(report["cue_count"], 3)
        self.assertIn("second lesson", text)
        self.assertEqual(report["coverage_status"], "caption_timeline_only_unverified")
        self.assertFalse(report["full_video_visuals_verified"])

    def test_youtube_no_captions_fails(self):
        class Downloader:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, url, download):
                return {"id":"abcdefghijk", "duration":100, "title":"No captions"}
        with patch.dict(sys.modules, {"yt_dlp":types.SimpleNamespace(YoutubeDL=Downloader)}):
            with self.assertRaisesRegex(ValueError, "No supported YouTube captions"):
                ingest_youtube("https://www.youtube.com/watch?v=abcdefghijk")

    def test_every_chunk_summarized_or_only_preview_claimed(self):
        seen = []
        def fake_summary(prompt, model):
            seen.append(prompt)
            return "Covered segment " + str(len(seen))
        text = "A" * 19001
        value, report = summarize_all(text, model="fake", use_ollama=True,
                                      summarize_fn=fake_summary)
        self.assertEqual(len(seen), 3)
        self.assertEqual(report["chunks_total"], 3)
        self.assertEqual(report["chunks_summarized"], 3)
        self.assertIn("Covered segment 3", value)
        preview, report = summarize_all(text, model="fake", use_ollama=False,
                                        summarize_fn=fake_summary)
        self.assertEqual(report["summary_coverage"], "extractive_preview_only")
        self.assertEqual(len(preview), 2000)

    @patch("suryadev.validate_url", return_value="https://example.com/test")
    @patch("suryadev.fetch_text", return_value=("Test website", "Evidence across complete sample"))
    def test_website_worker_saves_provenance(self, fetch, validate):
        with tempfile.TemporaryDirectory() as directory:
            lib = Library(directory)
            lib.add("https://example.com/test")
            result = lib.run_next(use_ollama=False)
            self.assertEqual(result["status"], "done")
            detail = task_detail(lib.db, directory, result["job_id"])
            self.assertEqual(detail["evidence_state"], "verified")
            self.assertEqual(detail["coverage"]["summary_coverage"], "extractive_preview_only")
            self.assertFalse(detail["complete_verified"])
            lib.db.close()

    @patch("suryadev.validate_url", return_value="https://www.youtube.com/watch?v=abcdefghijk")
    @patch("suryadev_ingest.ingest_youtube",
           return_value=("Test video", "[0.00-20.00s] video speech",
                         {"kind":"youtube","coverage_status":"caption_timeline_only_unverified",
                          "cue_count":1,"last_cue_seconds":20,"full_video_visuals_verified":False}))
    def test_youtube_queue_worker_and_saved_receipt(self, video, validate):
        with tempfile.TemporaryDirectory() as directory:
            lib = Library(directory)
            lib.add("https://www.youtube.com/watch?v=abcdefghijk")
            done = lib.run_next(use_ollama=False)
            self.assertEqual(done["status"], "done")
            detail = task_detail(lib.db, directory, done["job_id"])
            self.assertEqual(detail["coverage"]["cue_count"],1)
            self.assertTrue(any(step["name"] == "YouTube timed caption processing" for step in detail["steps"]))
            self.assertEqual(detail["steps"][-2]["state"], "unverified")
            lib.db.close()

    def test_feed_links_and_host_allowlist(self):
        rss = b"<rss><channel><item><link>https://example.com/one</link></item></channel></rss>"
        self.assertEqual(feed_links(rss),["https://example.com/one"])
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><link rel="alternate" href="https://example.com/two"/></entry></feed>'
        self.assertEqual(feed_links(atom),["https://example.com/two"])
        with self.assertRaisesRegex(ValueError, "DTD/ENTITY"):
            feed_links(b'<!DOCTYPE doc [ <!ENTITY x "evil"> ]><rss/>')
        self.assertFalse(allowed_source("https://unapproved.net/",{"example.com"}))
        self.assertTrue(allowed_source("https://example.com/yes",{"example.com"}))

    @patch("suryadev.validate_url", return_value="https://example.com/one")
    def test_six_hour_feeder_adds_only_approved_new_urls(self, validate):
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "sources.json"
            plan_path.write_text(json.dumps({
                "approved_urls":["https://example.com/one"],
                "approved_feeds":["https://example.com/rss.xml"],
                "allowed_source_hosts":["example.com"],
                "max_new_per_cycle":5, "max_queued":20
            }), encoding="utf-8")
            plan = read_plan(plan_path)
            lib = Library(directory)
            xml = b"<rss><channel><item><link>https://example.com/two</link></item><item><link>https://evil.com/abc</link></item></channel></rss>"
            with patch("suryadev_feeder.fetch_feed", return_value=xml):
                # Default kwarg is bound at definition time: pass explicit test fetcher.
                first = feed_once(lib, plan, fetcher=lambda u: xml)
                second = feed_once(lib, plan, fetcher=lambda u: xml)
            self.assertEqual(first["added_total"],2)
            self.assertEqual(second["added_total"],0)
            self.assertEqual(lib.stats()["queued"],2)
            lib.db.close()


if __name__ == "__main__":
    unittest.main()
