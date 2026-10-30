"""Three-source owner-approval is atomic, explicit and never clears video evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from suryadev_standalone_trial_sources import LESSONS,prepare
from suryadev_trial_limits import video_job_id


class StandaloneTrialSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"suryadev.sqlite3").write_bytes(b"existing-db-unopened")
        (self.root/"learning-plan.json").write_text(json.dumps({
            "approved_urls":["https://www.youtube.com/watch?v=old12345678"],
            "approved_feeds":[],
            "allowed_source_hosts":["www.youtube.com"],
            "max_queued":40,"max_new_per_cycle":5}),encoding="utf-8")
        (self.root/"video-trial-selection.json").write_text(json.dumps({
            "schema":"suryadev.video-trial-selection.v1",
            "target":3,"job_ids":[]}),encoding="utf-8")
        (self.root/"video-observer-attempts.json").write_text(json.dumps({
            "schema":"suryadev.video-attempts.v1",
            "job_ids":["approved-video-oldhistorical"]
        }),encoding="utf-8")

    def test_preview_is_read_only_and_exposes_three_distinct_video_ids(self):
        before=(self.root/"learning-plan.json").read_bytes()
        result=prepare(self.root)
        self.assertEqual(result["mode"],"preview")
        self.assertEqual(len(result["new_lessons"]),3)
        self.assertEqual(len({x["job_id"] for x in result["new_lessons"]}),3)
        self.assertFalse(result["source_approval_modified"])
        self.assertEqual((self.root/"learning-plan.json").read_bytes(),before)

    def test_opt_in_preserves_previous_approvals_and_evidence(self):
        original=(self.root/"learning-plan.json").read_bytes()
        attempts=(self.root/"video-observer-attempts.json").read_bytes()
        selected=(self.root/"video-trial-selection.json").read_bytes()
        out=prepare(self.root,approve=True)
        self.assertTrue(out["source_approval_modified"])
        self.assertEqual(Path(out["backup"]).read_bytes(),original)
        after=json.loads((self.root/"learning-plan.json").read_text())
        self.assertEqual(len(after["approved_urls"]),4)
        self.assertEqual(after["approved_urls"][0],"https://www.youtube.com/watch?v=old12345678")
        self.assertEqual(after["approved_urls"][1:],[url for _,url in LESSONS])
        self.assertEqual((self.root/"video-observer-attempts.json").read_bytes(),attempts)
        self.assertEqual((self.root/"video-trial-selection.json").read_bytes(),selected)
        with self.assertRaisesRegex(RuntimeError,"already in the approved plan"):
            prepare(self.root,approve=True)

    def test_existing_candidate_evidence_prevents_source_addition(self):
        title,url=LESSONS[0]
        jid=video_job_id(url)
        folder=self.root/"video-review"/"runtime"/"jobs"/jid
        folder.mkdir(parents=True)
        original=(self.root/"learning-plan.json").read_bytes()
        with self.assertRaisesRegex(RuntimeError,"already has historical"):
            prepare(self.root,approve=True)
        self.assertEqual((self.root/"learning-plan.json").read_bytes(),original)

    def test_frozen_existing_trial_selection_cannot_be_replaced(self):
        p=self.root/"video-trial-selection.json"
        frozen=json.loads(p.read_text())
        frozen["job_ids"]=["approved-video-0123456789abcdef"]
        p.write_text(json.dumps(frozen),encoding="utf-8")
        original=(self.root/"learning-plan.json").read_bytes()
        with self.assertRaisesRegex(RuntimeError,"not an empty"):
            prepare(self.root,approve=True)
        self.assertEqual((self.root/"learning-plan.json").read_bytes(),original)


if __name__=="__main__":
    unittest.main()
