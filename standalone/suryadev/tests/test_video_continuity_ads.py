"""Video observation scheduling and optional Playwright MV3 policy; zero network."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from suryadev_video_review import VideoReview

ADAPTER = Path(__file__).resolve().parents[3] / "scripts" / "SURYDEV_VIDEO_LEARNING_ADAPTER.py"
spec = importlib.util.spec_from_file_location("verified_suryadev_video_adapter", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class VideoGuardTests(unittest.TestCase):
    def test_real_video_time_progress_resets_stall(self):
        guard=adapter.VideoProgressGuard(100,stalled_seconds=30)
        self.assertIsNone(guard.tick({"seconds":1.0},now=110))
        self.assertIsNone(guard.tick({"seconds":3.0},now=129))
        self.assertIsNone(guard.tick({"seconds":3.0},now=158))
        self.assertEqual(guard.tick({"seconds":3.0},now=160),
                         "content_playback_stalled")

    def test_ads_do_not_count_as_lecture_progress(self):
        guard=adapter.VideoProgressGuard(100,stalled_seconds=30,ad_wait_seconds=60)
        self.assertIsNone(guard.tick({"seconds":10},now=110))
        self.assertIsNone(guard.tick({"ad_showing":True,"seconds":11},now=111))
        self.assertIsNone(guard.tick({"ad_showing":True,"seconds":47},now=165))
        self.assertEqual(guard.tick({"ad_showing":True,"seconds":75},now=171),
                         "advertisement_wait_limit")
        self.assertEqual(guard.ad_events,1)
        self.assertEqual(guard.last_content_seconds,10)
        self.assertIsNone(guard.tick({"ad_showing":False,"seconds":0},now=172))
        self.assertGreater(guard.ad_wall_seconds,0)

    def test_missing_playback_stalls_instead_of_watching_forever(self):
        guard=adapter.VideoProgressGuard(0,stalled_seconds=30)
        self.assertIsNone(guard.tick({},now=15))
        self.assertEqual(guard.tick({},now=30),"content_playback_stalled")


class ChromiumFilterTests(unittest.TestCase):
    def test_opt_in_only(self):
        with patch.dict(os.environ,{"SURYADEV_UBOL_EXTENSION_DIR":""}):
            self.assertFalse(adapter._chromium_content_filter()["enabled"])
    def test_explicit_mv3_extension_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"manifest.json").write_text(json.dumps({
                "manifest_version":3,
                "name":"uBO Lite", "permissions":["declarativeNetRequest"]}))
            with patch.dict(os.environ,{"SURYADEV_UBOL_EXTENSION_DIR":str(p)}):
                result=adapter._chromium_content_filter()
            self.assertTrue(result["enabled"])
            self.assertEqual(len(result["args"]),2)
            self.assertTrue(result["args"][1].startswith("--load-extension="))
    def test_official_browser_channel_is_opt_in_and_extension_safe(self):
        filt={"enabled":False,"args":[]}
        # Old host settings may still be present in the owner's PowerShell
        # process, but they MUST NEVER launch Google Chrome / Microsoft Edge.
        for configured in ("","chrome","msedge","chromium","unofficial"):
            with self.subTest(configured=configured):
                with patch.dict(os.environ,{"SURYADEV_VIDEO_BROWSER_CHANNEL":configured}):
                    self.assertEqual(adapter._video_browser_channel(filt),"chromium")
                    self.assertEqual(adapter._video_browser_channel({
                        "enabled":True,"args":["--load-extension"]}),"chromium")

    def test_missing_or_unreviewed_extension_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with patch.dict(os.environ,{"SURYADEV_UBOL_EXTENSION_DIR":str(p)}):
                with self.assertRaises(ValueError):
                    adapter._chromium_content_filter()
            (p/"manifest.json").write_text(json.dumps({
                "manifest_version":3,"permissions":["nativeMessaging",
                                                     "declarativeNetRequest"]}))
            with patch.dict(os.environ,{"SURYADEV_UBOL_EXTENSION_DIR":str(p)}):
                with self.assertRaises(ValueError):
                    adapter._chromium_content_filter()


class SupervisorOwnershipTests(unittest.TestCase):
    def test_supervisor_job_media_heartbeat_shown_only_if_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            job_id="approved-video-"+"a"*16
            job_dir=root/"video-review"/"runtime"/"jobs"/job_id
            job_dir.mkdir(parents=True)
            now=time.time()
            (root/"video-concurrent-runtime.json").write_text(json.dumps({
                "schema":"suryadev.parallel-video.v1",
                "updated_at":now,
                "active_job_ids":[job_id]}))
            (job_dir/"media-health.json").write_text(json.dumps({
                "schema":"suryadev.garudanetra-media-health.v1",
                "job_id":job_id,"updated_at":now,
                "engine":"garudanetra-media-lite-playwright",
                "browser_channel":"chrome","player_state":"playing_or_buffered",
                "source_position_seconds":42.5,"ready_state":4,
                "network_state":2,"ad_showing":False,
                "observed_playback_rate":1.5,
                "measured_speed_ceiling_x":1.5,
                "learning_verified":False}))
            (job_dir/"playback-speed.json").write_text(json.dumps({
                "schema":"krishna.suryadev.playback-speed.v1",
                "job_id":job_id,"updated_at":now,
                "observed_rate":1.5,"requested_rate":1.5,
                "category":"explanation",
                "video_seconds":42.5,
                "browser_channel":"chrome",
                "measured_speed_ceiling_x":1.5}))
            review=VideoReview(root,root)
            status=review.snapshot()
            self.assertEqual(status["active_job"],job_id)
            self.assertEqual(status["media_health"]["source_position_seconds"],42.5)
            self.assertFalse(status["media_health"]["learning_verified"])
            self.assertEqual(status["playback"]["measured_speed_ceiling_x"],1.5)
            info=json.loads((job_dir/"media-health.json").read_text())
            info["updated_at"]=now-300
            (job_dir/"media-health.json").write_text(json.dumps(info))
            self.assertIsNone(review.snapshot()["media_health"])

    def test_fleet_dashboard_never_starts_standalone_video_or_grabs_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"fresh-workspace.json").write_text(json.dumps({
                "schema":"suryadev.fresh-workspace.v1",
                "node_profile":"fleet_adaptive"}))
            (root/"video-auto.json").write_text(json.dumps({
                "schema":"suryadev.video-auto.v1","enabled":True}))
            review=VideoReview(root,root)
            class Stub:
                def snapshot(self):
                    raise AssertionError("must not poll/start standalone worker")
            def stopped(_):
                review.auto_stop.set()
            with patch.object(review,"_auto_tick") as auto, \
                 patch.object(review.auto_stop,"wait",side_effect=stopped):
                review._auto_loop(Stub())
                auto.assert_not_called()
            self.assertEqual(review.auto_status,
                             "supervisor_owned_waiting_for_learning_worker")


if __name__=="__main__":
    unittest.main()
