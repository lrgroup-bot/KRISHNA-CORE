"""One GARUDANETRA-owned browser across web, media and diagnostics."""
from pathlib import Path
import os
from unittest.mock import patch
import unittest

from suryadev_browser_engine import browser_channel, browser_identity, require_garudanetra
from suryadev_browser_preflight import _probe, CODEC_PROBE_JS
from suryadev_video_browser_probe import CHANNELS


class EngineIdentityTests(unittest.TestCase):
    def test_only_unbranded_chromium_is_allowed(self):
        self.assertEqual(CHANNELS,{"chromium"})
        self.assertEqual(browser_channel(),"chromium")
        self.assertEqual(require_garudanetra(),"chromium")
        self.assertEqual(require_garudanetra("chromium"),"chromium")
        for channel in ("chrome","msedge","chrome-beta","firefox","webkit"):
            with self.subTest(channel=channel),self.assertRaises(ValueError):
                require_garudanetra(channel)

    def test_previously_inherited_chrome_environment_is_ignored(self):
        for value in ("chrome","msedge","chromium",""):
            with self.subTest(value=value),patch.dict(os.environ,
                    {"SURYADEV_VIDEO_BROWSER_CHANNEL":value}):
                self.assertEqual(browser_channel(),"chromium")
                self.assertEqual(browser_identity()["browser_channel"],"chromium")
                self.assertFalse(browser_identity()["branded_browser_required"])
                self.assertEqual(
                    browser_identity()["obsolete_branded_channel_hint_ignored"],
                    value in ("chrome","msedge"))

    def test_video_collectors_cannot_open_new_windows(self):
        root=Path(__file__).resolve().parents[1]
        media=(root/"suryadev_garudanetra_media.py").read_text(encoding="utf-8")
        probe=(root/"suryadev_video_browser_probe.py").read_text(encoding="utf-8")
        sweep=(root/"suryadev_video_speed_sweep.py").read_text(encoding="utf-8")
        adapter=(root.parents[1]/"scripts"/"SURYDEV_VIDEO_LEARNING_ADAPTER.py").read_text(
            encoding="utf-8")
        self.assertIn("self.headless = True",media)
        self.assertIn("profile,channel=channel,headless=True",probe)
        self.assertIn("profile,channel=channel,headless=True",sweep)
        self.assertIn("workspace, source_url, channel=browser_channel, headless=True",adapter)
        html=(root/"dashboard.html").read_text(encoding="utf-8")
        js=(root/"dashboard-ai-learner.js").read_text(encoding="utf-8")
        for id_ in ("ai-learner","ai-tab-youtube","ai-tab-pdf","ai-tab-website","ai-tab-book"):
            self.assertIn('id="'+id_+'"',html)
        self.assertNotIn("window.open(",js)
        self.assertNotIn("target='_blank'",html)
        self.assertIn("https://www.youtube-nocookie.com/embed/",js)

    def test_all_canonical_browser_entrypoints_have_explicit_chromium(self):
        root=Path(__file__).resolve().parents[1]
        docs={
            "suryadev_garudanetra.py": "channel=browser_channel()",
            "suryadev_garudanetra_media.py": "channel=self.channel",
            "suryadev_video_browser_probe.py": "channel=channel",
            "suryadev_video_speed_sweep.py": "channel=channel",
            "suryadev_browser_preflight.py": "channel=browser_channel()",
        }
        for name,needle in docs.items():
            with self.subTest(name=name):
                content=(root/name).read_text(encoding="utf-8")
                self.assertIn(needle,content)
        # Live media refuses a branded channel at construction, and both
        # diagnostic CLIs accept only Chromium through CHANNELS.


class MockPage:
    def goto(self,url):
        self.url=url
    def evaluate(self,script):
        assert script==CODEC_PROBE_JS
        return {"html_video":True,"h264_aac":"","vp9_opus":"probably",
                "vp8_vorbis":"probably"}


class MockBrowser:
    def __init__(self):
        self.closed=False
        self.version="test-chromium-1"
        self.page=MockPage()
    def new_page(self):
        return self.page
    def close(self):
        self.closed=True


class MockFactory:
    def __init__(self):
        self.kwargs=None
        self.browser=MockBrowser()
    def launch(self,**kwargs):
        self.kwargs=kwargs
        return self.browser


class BrowserPreflightTests(unittest.TestCase):
    def test_offline_codec_preflight_no_chrome_or_network(self):
        factory=MockFactory()
        row=_probe(factory,{"cpu_percent":10,"ram_percent":40})
        self.assertEqual(factory.kwargs,{"channel":"chromium","headless":True})
        self.assertTrue(factory.browser.closed)
        self.assertTrue(factory.browser.page.url.startswith("data:text/html,"))
        self.assertEqual(row["source_requests"],0)
        self.assertEqual(row["codec_can_play_type"]["vp9_opus"],"probably")
        self.assertFalse(row["media_playback_verified"])
        self.assertFalse(row["learning_verified"])


if __name__=="__main__":
    unittest.main()
