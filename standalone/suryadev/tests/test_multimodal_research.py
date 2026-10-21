"""Offline gate tests: all PDF pages, full-frame scan, bounded vision and comments."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from suryadev_deep_pdf import inspect_pdf_pages, deep_pdf_settings
from suryadev_deep_web import deep_web_settings, inspect_page
from suryadev_video_lab import scan_video, video_research, read_comments


class FakePage:
    def __init__(self,text="Page content"):
        self.text=text
    def extract_text(self):
        return self.text


class PdfDeepTests(unittest.TestCase):
    def test_ocr_and_local_vision_visit_every_single_page(self):
        pdf=types.SimpleNamespace(pages=[FakePage("A"),FakePage(""),
                                         FakePage("C")])
        rendered=[]
        def render(index):
            rendered.append(index)
            return {"page":index}
        pages,report=inspect_pdf_pages(
            b"%PDF-test",pdf,rasterizer=render,
            ocr=lambda page:"OCR"+str(page["page"]),
            vision=lambda page:"Chart explanation "+str(page["page"]))
        self.assertEqual(rendered,[0,1,2])
        self.assertEqual(len(pages),3)
        self.assertEqual(pages[1]["ocr_text"],"OCR1")
        self.assertEqual(report["pages_visual_model_examined"],3)
        self.assertFalse(report["semantic_comprehension_verified"])

    def test_missing_visual_or_unreadable_scanned_page_fails_closed(self):
        pdf=types.SimpleNamespace(pages=[FakePage("")])
        with self.assertRaisesRegex(RuntimeError,"page 1/1 incomplete"):
            inspect_pdf_pages(b"%PDF-test",pdf,rasterizer=lambda i: i,
                              ocr=lambda frame:"",vision=lambda frame:"nothing")
        with self.assertRaisesRegex(RuntimeError,"requires explicitly"):
            inspect_pdf_pages(b"%PDF-test",pdf,rasterizer=lambda i: i,
                              ocr=lambda frame:"yes",vision=None)

    def test_deep_enabling_explicit(self):
        self.assertFalse(deep_pdf_settings({})[0])
        self.assertEqual(deep_pdf_settings({"SURYADEV_DEEP_PDF":"1",
                                           "SURYADEV_VISION_MODEL":"gemma3:4b"}),
                         (True,"gemma3:4b"))
        self.assertFalse(deep_web_settings({})[0])


class Frame:
    def __init__(self, value): self.value = value
    def tobytes(self): return bytes([self.value])*4


class Capture:
    def __init__(self,n):self.frames=list(range(n));self.closed=False
    def isOpened(self):return True
    def get(self, param):return 2 if param==1 else len(self.frames)
    def read(self):
        return (True,Frame(self.frames.pop(0))) if self.frames else (False,None)
    def release(self):self.closed=True


class VideoLabTests(unittest.TestCase):
    def test_every_frame_scanned_but_only_sampled_frames_understood(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"approved.mp4";file.write_bytes(b"owner video")
            cap=Capture(5)
            fake_cv2=types.SimpleNamespace(CAP_PROP_FPS=1,CAP_PROP_FRAME_COUNT=2)
            with patch.dict(sys.modules,{"cv2":fake_cv2}):
                report=scan_video(file,capture=cap,
                                  visual_fn=lambda frame, t:"Frame meaning",
                                  visual_interval_seconds=1,max_visual_frames=2)
            self.assertTrue(cap.closed)
            self.assertEqual(report["frames_decoded"],5)
            self.assertEqual(report["frames_semantically_interpreted"],2)
            self.assertFalse(report["all_frames_semantically_interpreted"])
            self.assertTrue(report["all_decoded_frames_scanned"])
            self.assertEqual(len(report["frame_pixel_chain_sha256"]),64)

    def test_each_frame_vision_mode_is_explicit_and_strict(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td)/"approved.mp4"
            file.write_bytes(b"locally provided")
            cap = Capture(3)
            fake_cv2 = types.SimpleNamespace(CAP_PROP_FPS=1,CAP_PROP_FRAME_COUNT=2)
            with patch.dict(sys.modules, {"cv2":fake_cv2}):
                report=scan_video(
                    file, capture=cap, visual_fn=lambda frame,at:"interpreted",
                    every_frame_vision=True,max_visual_frames=3)
            self.assertEqual(report["frames_decoded"],3)
            self.assertEqual(report["frames_semantically_interpreted"],3)
            self.assertTrue(report["all_frames_semantically_interpreted"])
            reject = Capture(3)
            with patch.dict(sys.modules, {"cv2":fake_cv2}):
                with self.assertRaisesRegex(ValueError, "model-call budget"):
                    scan_video(file, capture=reject,
                               visual_fn=lambda frame,at:"interpreted",
                               every_frame_vision=True,max_visual_frames=2)
            self.assertTrue(reject.closed)
            with self.assertRaisesRegex(ValueError, "requires a local"):
                scan_video(file, capture=Capture(1),
                           every_frame_vision=True,visual_fn=None)

    def test_local_video_sidecars_comments_not_automatically_scraped(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"approved.mp4";path.write_bytes(b"legal local video")
            desc=Path(td)/"description.txt";desc.write_text("description",encoding="utf-8")
            comments=Path(td)/"comments.json"
            comments.write_text(json.dumps(["opinion 1",{"text":"opinion 2"}]),encoding="utf-8")
            captions=Path(td)/"captions.srt"
            captions.write_text("1\n00:00:00,000 --> 00:00:01,000\nResearch audio\n",encoding="utf-8")
            def fake_scanner(media,**kwargs):
                self.assertIsNone(kwargs["visual_fn"])
                return {"frames_decoded":42,"video_duration_seconds":2,
                        "visual_samples":[],"all_decoded_frames_scanned":True,
                        "frames_semantically_interpreted":0}
            result=video_research(path,td,description_file=desc,
                    comments_file=comments,transcript_file=captions,
                    scanner=fake_scanner)
            self.assertEqual(result["comments"]["analyzed"],2)
            self.assertFalse(result["semantic_comprehension_verified"])
            self.assertEqual(result["provider_youtube_requests"],0)
            self.assertIn("Research audio",Path(result["evidence_file"]).read_text())
            self.assertIn("opinion 2",Path(result["evidence_file"]).read_text())
            self.assertEqual(read_comments(comments)[1]["status"],
                             "owner_supplied_public_comment_snapshot")


class WebDeepTests(unittest.IsolatedAsyncioTestCase):
    async def test_scrolls_every_viewport_records_images_and_links(self):
        class Page:
            def __init__(self):self.moves=[]
            async def evaluate(self, expr, *args):
                if "images: Array.from" in expr:
                    return {"images":[{"alt":"network topology","src":"https://example.org/a.png",
                                       "complete":True,"width":40,"height":10}],
                            "links":[{"href":"https://example.org/next","label":"next"}],
                            "embeds":[],"tables":1,"canvas":0,"svg":0}
                if "height:window.innerHeight" in expr:
                    return {"height":600,"documentHeight":1200}
                if "window.scrollTo" in expr:
                    self.moves.append(args[0]);return None
                if "scrollHeight" in expr:return 1200
                raise AssertionError(expr)
            async def wait_for_timeout(self,ms):pass
            async def screenshot(self,**kwargs):return b"pretend png"
        page=Page()
        result=await inspect_page(page,model="local",pause_ms=0,
                                  vision=lambda png:"Visual table")
        self.assertEqual(page.moves,[0,600,0])
        self.assertEqual(result["viewports_visited"],2)
        self.assertEqual(result["viewports_interpreted_by_local_vision"],2)
        self.assertFalse(result["semantic_comprehension_verified"])
        self.assertEqual(result["links_discovered"],1)


if __name__=="__main__":
    unittest.main()
