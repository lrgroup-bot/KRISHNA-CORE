"""AI Learner player may only embed a configured local service in-page.

No FreeTube.exe launches; no remote arbitrary iframe, unapproved lesson,
browser login, transcript spoofing or automatic evidence promotion.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from suryadev_ai_player import player_config, local_invidious_origin

ROOT=Path(__file__).resolve().parents[1]


class InPagePlayerSafety(unittest.TestCase):
    def test_disabled_without_explicit_owner_configuration(self):
        result=player_config({})
        self.assertEqual(result["schema"],"suryadev.ai-learner-player.v1")
        self.assertFalse(result["configured"])
        self.assertEqual(result["origin"],"")
        self.assertFalse(result["ad_free_claim_verified"])
        self.assertFalse(result["study_evidence_verified"])
        self.assertFalse(result["new_browser_window"])

    def test_configured_loopback_is_not_claimed_operational_or_ad_free(self):
        for inp,normalized in (
            ("http://127.0.0.1:3000","http://127.0.0.1:3000"),
            ("http://localhost:3030/","http://127.0.0.1:3030"),
            ("http://[::1]:3000","http://127.0.0.1:3000"),
        ):
            with self.subTest(inp=inp):
                self.assertEqual(local_invidious_origin(inp),normalized)
                config=player_config({"SURYADEV_LOCAL_INVIDIOUS_ORIGIN":inp})
                self.assertTrue(config["configured"])
                self.assertEqual(config["provider"],"invidious-local")
                self.assertEqual(config["origin"],normalized)
                self.assertFalse(config["service_reachability_verified"])
                self.assertFalse(config["ad_free_claim_verified"])
                self.assertFalse(config["source_observation_verified"])
                self.assertFalse(config["study_evidence_verified"])

    def test_rejects_remote_url_creds_and_paths(self):
        invalid=(
            "https://invidious.example","http://invidious.example:3000",
            "http://192.168.0.109:3000","http://127.0.0.1",
            "http://127.0.0.1:80","http://user:pass@127.0.0.1:3000",
            "http://localhost:3000/a","http://localhost:3000?x=1",
            "http://localhost:3000/#token","file:///etc/passwd",
            "javascript:alert(1)","http://127.0.0.1:99999",
        )
        for origin in invalid:
            with self.subTest(origin=origin),self.assertRaises(ValueError):
                local_invidious_origin(origin)
            self.assertFalse(player_config(
                {"SURYADEV_LOCAL_INVIDIOUS_ORIGIN":origin})["configured"])

    def test_dashboard_csp_defaults_closed_and_only_allows_opted_in_loopback(self):
        from io import BytesIO
        from unittest.mock import patch
        from suryadev_extras import _send_http_response

        class FakeHandler:
            def __init__(self):
                self.headers = {}
                self.wfile = BytesIO()
            def send_response(self, status):
                self.status = status
            def send_header(self, key, value):
                self.headers[key.lower()] = value
            def end_headers(self):
                pass

        examples = (
            ({}, "frame-src 'none'"),
            ({"SURYADEV_LOCAL_INVIDIOUS_ORIGIN":"http://localhost:3000"},
             "frame-src http://127.0.0.1:3000"),
            ({"SURYADEV_LOCAL_INVIDIOUS_ORIGIN":"http://public.example:3000"},
             "frame-src 'none'"),
        )
        for env, expected in examples:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                handler = FakeHandler()
                self.assertTrue(_send_http_response(handler, 200, "text/plain", b"ok"))
                policy = handler.headers["content-security-policy"]
                self.assertIn(expected, policy)
                self.assertNotIn("youtube-nocookie.com", policy)
                self.assertEqual(handler.wfile.getvalue(), b"ok")

    def test_canonical_ai_learner_page_is_single_window_four_lanes(self):
        html=(ROOT/"dashboard.html").read_text(encoding="utf-8")
        js=(ROOT/"dashboard-ai-learner.js").read_text(encoding="utf-8")
        routes=(ROOT/"dashboard-pages.js").read_text(encoding="utf-8")
        backend=(ROOT/"suryadev_extras.py").read_text(encoding="utf-8")
        self.assertEqual(html.count('href="#ai-learner"'),1)
        self.assertIn('key:"ai-learner"',routes)
        for key in ("youtube","pdf","website","book"):
            self.assertEqual(html.count('id="ai-tab-'+key+'"'),1)
        self.assertIn('/api/ai-learner/player',js)
        self.assertIn('/api/ai-learner/player',backend)
        self.assertIn('"/embed/"+id',js)
        self.assertNotIn('www.youtube-nocookie.com/embed/',js)
        self.assertNotIn("window.open(",js)
        self.assertNotIn("new Window(",js)
        self.assertIn("frame.src=origin+",js)
        self.assertIn("frame.setAttribute(\"sandbox\"",js)
        self.assertIn('previewJobId=job.job_id',js)
        self.assertIn('source_currently_approved===true',js)

if __name__=="__main__":
    unittest.main()
