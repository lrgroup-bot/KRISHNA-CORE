"""Read-only tests of honest YouTube processing time and candidate knowledge.

No network, provider traffic, browser launch, media download, or worker starts.
"""
import json
from pathlib import Path
import tempfile
import unittest

from suryadev import Library
from suryadev_youtube_audit import youtube_audit, caption_jobs, observer_jobs


class YoutubeLearningAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.lib=Library(self.root)
        self.addCleanup(self.lib.db.close)

    def add_caption(self):
        url="https://www.youtube.com/watch?v=mgBpcQRDtl0"
        jid=self.lib.add(url)
        with self.lib.db:
            self.lib.db.execute("UPDATE jobs SET status='done' WHERE id=?",(jid,))
            self.lib.db.execute(
                "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created,summary_method) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (jid,url,"a"*64,"Python lesson",
                 "Candidate: the lesson discusses generators; practical mastery not tested.",
                 "transcript",1000,"ollama_chunked:qwen3.5:2b"))
            self.lib.db.execute(
                "INSERT INTO job_provenance(job_id,kind,report_json,recorded) VALUES (?,?,?,?)",
                (jid,"youtube",json.dumps({"duration_seconds":600,"cue_count":15,
                     "last_cue_seconds":595,"first_cue_seconds":5,
                     "long_uncaptioned_gaps":[{"start_seconds":100,"end_seconds":170}],
                     "summary_coverage":"all_text_chunks_sent_to_ollama_unverified",
                     "chunks_total":2,"chunks_summarized":2}),1000))
            self.lib.db.execute(
                "INSERT INTO job_timing(job_id,kind,started_at,acquisition_seconds,"
                "summary_phase_seconds,elapsed_seconds,outcome,recorded) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (jid,"youtube",1000,12.5,34.0,47.2,"done",1047))
        return jid

    def add_observation(self, *, status="AWAITING_SERVER_ACK"):
        jid="video-lesson-01"
        home=self.root/"video-review"
        inbox=home/"approved-inbox"
        work=home/"runtime"/"jobs"/jid
        inbox.mkdir(parents=True)
        work.mkdir(parents=True)
        (inbox/(jid+".json")).write_text(json.dumps({
            "schema":"krishna.suryadev.job.v1","job_id":jid,
            "kind":"video_research",
            "target":"https://www.youtube.com/watch?v=mgBpcQRDtl0"
        }),encoding="utf-8")
        (work/"worker-report.json").write_text(json.dumps({
            "status":status, "bundle_valid":True
        }),encoding="utf-8")
        (work/"learning-bundle.json").write_text(json.dumps({
            "source":{"title":"Python lecture"},
            "session":{"started_at":1790000000,"ended_at":1790000120.5,
                       "watched_seconds":240,"source_duration_seconds":3600,
                       "video_ended":False,"four_x_observed":True},
            "transcript":{"source":"browser_caption","line_count":36},
            "learning_chunks":[{"topic":"Generators","start_seconds":0,"end_seconds":120,
                                "text":"Candidate discussion of yield, needs validation",
                                "evidence_status":"candidate"}],
            "visual_evidence":[{"sha256":"d"*64}]
        }),encoding="utf-8")
        return jid

    def test_caption_timing_is_acquisition_not_video_watching(self):
        self.add_caption()
        row=caption_jobs(self.lib.db)[0]
        self.assertEqual(row["acquisition_wall_seconds"],12.5)
        self.assertEqual(row["analysis_wall_seconds"],34.0)
        self.assertEqual(row["total_wall_seconds"],47.2)
        self.assertEqual(row["video_duration_seconds"],600)
        self.assertEqual(row["caption_cues"],15)
        self.assertFalse(row["youtube_video_watched"])
        self.assertFalse(row["brahmagyan_exam_verified"])
        self.assertIn("Candidate:",row["what_extracted_or_summarized"])

    def test_observer_wall_time_position_and_content_are_distinct(self):
        self.add_observation()
        row=observer_jobs(self.root)[0]
        self.assertEqual(row["wall_clock_seconds"],120.5)
        self.assertEqual(row["last_playback_position_seconds"],240)
        self.assertEqual(row["source_duration_seconds"],3600)
        self.assertFalse(row["video_ended"])
        self.assertEqual(row["learning_candidate_chunks"],1)
        self.assertEqual(row["visual_frame_samples"],1)
        self.assertTrue(row["awaiting_server_ack"])
        self.assertFalse(row["brahmagyan_exam_verified"])
        self.assertIn("needs validation",row["what_was_collected"][0]["candidate_text"])

    def test_legacy_stalled_ack_is_not_misrepresented_as_learning_ready(self):
        from suryadev_video_review import VideoReview
        jid=self.add_observation()
        folder=self.root/"video-review"/"runtime"/"jobs"/jid
        path=folder/"learning-bundle.json"
        bundle=json.loads(path.read_text(encoding="utf-8"))
        bundle["session"].update({
            "end_reason":"content_playback_stalled",
            "watched_seconds":0,
            "source_duration_seconds":0})
        bundle["transcript"]={"source":"unavailable","line_count":0}
        bundle["learning_chunks"]=[]
        bundle["visual_evidence"]=[{"sha256":"d"*64,
                                   "timestamp_seconds":0}]
        path.write_text(json.dumps(bundle),encoding="utf-8")
        report=observer_jobs(self.root)[0]
        self.assertEqual(report["canonical_worker_status"],"AWAITING_SERVER_ACK")
        self.assertEqual(report["status"],"INCOMPLETE_STALLED_OBSERVATION")
        self.assertTrue(report["legacy_incomplete_evidence"])
        self.assertFalse(report["awaiting_server_ack"])
        self.assertFalse(report["brahmagyan_exam_verified"])
        state=self.root/"video-review"/"runtime"/"worker-state.json"
        state.write_text(json.dumps({"jobs":{jid:{"status":"AWAITING_SERVER_ACK"}}}))
        panel=VideoReview(self.root,self.root).snapshot()["jobs"][0]
        self.assertEqual(panel["status"],"INCOMPLETE_STALLED_OBSERVATION")
        self.assertFalse(panel["can_run"])
        # Historical source artifacts remain byte-for-byte unchanged.
        self.assertEqual(bundle,json.loads(path.read_text(encoding="utf-8")))

    def test_empty_is_honest_and_read_only(self):
        before=list(self.root.iterdir())
        result=youtube_audit(self.root,self.lib.db)
        self.assertEqual(result["counts"]["rishi_exams_verified"],0)
        self.assertEqual(result["caption_extraction"],[])
        self.assertEqual(result["browser_observations"],[])
        self.assertEqual(before,list(self.root.iterdir()))
        self.assertTrue(result["read_only"])

    def test_bad_bundle_is_not_treated_as_verified_evidence(self):
        jid=self.add_observation()
        file=self.root/"video-review"/"runtime"/"jobs"/jid/"learning-bundle.json"
        file.write_text("{broken",encoding="utf-8")
        row=observer_jobs(self.root)[0]
        self.assertEqual(row["learning_candidate_chunks"],0)
        self.assertIsNone(row["wall_clock_seconds"])
        self.assertFalse(row["brahmagyan_exam_verified"])


if __name__=="__main__":
    unittest.main()
