"""Adaptive source-concurrency and Garudanetra browser safety tests."""
import asyncio
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_garudanetra import GarudanetraLite
from suryadev_parallel import (plan_capacity, AdaptiveResearchWorkers,
    youtube_rate_limited, record_youtube_rate_limit, youtube_access)
from suryadev_liveops import operations_snapshot, atomic_json


def healthy(**overrides):
    data = {
        "available":True,"cpu_percent":10.0,"ram_percent":32.0,
        "ram_used_gb":5.0,"ram_total_gb":16.0,
        "disk_percent":28.0,"disk_free_gb":120.0,
        "gpu":{"available":False},
    }
    data.update(overrides)
    return data


class AdaptiveCapacityTests(unittest.TestCase):
    def test_missing_or_overloaded_metrics_never_admit_new_work(self):
        self.assertEqual(plan_capacity({"available":False})["max_total"], 0)
        for readings in (
            healthy(cpu_percent=92),
            healthy(ram_percent=90),
            healthy(disk_percent=90),
            healthy(disk_free_gb=1.9),
            healthy(ram_total_gb=8,ram_used_gb=7),
            healthy(gpu={"available":True,"usage_percent":96,"vram_percent":10}),
        ):
            with self.subTest(readings=readings):
                self.assertEqual(plan_capacity(readings, logical_cpus=8)["max_total"],0)

    def test_greater_hardware_headroom_allows_more_website_video_pdf_work(self):
        large = plan_capacity(healthy(), logical_cpus=12)
        self.assertTrue(large["safe"])
        self.assertGreaterEqual(large["max_total"],3)
        self.assertGreaterEqual(large["limits"]["website"],2)
        self.assertGreaterEqual(large["limits"]["youtube"],1)
        self.assertGreaterEqual(large["limits"]["pdf"],1)
        smaller = plan_capacity(healthy(cpu_percent=75), logical_cpus=12)
        self.assertEqual(smaller["max_total"],1)
        self.assertEqual(smaller["local_model_concurrency"],1)

    def test_no_unbounded_tab_counts(self):
        with self.assertRaises(ValueError):
            GarudanetraLite("unused", max_tabs=5)
        with self.assertRaises(ValueError):
            GarudanetraLite("unused", max_tabs=0)


