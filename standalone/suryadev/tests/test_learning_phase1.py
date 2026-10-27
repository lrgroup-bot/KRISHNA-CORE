"""No-network Phase-1 acceptance regression: never replay historical observations."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from suryadev_learning_phase1 import phase1, assess_video
from suryadev_trial_limits import video_job_id

URLS=[
 "https://www.youtube.com/watch?v=mgBpcQRDtl0",
 "https://www.youtube.com/watch?v=VZ5LU8vHT0s",
 "https://www.youtube.com/watch?v=abcdefghijk",
 "https://www.youtube.com/watch?v=123456789ab",
]


def plan(root):
    (root/"learning-plan.json").write_text(json.dumps({
        "schema":"suryadev.learning-plan.v1",
        "approved_urls":URLS,"approved_feeds":[],
        "allowed_source_hosts":["www.youtube.com"],
        "max_queued":40,"max_new_per_cycle":5,
    }),encoding="utf-8")


class PhaseOneAcceptanceTests(unittest.TestCase):
    def test_existing_video_history_protected_and_gate_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            for url in URLS:
                folder=root/"video-review"/"runtime"/"jobs"/video_job_id(url)
                folder.mkdir(parents=True,exist_ok=True)
            (root/"video-observer-attempts.json").write_text(json.dumps({
                "schema":"suryadev.video-attempts.v1",
                "job_ids":[video_job_id(x) for x in URLS[:3]]
            }),encoding="utf-8")
            report=phase1(root)
            self.assertEqual(report["result"],"BLOCKED_NO_NEW_APPROVED_VIDEO")
            self.assertEqual(report["fresh_eligible_videos"],0)
            self.assertEqual(report["historical_videos_protected"],4)
            self.assertTrue(all(not x["eligible_for_first_observation"] for x in report["videos"]))
            self.assertTrue(report["no_mutations"])
            self.assertFalse(report["full_learning_verified"])

    def test_one_fresh_approved_source_does_not_authorize_other_replays(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            for url in URLS[:3]:
                (root/"video-review"/"runtime"/"jobs"/video_job_id(url)).mkdir(
                    parents=True,exist_ok=True)
            (root/"video-observer-attempts.json").write_text(json.dumps({
                "schema":"suryadev.video-attempts.v1",
                "job_ids":[video_job_id(x) for x in URLS[:3]]
            }),encoding="utf-8")
            report=phase1(root)
            self.assertEqual(report["result"],"READY_FOR_FRESH_APPROVED_OBSERVATION")
            self.assertEqual(report["fresh_eligible_videos"],1)
            self.assertTrue(report["videos"][-1]["eligible_for_first_observation"])
            self.assertFalse(report["videos"][0]["eligible_for_first_observation"])

    def test_recovery_classifies_provider_block_and_protects_old_attempts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            jid=video_job_id(URLS[0])
            folder=root/"video-review"/"runtime"/"jobs"/jid
            folder.mkdir(parents=True)
            (root/"video-observer-attempts.json").write_text(json.dumps({
                "schema":"suryadev.video-attempts.v1", "job_ids":[jid]
            }),encoding="utf-8")
            inbox=root/"video-review"/"approved-inbox"
            inbox.mkdir(parents=True)
            (inbox/(jid+".json")).write_text(json.dumps({
                "schema":"krishna.suryadev.job.v1","job_id":jid,
                "kind":"video_research","target":URLS[0]
            }),encoding="utf-8")
            (folder/"learning-bundle.json").write_text(json.dumps({
                "session":{"end_reason":"media_unloaded_after_playback",
                           "garudanetra_media":{"media_http_errors":[
                               {"status":403,"host":"rr1---sn.googlevideo.com"}]}},
                "transcript":{"line_count":0}
            }),encoding="utf-8")
            report=phase1(root)
            recovery=report["recovery"]
            self.assertEqual(recovery["media_http_403_events"],1)
            self.assertEqual(recovery["media_interrupted_videos"],1)
            self.assertEqual(recovery["zero_caption_videos"],1)
            self.assertIn("youtube_media_http_403_observed",recovery["reasons"])
            self.assertFalse(recovery["safe_to_autoreplay_attempted"])
            self.assertFalse(recovery["automatic_retry_authorized"])
            self.assertTrue(report["no_mutations"])
            self.assertEqual(report["fresh_eligible_videos"],3)

    def test_recovery_empty_approvals_or_history_not_silently_replayed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            for url in URLS:
                (root/"video-review"/"runtime"/"jobs"/video_job_id(url)).mkdir(
                    parents=True,exist_ok=True)
            report=phase1(root)
            self.assertIn("no_fresh_approved_video",report["recovery"]["reasons"])
            self.assertFalse(report["recovery"]["safe_to_autoreplay_attempted"])
            self.assertEqual(report["recovery"]["fresh_approved_ready"],0)

    def test_empty_saved_trial_is_recoverable_only_for_new_unattempted_url(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            for url in URLS:
                (root/"video-review"/"runtime"/"jobs"/video_job_id(url)).mkdir(
                    parents=True,exist_ok=True)
            (root/"video-trial-selection.json").write_text(json.dumps({
                "schema":"suryadev.video-trial-selection.v1",
                "target":3, "job_ids":[]
            }),encoding="utf-8")
            report=phase1(root)
            self.assertEqual(report["result"],"BLOCKED_NO_NEW_APPROVED_VIDEO")
            self.assertTrue(report["recovery"]["saved_trial_selection_empty_recoverable"])
            self.assertFalse(report["recovery"]["saved_trial_selection_frozen"])
            self.assertIn("brand-new",report["recovery"]["next_action"])
            self.assertFalse(report["recovery"]["safe_to_autoreplay_attempted"])

    def test_nonempty_saved_trial_requires_explicit_new_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            (root/"video-trial-selection.json").write_text(json.dumps({
                "schema":"suryadev.video-trial-selection.v1",
                "target":3, "job_ids":[video_job_id(URLS[0])]
            }),encoding="utf-8")
            report=phase1(root)
            self.assertTrue(report["recovery"]["saved_trial_selection_frozen"])
            self.assertFalse(report["recovery"]["saved_trial_selection_empty_recoverable"])
            self.assertIn("frozen",report["recovery"]["next_action"])

    def test_invalid_saved_trial_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            (root/"video-trial-selection.json").write_text('{"schema":"bad"}',
                                                             encoding="utf-8")
            report=phase1(root)
            self.assertFalse(report["recovery"]["saved_trial_selection_valid"])
            self.assertIn("trial_selection_invalid",report["recovery"]["reasons"])
            self.assertIn("invalid",report["recovery"]["next_action"])

    def test_clock_advance_and_candidate_chunk_never_equal_comprehension(self):
        report=assess_video({
            "status":"AWAITING_SERVER_ACK",
            "last_playback_position_seconds":70.0,
            "source_duration_seconds":70.0,"video_ended":True,
            "bundle_validated":True,"learning_candidate_chunks":3,
            "captured_caption_lines":40,"visual_frame_samples":40,
            "caption_completeness_verified":False,
            "full_audio_visual_coverage_verified":False,
            "brahmagyan_exam_verified":False,
        },attempted=True,has_runtime=True,historical="AWAITING_SERVER_ACK")
        self.assertEqual(report["status"],"HISTORICAL_INCOMPLETE")
        self.assertFalse(report["complete_learning_verified"])
        self.assertIn("caption_completeness_unverified",report["reasons"])
        self.assertIn("independent_comprehension_unverified",report["reasons"])

    def test_corrupt_attempt_journal_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            plan(root)
            (root/"video-observer-attempts.json").write_text("{",encoding="utf-8")
            report=phase1(root)
            self.assertEqual(report["result"],"BLOCKED_INVALID_ATTEMPT_HISTORY")
            self.assertIsNone(report["fresh_eligible_videos"])
            self.assertFalse(any(x["eligible_for_first_observation"] for x in report["videos"]))


if __name__=="__main__":
    unittest.main()
