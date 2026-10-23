"""Automation must require bounded owner source approval and one active worker."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_dashboard_worker import DashboardWorkerControl
from suryadev_video_review import VideoReview


def plan(root, urls):
    path = Path(root)/"learning-plan.json"
    path.write_text(json.dumps({"approved_urls":urls, "approved_feeds":[],
         "allowed_source_hosts":["www.youtube.com","www.python.org"],
         "max_new_per_cycle":5,"max_queued":10}),encoding="utf-8")
    return path


class DashboardAutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = Path(__file__).resolve().parents[1]

    def test_worker_is_user_activated_not_a_service(self):
        ctl = DashboardWorkerControl(self.root, self.folder)
        self.assertFalse(ctl.snapshot()["managed_running"])
        self.assertFalse(ctl.snapshot()["plan_exists"])
        self.assertFalse((self.root/"dashboard-worker.log").exists())

    def test_start_requires_selected_safe_model(self):
        ctl = DashboardWorkerControl(self.root, self.folder)
        with self.assertRaises(ValueError):
            ctl.start(model="any-arbitrary-program")
        self.assertFalse((self.root/"dashboard-worker.log").exists())

    def test_managed_worker_is_a_real_subprocess_and_never_duplicated(self):
        class FakeProcess:
            pid = 90001
            def __init__(self):
                self.signals=[]
            def poll(self):
                return None
            def send_signal(self, sig):
                self.signals.append(sig)
        fake=FakeProcess()
        ctl=DashboardWorkerControl(self.root,self.folder)
        try:
            with patch("suryadev_dashboard_worker.subprocess.Popen",return_value=fake) as launch:
                first=ctl.start(model="qwen3.5:2b")
                self.assertEqual(first["status"],"STARTING")
                self.assertFalse(first["approved_plan_loaded"])
                self.assertEqual(launch.call_args.args[0][-4:],
                    ["--interval","30","--model","qwen3.5:2b"])
                with self.assertRaisesRegex(RuntimeError,"already running"):
                    ctl.start(model="qwen3.5:2b")
                self.assertTrue(ctl.snapshot()["managed_running"])
                stop=ctl.stop()
                self.assertEqual(stop["status"],"STOPPING")
                self.assertEqual(len(fake.signals),1)
        finally:
            ctl.close()

    def test_video_auto_is_explicit_opt_in_and_exact_urls_only(self):
        approved="https://www.youtube.com/watch?v=mgBpcQRDtl0"
        unrelated="https://www.python.org/about/"
        plan(self.root,[approved,unrelated])
        v=VideoReview(self.root,self.folder)
        self.assertFalse(v.auto_enabled())
        self.assertEqual(v.set_auto(True)["auto_enabled"],True)
        self.assertTrue(v.auto_enabled())
        with patch.object(v,"run_job",return_value={"status":"RUNNING"}) as run:
            v._auto_tick()
            self.assertEqual(run.call_count,1)
            self.assertEqual(run.call_args.args[1],True)
            job_id=run.call_args.args[0]
            job=json.loads(v._path(job_id).read_text(encoding="utf-8"))
            self.assertEqual(job["target"],approved)
            self.assertTrue(job["constraints"]["adaptive_playback"])
            v._auto_tick()
            self.assertEqual(run.call_count,1,"Never automatically replay the same source")
        self.assertEqual(v.set_auto(False)["auto_enabled"],False)
        self.assertFalse(v.auto_enabled())

    def test_approved_video_source_is_persisted_once_without_launch(self):
        url="https://www.youtube.com/watch?v=mgBpcQRDtl0"
        review=VideoReview(self.root,self.folder)
        state=review.approve_source(url)
        self.assertEqual(state["status"],"approved")
        self.assertFalse(review.auto_enabled())
        saved=json.loads((self.root/"learning-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["approved_urls"],[url])
        self.assertIn("www.youtube.com",saved["allowed_source_hosts"])
        self.assertEqual(review.approve_source(url)["status"],"already_approved")
        self.assertEqual(len(list(self.root.glob("learning-plan.before-video-*.json"))),0)
        self.assertFalse((self.root/"video-review"/"approved-inbox").exists())

    def test_video_approval_preserves_original_plan_and_backup(self):
        url="https://www.youtube.com/watch?v=mgBpcQRDtl0"
        existing="https://www.python.org/about/"
        plan(self.root,[existing])
        review=VideoReview(self.root,self.folder)
        review.approve_source(url)
        updated=json.loads((self.root/"learning-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(updated["approved_urls"],[existing,url])
        backups=list(self.root.glob("learning-plan.before-video-*.json"))
        self.assertEqual(len(backups),1)
        original=json.loads(backups[0].read_text(encoding="utf-8"))
        self.assertEqual(original["approved_urls"],[existing])
        for invalid in ("https://127.0.0.1/watch?v=x",
                        "http://www.youtube.com/watch?v=x",
                        "https://www.youtube.com/"):
            with self.subTest(url=invalid):
                with self.assertRaises(ValueError):
                    review.approve_source(invalid)
        self.assertEqual(json.loads((self.root/"learning-plan.json").read_text(
            encoding="utf-8"))["approved_urls"],[existing,url])

    def test_video_auto_rejects_missing_approval_and_starts_no_work(self):
        v=VideoReview(self.root,self.folder)
        with self.assertRaises((ValueError,OSError)):
            v.set_auto(True)
        plan(self.root,["https://www.python.org/about/"])
        with self.assertRaisesRegex(ValueError,"YouTube"):
            v.set_auto(True)
        self.assertFalse(v.auto_enabled())


if __name__ == "__main__":
    unittest.main()