class YouTubeRateLimitSafetyTests(unittest.TestCase):
    def test_429_classification_and_bounded_persistent_cooldown(self):
        self.assertTrue(youtube_rate_limited("HTTP Error 429: Too Many Requests"))
        self.assertFalse(youtube_rate_limited("Video unavailable"))
        with tempfile.TemporaryDirectory() as root:
            now=time.time()
            self.assertEqual(youtube_access(root,now)["state"],"ready")
            record_youtube_rate_limit(root,now=now)
            self.assertEqual(youtube_access(root,now+1)["state"],"rate_limited")
            self.assertEqual(youtube_access(root,now+3601)["state"],"ready")
            atomic_json(root,"youtube-access-state.json",
                        {"cooldown_until": float("inf")})
            self.assertEqual(youtube_access(root,now)["state"],"ready")

    def test_no_youtube_worker_launch_during_rate_limit_but_website_still_runs(self):
        with tempfile.TemporaryDirectory() as root:
            lib = Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    lib.add("https://www.youtube.com/watch?v=abcdefghijk")
                    lib.add("https://example.com/reading")
                record_youtube_rate_limit(root)
                FakeGarudanetra.visits = []
                with AdaptiveResearchWorkers(root, use_ollama=False,
                         browser_factory=FakeGarudanetra, check_seconds=10) as pool:
                    with patch("suryadev_parallel.os.cpu_count",return_value=8):
                        result=pool.pump(telemetry=healthy())
                        self.assertEqual(result["capacity"]["limits"]["youtube"],0)
                        self.assertNotIn("youtube",result["capacity"]["launched_this_cycle"])
                        self.assertIn("website",result["capacity"]["launched_this_cycle"])
                        pool.pool.shutdown(wait=True)
                        pool._reap()
                self.assertEqual(lib.db.execute(
                    "SELECT status FROM jobs WHERE url LIKE '%youtube%'").fetchone()[0],
                    "queued")
                self.assertEqual(lib.db.execute(
                    "SELECT status FROM jobs WHERE url LIKE '%reading%'").fetchone()[0],
                    "done")
            finally:
                lib.db.close()

    def test_observed_youtube_429_cools_following_queued_videos(self):
        with tempfile.TemporaryDirectory() as root:
            lib=Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    lib.add("https://www.youtube.com/watch?v=abcdefghijk")
                    lib.add("https://www.youtube.com/watch?v=123456789ab")
                def fail(_url):
                    raise RuntimeError("HTTP Error 429: Too Many Requests")
                with patch("suryadev_ingest.ingest_youtube",side_effect=fail):
                    with AdaptiveResearchWorkers(root, use_ollama=False,check_seconds=10) as pool:
                        with patch("suryadev_parallel.os.cpu_count",return_value=8):
                            first=pool.pump(telemetry=healthy())
                            self.assertEqual(first["capacity"]["limits"]["youtube"],1)
                            self.assertEqual(first["capacity"]["launched_this_cycle"],["youtube"])
                            for _ in range(70):
                                if any(f.done() for f in pool.futures):
                                    break
                                time.sleep(.03)
                            again=pool.pump(telemetry=healthy())
                            self.assertEqual(again["capacity"]["limits"]["youtube"],0)
                            self.assertEqual(again["capacity"]["youtube_access"]["state"],
                                             "rate_limited")
                            self.assertEqual(again["capacity"]["launched_this_cycle"],[])
                self.assertEqual(lib.stats()["failed"],1)
                self.assertEqual(lib.stats()["queued"],1)
                with AdaptiveResearchWorkers(root,use_ollama=False) as replacement:
                    persisted = replacement.pump(telemetry=healthy())["capacity"]
                    self.assertEqual(persisted["limits"]["youtube"],0)
            finally:
                lib.db.close()


class FakeRoute:
    class Request:
        def __init__(self, url, resource_type):
            self.url = url
            self.resource_type = resource_type
    def __init__(self,url,type_="document"):
        self.request=self.Request(url,type_)
        self.action=None
    async def abort(self):
        self.action="blocked"
    async def continue_(self):
        self.action="allowed"


class GarudanetraPolicyTests(unittest.TestCase):
    def test_blocks_private_urls_outside_approved_host_and_heavy_assets(self):
        engine = GarudanetraLite("unused")
        engine._allowed_hosts.add("www.python.org")
        good = FakeRoute("https://www.python.org/about/")
        external = FakeRoute("https://tracker.example.net/track")
        private = FakeRoute("http://127.0.0.1:8766/health")
        media = FakeRoute("https://www.python.org/video.mp4","media")
        image = FakeRoute("https://www.python.org/photo.jpg","image")
        async def perform():
            for item in (good,external,private,media,image):
                await engine._route(item)
        asyncio.run(perform())
        self.assertEqual(good.action,"allowed")
        for item in (external,private,media,image):
            self.assertEqual(item.action,"blocked")

    def test_status_never_pretends_external_core_is_paired(self):
        with tempfile.TemporaryDirectory() as root:
            engine = GarudanetraLite(root)
            engine._status("stopped")
            data = json.loads((Path(root)/"garudanetra-runtime.json").read_text())
            self.assertFalse(data["process_owns_browser"])
            self.assertEqual(data["open_tabs"],0)
            self.assertTrue(data["standalone_adapter"])


class FakeGarudanetra:
    started = 0
    visits = []
    def __init__(self, root, max_tabs=4):
        self._tabs = {}
    def start(self):
        type(self).started += 1
        return self
    def render(self,url,job_id=None):
        type(self).visits.append((url,job_id))
        time.sleep(0.08)
        return "Garudanetra test page", "Rendered visible body text for testing " + str(job_id), {
            "kind":"website", "coverage_status":"garudanetra_rendered_text_unverified",
            "browser_tab_opened":True,
            "full_rendered_page_verified":False,
        }
    def stop(self):
        pass


