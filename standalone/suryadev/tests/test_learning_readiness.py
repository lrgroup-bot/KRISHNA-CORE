"""AI Learner readiness reports only grounded, time-bounded runtime state."""
import json
import tempfile
import time
import unittest
from pathlib import Path

from suryadev_learning_readiness import snapshot
from suryadev_trial_limits import video_job_id

VIDEOS=[
    "https://www.youtube.com/watch?v=mgBpcQRDtl0",
    "https://www.youtube.com/watch?v=abcdefghijk",
    "https://www.youtube.com/watch?v=123456789ab",
    "https://www.youtube.com/watch?v=VZ5LU8vHT0s",
]


class ReadinessTests(unittest.TestCase):
    def test_real_blockers_and_stale_activity(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            app=root/"app"
            app.mkdir()
            (root/"learning-plan.json").write_text(json.dumps({
                "approved_urls":VIDEOS,
                "approved_feeds":[],
                "allowed_source_hosts":["www.youtube.com"]
            }),encoding="utf-8")
            (root/"video-auto.json").write_text(json.dumps({
                "schema":"suryadev.video-auto.v1","enabled":True
            }),encoding="utf-8")
            (root/"video-trial-selection.json").write_text(json.dumps({
                "schema":"suryadev.video-trial-selection.v1",
                "target":3,"job_ids":[]
            }),encoding="utf-8")
            (root/"video-observer-attempts.json").write_text(json.dumps({
                "schema":"suryadev.video-attempts.v1",
                "job_ids":[video_job_id(v) for v in VIDEOS[:3]]
            }),encoding="utf-8")
            (root/"book-plan.json").write_text(json.dumps({
                "books":[{"path":"placeholder"} for _ in range(5)]
            }),encoding="utf-8")
            (root/"book-concurrent-runtime.json").write_text(json.dumps({
                "active":1,"updated_at":100.0
            }),encoding="utf-8")
            s=snapshot(root,app,control={"managed_running":False,
                       "external_worker_active":False},now=1000.0)
            self.assertEqual(s["approved_videos"],4)
            self.assertEqual(s["previously_attempted_videos"],3)
            self.assertEqual(s["unattempted_approved_videos"],1)
            self.assertEqual(s["selected_videos"],0)
            self.assertTrue(s["selection_empty_recovery_possible"])
            self.assertEqual(s["approved_books"],5)
            self.assertFalse(s["book_runtime_fresh"])
            self.assertIsNone(s["reported_active_books"])
            self.assertTrue(any("No verified" in x for x in s["reasons"]))
            self.assertTrue(any("empty" in x for x in s["reasons"]))

    def test_book_idle_explains_measured_capacity_and_checkpoint_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            app=root/"app"
            app.mkdir()
            (root/"book-plan.json").write_text(json.dumps({
                "books":[{"path":"pinned-sample.pdf"}]}),encoding="utf-8")
            (root/"book-concurrent-runtime.json").write_text(json.dumps({
                "active":0,"updated_at":998.0}),encoding="utf-8")
            (root/"capacity-runtime.json").write_text(json.dumps({
                "max_total":2,"reserved_book_slots":0,
                "sample_time":998.0,"queued":{}}),encoding="utf-8")
            (root/"book-continuity-runtime.json").write_text(json.dumps({
                "state":"book_paused_error","updated_at":997.0,
                "error":"TimeoutError: local inference did not finish"}),encoding="utf-8")
            result=snapshot(root,app,control={
                "managed_running":True, "managed_model":"qwen3.5:2b",
                "learning_role":"local_inference"},now=1000.0)
            self.assertEqual(result["worker_model"],"qwen3.5:2b")
            self.assertEqual(result["learning_role"],"local_inference")
            self.assertEqual(result["admitted_slots"],2)
            self.assertEqual(result["reserved_book_slots"],0)
            self.assertEqual(result["book_last_state"],"book_paused_error")
            self.assertIn("TimeoutError",result["book_last_error"])
            self.assertTrue(any("No book capacity" in x for x in result["reasons"]))
            self.assertTrue(any("checkpoint paused" in x for x in result["reasons"]))

    def test_external_lock_and_recent_book_receipt_are_not_managed_process(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            app=root/"app"
            app.mkdir()
            (root/"book-concurrent-runtime.json").write_text(json.dumps({
                "active":1,"updated_at":995.0}),encoding="utf-8")
            s=snapshot(root,app,control={"managed_running":False,
                        "external_worker_active":True},now=1000.0)
            self.assertTrue(s["worker_external_lock"])
            self.assertFalse(s["worker_managed_running"])
            self.assertTrue(s["book_runtime_fresh"])
            self.assertEqual(s["reported_active_books"],1)
            self.assertFalse(any("No verified managed" in x for x in s["reasons"]))


if __name__=="__main__":
    unittest.main()
