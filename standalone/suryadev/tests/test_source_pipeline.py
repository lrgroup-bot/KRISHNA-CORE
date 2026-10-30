"""End-to-end contract tests for three source types, evidence, and six-hour feed."""
import hashlib
import json
from pathlib import Path
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_feeder import read_plan, feed_once, feed_links, allowed_source, fetch_feed, MAX_FEED_BYTES
from suryadev_ingest import caption_cues, caption_report, ingest_pdf, ingest_youtube, selected_caption_language
from suryadev_summary import summarize_all
from suryadev_mission import mission
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

    def test_caption_download_is_one_language_only_with_no_429_retry(self):
        urls = []
        class Downloader:
            def __init__(self, opts):
                assert opts["subtitleslangs"] == ["en"]
                assert opts["retries"] == 0
                assert opts["extractor_retries"] == 0
                assert opts["fragment_retries"] == 0
                assert opts["sleep_interval_subtitles"] >= 1
                self.options = opts
            def __enter__(self): return self
            def __exit__(self,*_): pass
            def extract_info(self,url,download):
                urls.append(url)
                folder = Path(self.options["outtmpl"]).parent
                (folder / "abcdefghijk.en.vtt").write_text(VTT,encoding="utf-8")
                return {"id":"abcdefghijk","duration":20,"title":"One language"}
        with patch.dict(os.environ, {"SURYADEV_CAPTION_LANG":"en"}):
            with patch.dict(sys.modules, {"yt_dlp":types.SimpleNamespace(YoutubeDL=Downloader)}):
                title,text,coverage = ingest_youtube(
                    "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(len(urls),1)
        self.assertEqual(coverage["caption_language_requested"],"en")
        self.assertEqual(coverage["cue_count"],3)

    def test_caption_language_operator_choice_and_invalid_rejection(self):
        for code in ("en","hi","or"):
            with patch.dict(os.environ,{"SURYADEV_CAPTION_LANG":code}):
                self.assertEqual(selected_caption_language(),code)
        with patch.dict(os.environ,{"SURYADEV_CAPTION_LANG":"all"}):
            with self.assertRaisesRegex(ValueError,"en, hi, or"):
                selected_caption_language()

    def test_youtube_429_is_explicit_error_with_no_secondary_language_attempt(self):
        class Downloader:
            calls=0
            def __init__(self,opts):
                self.opts=opts
                self.assert_opts = opts
            def __enter__(self): return self
            def __exit__(self,*_): pass
            def extract_info(self,url,download):
                type(self).calls += 1
                assert self.opts["subtitleslangs"] == ["en"]
                raise RuntimeError("Unable to download video subtitles for 'en': HTTP Error 429: Too Many Requests")
        with patch.dict(os.environ,{"SURYADEV_CAPTION_LANG":"en"}):
            with patch.dict(sys.modules,{"yt_dlp":types.SimpleNamespace(YoutubeDL=Downloader)}):
                with self.assertRaisesRegex(RuntimeError,"YouTube HTTP 429.*No automatic retry"):
                    ingest_youtube("https://www.youtube.com/watch?v=abcdefghijk")
        self.assertEqual(Downloader.calls,1)

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

    def test_large_full_length_captions_are_chunked_not_discarded(self):
        # Regression for the actual CS50P lecture failure (>220k chars).
        speech="source anchored proof " * 12000 + "THE FINAL CAPTION PROOF"
        vtt=("WEBVTT\n\n00:00:00.000 --> 00:03:20.000\n"
             +speech+"\n")
        class Downloader:
            def __init__(self,options):
                self.options=options
            def __enter__(self):
                return self
            def __exit__(self,*args):
                return False
            def extract_info(self,url,download):
                folder=Path(self.options["outtmpl"]).parent
                (folder/"abcdefghijk.en.vtt").write_text(vtt,encoding="utf-8")
                return {"id":"abcdefghijk","duration":200,
                        "title":"Long documented lecture"}
        with patch.dict(sys.modules,{"yt_dlp":types.SimpleNamespace(YoutubeDL=Downloader)}):
            title, text, coverage=ingest_youtube(
                "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertGreater(len(text),220_000)
        self.assertIn("THE FINAL CAPTION PROOF",text)
        self.assertEqual(coverage["cue_count"],1)
        calls=[]
        def observer(prompt,model):
            calls.append(prompt)
            return "Candidate "+str(len(calls))
        summary,receipts=summarize_all(text,model="local-test",use_ollama=True,
                                        summarize_fn=observer)
        self.assertEqual(receipts["chunks_total"],receipts["chunks_summarized"])
        self.assertGreater(len(calls),24)
        self.assertIn("THE FINAL CAPTION PROOF",calls[-1])
        self.assertEqual(receipts["summary_coverage"],
                         "all_text_chunks_sent_to_ollama_unverified")

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
    @patch("suryadev_garudanetra.render_website", return_value=("Test website", "Evidence across complete sample", {"kind":"website","coverage_status":"garudanetra_rendered_text_unverified","browser_tab_opened":True,"full_rendered_page_verified":False}))
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

    @patch("suryadev.validate_url", return_value="https://example.com/sample.pdf")
    @patch("suryadev_ingest.ingest_pdf",
           return_value=("Sample PDF", "[PDF page 1/2] first\\n[PDF page 2/2] second",
                         {"kind":"pdf","coverage_status":"all_pages_text_extracted",
                          "pages_total":2,"pages_extracted":2,"pages_missing_text":[],
                          "full_document_visuals_verified":False}))
    def test_pdf_queue_to_evidence_and_page_receipt(self, pdf, validate):
        with tempfile.TemporaryDirectory() as directory:
            lib = Library(directory)
            job_id = lib.add("https://example.com/sample.pdf")
            result = lib.run_next(use_ollama=False)
            self.assertEqual(result["status"], "done")
            detail = task_detail(lib.db, directory, job_id)
            self.assertEqual(detail["coverage"]["pages_extracted"],2)
            self.assertTrue(any(step["name"] == "PDF page text extraction" and
                                step["state"] == "done" for step in detail["steps"]))
            self.assertFalse(detail["complete_verified"])
            lib.db.close()

    def test_mission_rejects_invalid_runtime_bounds(self):
        with self.assertRaises(ValueError):
            mission("unused", "unused.json", duration_hours=0)
        with self.assertRaises(ValueError):
            mission("unused", "unused.json", refill_minutes=1)
        with self.assertRaises(ValueError):
            mission("unused", "unused.json", check_seconds=1)

    def test_feed_links_and_host_allowlist(self):
        rss = b"<rss><channel><item><link>https://example.com/one</link></item></channel></rss>"
        self.assertEqual(feed_links(rss),["https://example.com/one"])
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><link rel="alternate" href="https://example.com/two"/></entry></feed>'
        self.assertEqual(feed_links(atom),["https://example.com/two"])
        with self.assertRaisesRegex(ValueError, "DTD/ENTITY"):
            feed_links(b'<!DOCTYPE doc [ <!ENTITY x "evil"> ]><rss/>')
        # Literal XML/HTML declarations quoted in an article's CDATA or
        # comments are DATA, not XML DTD or entity declarations.
        safe = (b'<rss><channel><item><description><![CDATA['
                b'Example: <!DOCTYPE html> and <!ENTITY demo>'
                b']]></description><link>https://example.com/cdata</link>'
                b'</item></channel></rss>')
        self.assertEqual(feed_links(safe), ["https://example.com/cdata"])
        commented = (b'<rss><!-- <!DOCTYPE html> -->'
                     b'<channel><item><link>https://example.com/comment</link>'
                     b'</item></channel></rss>')
        self.assertEqual(feed_links(commented), ["https://example.com/comment"])
        with self.assertRaisesRegex(ValueError, "DTD/ENTITY"):
            feed_links(b'<!DOCTYPE rss [<!ENTITY x "EXPAND">]>'
                       b'<rss><channel><item><link>&x;</link></item>'
                       b'</channel></rss>')
        self.assertFalse(allowed_source("https://unapproved.net/",{"example.com"}))
        self.assertTrue(allowed_source("https://example.com/yes",{"example.com"}))

    def test_large_approved_feed_stays_bounded_and_parsable(self):
        """A GitHub Blog-sized publisher response should not be rejected at 1 MiB."""
        html = b"x" * 1_400_000
        xml = b"<rss><channel><item><description>" + html + (
            b"</description><link>https://example.com/article</link>"
            b"</item></channel></rss>")
        class Response:
            headers = {"Content-Encoding": "identity"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit):
                self.limit = limit
                return xml[:limit]
        response = Response()
        with patch("suryadev_feeder.validate_url"), patch(
                "suryadev_feeder.build_opener") as opener:
            opener.return_value.open.return_value = response
            data = fetch_feed("https://example.com/rss.xml")
        self.assertEqual(data, xml)
        self.assertEqual(response.limit, MAX_FEED_BYTES + 1)
        self.assertEqual(feed_links(data), ["https://example.com/article"])
        self.assertLessEqual(MAX_FEED_BYTES, 8 * 1024 * 1024)

    def test_oversized_feed_rejected_by_header_and_body(self):
        class HeaderTooLarge:
            headers = {"Content-Encoding": "identity",
                       "Content-Length": str(MAX_FEED_BYTES + 1)}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit):
                raise AssertionError("oversized feed must fail before reading")
        class BodyTooLarge:
            headers = {"Content-Encoding": "identity"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit):
                assert limit == MAX_FEED_BYTES + 1
                return b"x" * limit
        with patch("suryadev_feeder.validate_url"), patch(
                "suryadev_feeder.build_opener") as opener:
            opener.return_value.open.return_value = HeaderTooLarge()
            with self.assertRaisesRegex(ValueError, "feed is too large"):
                fetch_feed("https://example.com/rss.xml")
            opener.return_value.open.return_value = BodyTooLarge()
            with self.assertRaisesRegex(ValueError, "feed is too large"):
                fetch_feed("https://example.com/rss.xml")

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