class ParallelWorkerIntegration(unittest.TestCase):
    def test_auto_slots_process_multiple_real_sqlite_jobs(self):
        with tempfile.TemporaryDirectory() as root:
            lib = Library(root)
            try:
                with patch("suryadev.validate_url", return_value=None):
                    first = lib.add("https://example.com/a")
                    second = lib.add("https://example.com/b")
                FakeGarudanetra.started = 0
                FakeGarudanetra.visits = []
                with AdaptiveResearchWorkers(root,use_ollama=False,
                        browser_factory=FakeGarudanetra,check_seconds=10) as workers:
                    with patch("suryadev_parallel.os.cpu_count",return_value=12):
                        launched = workers.pump(telemetry=healthy())
                        self.assertGreaterEqual(len(launched["capacity"]["launched_this_cycle"]),2)
                        until=time.time()+8
                        while time.time()<until and len(FakeGarudanetra.visits)<2:
                            time.sleep(.05)
                        until=time.time()+8
                        while time.time()<until:
                            finished=workers.pump(telemetry=healthy())["finished"]
                            if workers.last_result and not workers.futures:
                                break
                            time.sleep(.05)
                    self.assertEqual(FakeGarudanetra.started,1)
                    self.assertEqual(len(FakeGarudanetra.visits),2)
                self.assertEqual(lib.stats().get("done"),2)
                self.assertEqual(lib.db.execute("SELECT count(*) FROM job_provenance").fetchone()[0],2)
                summary=operations_snapshot(lib.db,root)
                self.assertEqual(summary["processing"]["website"]["running"],0)
                self.assertEqual(summary["capacity"]["state"],"stopped")
            finally:
                lib.db.close()

    def test_unavailable_psutil_leaves_queue_intact(self):
        with tempfile.TemporaryDirectory() as root:
            lib=Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    lib.add("https://example.com/a")
                with AdaptiveResearchWorkers(root,use_ollama=False,
                         browser_factory=FakeGarudanetra) as workers:
                    before=FakeGarudanetra.started
                    result=workers.pump(telemetry={"available":False})
                    self.assertEqual(result["capacity"]["active_total"],0)
                    self.assertEqual(FakeGarudanetra.started,before)
                self.assertEqual(lib.stats().get("queued"),1)
            finally:
                lib.db.close()


class DashboardV6Contract(unittest.TestCase):
    def test_all_three_source_lanes_and_real_browser_tabs_present(self):
        folder=Path(__file__).resolve().parents[1]
        html=(folder/"dashboard.html").read_text(encoding="utf-8")
        js=(folder/"dashboard-garudanetra.js").read_text(encoding="utf-8")
        for name in (
            "garudanetra", "netra-web-running","netra-video-running",
            "netra-pdf-running","netra-web-capacity","netra-video-capacity",
            "netra-pdf-capacity","netra-web-tabs","netra-workspace-tabs",
            "netra-total-capacity",
        ):
            self.assertIn('id="'+name+'"',html)
        self.assertIn("data.processing",js)
        self.assertIn("data.garudanetra",js)
        self.assertIn("data.capacity",js)
        self.assertIn("openDetail(job.id)",js)
        self.assertIn('src="/dashboard-garudanetra.js"',html)
        self.assertIn('href="/dashboard-garudanetra.css"',html)
        self.assertIn('id="netra-youtube-access"', html)
        self.assertIn('ytAccess.state === "rate_limited"',js)
        self.assertIn('Failed jobs require manual retry.',js)
        assets=(folder/"suryadev_extras.py").read_text(encoding="utf-8")
        self.assertIn('"/dashboard-garudanetra.js": "dashboard-garudanetra.js"', assets)
        self.assertIn('"/dashboard-garudanetra.css": "dashboard-garudanetra.css"', assets)


if __name__ == "__main__":
    unittest.main()
