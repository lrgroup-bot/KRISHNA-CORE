"""Publisher-caption fallback never bypasses YouTube or claims video viewing."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_continuity import (
    activate_official_pack, ContinuityFeeder, OFFICIAL_PUBLISHER_TRANSCRIPTS)
from suryadev_feeder import read_plan
from suryadev_publisher import recover_failed_video_from_publisher, publisher_transcript_text
from suryadev_task_details import task_detail


def test_srt():
    cues=[]
    for i in range(16):
        cues.append(
            f"{i+1}\n00:00:{i:02}.000 --> 00:00:{i+1:02}.000\n"
            f"Publisher lesson {i}: source-based learning only.\n")
    return "\n".join(cues).encode("utf-8")


class PublisherRecoveryTests(unittest.TestCase):
    def test_official_cs50_mapping_imports_real_timed_text_without_youtube_and_audits_429(self):
        with tempfile.TemporaryDirectory() as root:
            activate_official_pack(root)
            plan=read_plan(Path(root)/"learning-plan.json")
            self.assertEqual(plan["approved_publisher_transcripts"][0],
                             OFFICIAL_PUBLISHER_TRANSCRIPTS[0])
            lib=Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    job=lib.add("https://www.youtube.com/watch?v=mgBpcQRDtl0")
                fail_at=time.time()-30
                with lib.db:
                    lib.db.execute(
                        "UPDATE jobs SET status='failed',updated=?,error=? WHERE id=?",
                        (fail_at,"DownloadError: HTTP Error 429: Too Many Requests",job))
                requests=[]
                def official_only(url):
                    requests.append(url)
                    return test_srt()
                result=recover_failed_video_from_publisher(
                    lib,plan,fetcher=official_only,use_ollama=False)
                self.assertEqual(result["status"],"publisher_transcript_recovered")
                self.assertEqual(result["job_id"],job)
                self.assertEqual(requests,[OFFICIAL_PUBLISHER_TRANSCRIPTS[0]["transcript_url"]])
                self.assertEqual(lib.stats().get("done"),1)
                detail=task_detail(lib.db,root,job)
                self.assertEqual(detail["evidence_state"],"verified")
                self.assertEqual(detail["coverage"]["cue_count"],16)
                self.assertTrue(detail["coverage"]["publisher_transcript_only"])
                self.assertFalse(detail["coverage"]["youtube_extraction_success"])
                self.assertFalse(detail["coverage"]["full_video_visuals_verified"])
                self.assertFalse(detail["complete_verified"])
                self.assertIn("HTTP Error 429",detail["publisher_recovery"]["previous_error"])
                self.assertEqual(detail["publisher_recovery"]["transcript_url"],
                                 requests[0])
                self.assertTrue(any(
                    s["name"]=="Approved publisher subtitle recovery" and
                    s["state"]=="done" for s in detail["steps"]))
                self.assertTrue(any(
                    s["name"]=="Entire source processed and verified" and
                    s["state"]=="unverified" for s in detail["steps"]))
            finally:
                lib.db.close()

    def test_malformed_and_unapproved_mapping_fails_plan_validation(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"learning-plan.json"
            p.write_text(json.dumps({
                "approved_urls":[],"approved_feeds":[],
                "allowed_source_hosts":["cdn.cs50.net"],
                "approved_publisher_transcripts":[{
                    "video_url":"https://www.youtube.com/watch?v=mgBpcQRDtl0",
                    "transcript_url":"https://evil.example/video.srt"}],
                "max_new_per_cycle":5,"max_queued":10}),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"explicitly allowed host"):
                read_plan(p)

    def test_unknown_failed_job_does_not_trigger_publisher_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            activate_official_pack(root)
            plan=read_plan(Path(root)/"learning-plan.json")
            lib=Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    job=lib.add("https://www.youtube.com/watch?v=01234567890")
                with lib.db:
                    lib.db.execute(
                        "UPDATE jobs SET status='failed',error=? WHERE id=?",
                        ("HTTP Error 429: Too Many Requests",job))
                result=recover_failed_video_from_publisher(
                    lib,plan,fetcher=lambda url: (_ for _ in ()).throw(
                        AssertionError("unapproved source must not be fetched")))
                self.assertEqual(result["recovered"],0)
                self.assertEqual(lib.stats()["failed"],1)
            finally:
                lib.db.close()

    def test_publisher_network_failure_has_bounded_backoff_and_retains_failed_job(self):
        with tempfile.TemporaryDirectory() as root:
            activate_official_pack(root)
            plan=read_plan(Path(root)/"learning-plan.json")
            lib=Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    job=lib.add("https://www.youtube.com/watch?v=mgBpcQRDtl0")
                with lib.db:
                    lib.db.execute(
                        "UPDATE jobs SET status='failed',error=? WHERE id=?",
                        ("HTTP Error 429: Too Many Requests",job))
                result=recover_failed_video_from_publisher(
                    lib,plan,fetcher=lambda url: (_ for _ in ()).throw(
                        OSError("publisher unavailable")),now=12345)
                self.assertEqual(result["status"],"publisher_unavailable")
                retry=recover_failed_video_from_publisher(
                    lib,plan,fetcher=lambda url: (_ for _ in ()).throw(
                        AssertionError("backoff was bypassed")),now=12346)
                self.assertEqual(retry["status"],"publisher_backoff")
                self.assertEqual(lib.stats()["failed"],1)
                self.assertFalse(task_detail(lib.db,root,job)["finding_id"])
            finally:
                lib.db.close()

    def test_continuity_first_recovers_official_captions_and_adds_other_sources(self):
        with tempfile.TemporaryDirectory() as root:
            activate_official_pack(root)
            lib=Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    job=lib.add("https://www.youtube.com/watch?v=mgBpcQRDtl0")
                with lib.db:
                    lib.db.execute(
                        "UPDATE jobs SET status='failed',error=? WHERE id=?",
                        ("HTTP Error 429: Too Many Requests",job))
                empty_rss=b"<rss><channel></channel></rss>"
                feeder=ContinuityFeeder(root,Path(root)/"learning-plan.json",
                    refill_seconds=300,fetcher=lambda _:empty_rss,
                    publisher_fetcher=lambda _:test_srt())
                with patch("suryadev.validate_url",return_value=None):
                    result=feeder.tick(lib,youtube_blocked=True)
                self.assertEqual(result["publisher_recovered"],1)
                self.assertGreater(result["added_total"],0)
                self.assertEqual(lib.stats().get("done"),1)
                self.assertGreater(lib.stats().get("queued"),0)
                self.assertFalse(result["youtube_video_equivalence_claimed"])
            finally:
                lib.db.close()


if __name__ == "__main__":
    unittest.main()
