"""A stalled YouTube browser is diagnostic evidence, not successful learning."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import suryadev_worker


class VideoAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.work=self.root/"job"
        self.work.mkdir()

    def bundle(self, *, reason="video_html_ended", watched=120,
               duration=120, captions=0, frames=None):
        if frames is None:
            frames=[10,40]
        return {
            "schema":"krishna.suryadev.learning-bundle.v1",
            "job_id":"approved-video-test-one",
            "source":{"url":"https://www.youtube.com/watch?v=abcdefghijk",
                      "title":"Test lecture","subject":"Lecture"},
            "session":{"end_reason":reason,
                       "watched_seconds":watched,
                       "source_duration_seconds":duration,
                       "video_ended":reason=="video_html_ended"},
            "transcript":{"source":"browser_caption" if captions else "unavailable",
                          "line_count":captions},
            "learning_chunks":([{"topic":"Lesson","text":"Actual timed cue",
                                 "start_seconds":10,"end_seconds":20}]
                               if captions else []),
            "visual_evidence":[
                {"sha256":"a"*64,"timestamp_seconds":ts,"reason":"periodic_context"}
                for ts in frames],
            "raw_media_included":False,
        }

    def validate(self, bundle):
        path=self.work/"learning-bundle.json"
        path.write_text(json.dumps(bundle),encoding="utf-8")
        return suryadev_worker._validate_bundle(path,{
            "job_id":"approved-video-test-one","kind":"video_research"})

    def test_eight_second_captionless_stall_must_not_be_acknowledged(self):
        row=self.bundle(reason="content_playback_stalled",
                        watched=8,duration=0,frames=[0],captions=0)
        self.assertFalse(self.validate(row)["valid"])
        self.assertIn("content_playback_stalled",self.validate(row)["reason"])

    def test_failed_browser_or_ad_wait_never_claims_success(self):
        for reason in ("advertisement_wait_limit","browser_snapshot_unavailable"):
            with self.subTest(reason=reason):
                result=self.validate(self.bundle(reason=reason,captions=1))
                self.assertFalse(result["valid"])
                self.assertIn(reason,result["reason"])

    def test_garudanetra_media_reset_redirect_and_error_do_not_reach_core(self):
        for reason in ("media_unloaded_after_playback",
                       "video_element_replaced",
                       "unapproved_video_navigation", "media_error"):
            with self.subTest(reason=reason):
                bundle=self.bundle(reason=reason,watched=300,duration=3600,
                                   captions=12,frames=[20,75])
                bundle["session"]["garudanetra_media"]={
                    "engine":"garudanetra-media-lite-playwright",
                    "profile_isolated":True,"source_learning_verified":False}
                result=self.validate(bundle)
                self.assertFalse(result["valid"])
                self.assertIn(reason,result["reason"])

    def test_zero_caption_single_frame_rejected_even_without_stall(self):
        result=self.validate(self.bundle(frames=[0],watched=8,duration=3600))
        self.assertFalse(result["valid"])
        self.assertIn("insufficient",result["reason"])

    def test_legitimate_time_separated_visual_candidates_remain_unverified(self):
        result=self.validate(self.bundle(watched=90,duration=3600,frames=[20,75]))
        self.assertTrue(result["valid"])
        self.assertEqual(result["visual_count"],2)

    def test_real_caption_can_have_fewer_visuals(self):
        result=self.validate(self.bundle(captions=4,frames=[]))
        self.assertTrue(result["valid"])
        self.assertEqual(result["chunk_count"],1)

    def test_worker_final_report_marks_stall_evidence_required(self):
        job={"schema":"krishna.suryadev.job.v1",
             "job_id":"approved-video-test-one","kind":"video_research",
             "target":"https://www.youtube.com/watch?v=abcdefghijk",
             "constraints":{"duration_seconds":60}}
        job_path=self.root/"job.json"
        job_path.write_text(json.dumps(job),encoding="utf-8")
        runtime=self.root/"runtime"
        def fake_adapter(*args):
            destination=runtime/"jobs"/job["job_id"]
            destination.mkdir(parents=True,exist_ok=True)
            (destination/"learning-bundle.json").write_text(
                json.dumps(self.bundle(reason="content_playback_stalled",
                                       watched=8,duration=0,captions=0,frames=[0])))
            return {"returncode":0,"stdout":"","stderr":""}
        with patch.object(suryadev_worker,"_run_adapter",side_effect=fake_adapter), \
             patch.object(suryadev_worker,"probe",return_value={}):
            outcome=suryadev_worker.process_job(job_path,runtime)
        self.assertEqual(outcome["status"],"EVIDENCE_REQUIRED")
        self.assertFalse(outcome["ready_for_upload"])
        self.assertFalse(outcome["bundle_valid"])
        self.assertTrue((runtime/"jobs"/job["job_id"]/"learning-bundle.json").exists())


if __name__=="__main__":
    unittest.main()
