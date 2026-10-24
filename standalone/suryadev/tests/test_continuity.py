"""Read-only fallback/approved-source continuity regression and installer contracts."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_continuity import (
    OFFICIAL_TECH_FEEDS, OFFICIAL_TECH_URLS, OFFICIAL_TECH_HOSTS,
    ContinuityFeeder, activate_official_pack,
)
from suryadev_liveops import operations_snapshot


def plan(urls=None, feeds=None, hosts=None, limit=10):
    return {
        "approved_urls": urls or [],
        "approved_feeds": feeds or [],
        "allowed_source_hosts": hosts or ["example.org"],
        "max_new_per_cycle": limit,
        "max_queued": 50,
    }


class OfficialContinuityPackTests(unittest.TestCase):
    def test_opt_in_pack_preserves_original_sources_budgets_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            active = Path(root) / "learning-plan.json"
            existing = plan(["https://example.org/original"],
                            ["https://example.org/feed.xml"],["example.org"],limit=7)
            existing["description"] = "Do not replace my research topic"
            active.write_text(json.dumps(existing),encoding="utf-8")
            first = activate_official_pack(root)
            self.assertEqual(first["status"],"activated")
            self.assertTrue(Path(first["backup"]).is_file())
            self.assertEqual(json.loads(Path(first["backup"]).read_text()),existing)
            merged=json.loads(active.read_text())
            self.assertEqual(merged["description"],existing["description"])
            self.assertEqual(merged["max_new_per_cycle"],7)
            self.assertEqual(merged["approved_urls"][0],"https://example.org/original")
            self.assertEqual(merged["approved_feeds"][0],"https://example.org/feed.xml")
            self.assertTrue(set(OFFICIAL_TECH_URLS).issubset(merged["approved_urls"]))
            self.assertTrue(set(OFFICIAL_TECH_FEEDS).issubset(merged["approved_feeds"]))
            self.assertTrue(set(OFFICIAL_TECH_HOSTS).issubset(merged["allowed_source_hosts"]))
            second = activate_official_pack(root)
            self.assertEqual(second["status"],"unchanged")
            self.assertEqual(json.loads(active.read_text()),merged)

    def test_invalid_existing_plan_is_never_modified(self):
        with tempfile.TemporaryDirectory() as root:
            active=Path(root)/"learning-plan.json"
            active.write_text('{"approved_urls": "not-an-array"}',encoding="utf-8")
            original=active.read_bytes()
            with self.assertRaises(ValueError):
                activate_official_pack(root)
            self.assertEqual(active.read_bytes(),original)

    def test_opt_in_can_create_new_plan_without_installing_or_starting_worker(self):
        with tempfile.TemporaryDirectory() as root:
            result=activate_official_pack(root)
            self.assertEqual(result["status"],"activated")
            self.assertEqual(result["approved_urls"],len(OFFICIAL_TECH_URLS))
            self.assertEqual(result["approved_feeds"],len(OFFICIAL_TECH_FEEDS))
            self.assertFalse((Path(root)/"suryadev.sqlite3").exists())


class ContinuityRefillTests(unittest.TestCase):
    def test_approved_feed_hot_reload_idempotency_and_no_unapproved_hosts(self):
        with tempfile.TemporaryDirectory() as root:
            active=Path(root)/"learning-plan.json"
            active.write_text(json.dumps(plan(
                ["https://example.org/a"],[],["example.org"])),encoding="utf-8")
            now=[1000.0]
            feed=b"<rss><channel><item><link>https://example.org/b</link></item><item><link>https://bad.example/sneaky</link></item></channel></rss>"
            lib=Library(root)
            try:
                adapter=ContinuityFeeder(root,active,refill_seconds=60,
                                         fetcher=lambda _:feed,clock=lambda:now[0])
                with patch("suryadev.validate_url",return_value=None):
                    result=adapter.tick(lib,youtube_blocked=True)
                    self.assertEqual(result["added_total"],1)
                    self.assertTrue(result["youtube_blocked"])
                    self.assertFalse(result["youtube_video_equivalence_claimed"])
                    self.assertIsNone(adapter.tick(lib))
                    # An operator has opted into a new live feed while the
                    # worker is running; no mission restart is necessary.
                    active.write_text(json.dumps(plan(
                        ["https://example.org/a"],
                        ["https://example.org/feed.xml"],["example.org"])),encoding="utf-8")
                    now[0]+=61
                    again=adapter.tick(lib,youtube_blocked=True)
                self.assertEqual(again["added_total"],1)
                self.assertEqual(lib.stats()["queued"],2)
                self.assertEqual(lib.db.execute(
                    "SELECT COUNT(*) FROM jobs WHERE url LIKE '%bad.example%'").fetchone()[0],0)
                status=operations_snapshot(lib.db,root)
                self.assertTrue(status["continuity"]["active"])
                self.assertEqual(status["continuity"]["refresh_count"],2)
                adapter.stop()
                self.assertFalse(operations_snapshot(lib.db,root)["continuity"]["active"])
            finally:
                lib.db.close()

    def test_feed_failure_does_not_crash_worker_or_claim_complete_video(self):
        with tempfile.TemporaryDirectory() as root:
            active=Path(root)/"learning-plan.json"
            active.write_text(json.dumps(plan(
                ["https://example.org/a"],
                ["https://example.org/rss.xml"],["example.org"])),encoding="utf-8")
            lib=Library(root)
            try:
                def broken_feed(_):
                    raise OSError("Publisher feed temporarily unavailable")
                adapter=ContinuityFeeder(root,active,refill_seconds=300,
                                         fetcher=broken_feed)
                with patch("suryadev.validate_url",return_value=None):
                    result=adapter.tick(lib,youtube_blocked=True)
                self.assertEqual(result["added_total"],1)
                self.assertEqual(result["feed_error_count"],1)
                self.assertEqual(lib.stats()["queued"],1)
                self.assertFalse(result["youtube_video_equivalence_claimed"])
            finally:
                lib.db.close()

    def test_worker_with_explicit_plan_refills_queue_before_processing(self):
        import suryadev_extras
        with tempfile.TemporaryDirectory() as root:
            active=Path(root)/"learning-plan.json"
            active.write_text(json.dumps(plan(
                ["https://example.org/source"],[],["example.org"])),encoding="utf-8")
            lib=Library(root)
            observed=[]
            class FakeAdaptive:
                youtube_access={"state":"rate_limited"}
                def __init__(self,*a,**kw): pass
                futures = {}
                def __enter__(self): return self
                def __exit__(self,*_): pass
                def pump(self, *, admit_new=True):
                    observed.append(lib.stats().get("queued",0))
                    raise KeyboardInterrupt()
            try:
                with patch("suryadev.validate_url",return_value=None),patch.object(
                    suryadev_extras,"AdaptiveResearchWorkers",FakeAdaptive):
                    with self.assertRaises(KeyboardInterrupt):
                        suryadev_extras.work_loop(
                            lib,10,False,"unused",plan_path=active,refill_minutes=1)
                self.assertEqual(observed,[1])
                self.assertEqual(lib.stats()["queued"],1)
                state=operations_snapshot(lib.db,root)
                self.assertFalse(state["continuity"]["active"])
            finally:
                lib.db.close()

    def test_dashboard_assets_and_release_ship_real_continuity(self):
        folder=Path(__file__).resolve().parents[1]
        html=(folder/"dashboard.html").read_text(encoding="utf-8")
        js=(folder/"dashboard-garudanetra.js").read_text(encoding="utf-8")
        installer=(folder/"install-windows.ps1").read_text(encoding="utf-8")
        self.assertIn('id="netra-continuity-status"',html)
        self.assertIn('const continuity = data.continuity',js)
        self.assertIn('youtube_video_equivalence_claimed', (folder/"suryadev_continuity.py").read_text())
        self.assertIn("'suryadev_continuity.py'",installer)
        launcher=(folder/"start-continuous-learning.ps1").read_text(encoding="utf-8")
        self.assertIn("'start-continuous-learning.ps1'",installer)
        self.assertIn('activate-official-tech',launcher)
        self.assertIn('"--plan", $plan',launcher)
        self.assertIn('& $Python @workerArgs',launcher)
        self.assertNotIn('& $Python @args',launcher)
        self.assertNotIn('retry-failed',launcher)



if __name__ == "__main__":
    unittest.main()
