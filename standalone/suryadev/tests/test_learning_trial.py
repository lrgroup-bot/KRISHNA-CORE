"""Offline checks for single owner-approved trial and source-gated autonomous exams."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from suryadev import Library
from suryadev_trial import BOOK, VIDEO, audit_trial, prepare_trial
from suryadev_trial_exam import AutomaticTrialExam, eligible_questions, grade
from suryadev_liveops import atomic_json


class LearningTrialTests(unittest.TestCase):
    def test_trial_uses_exact_public_urls_and_no_unapproved_substitutes(self):
        self.assertEqual(BOOK,"https://greenteapress.com/thinkpython2/thinkpython2.pdf")
        self.assertEqual(VIDEO,"https://www.youtube.com/watch?v=VZ5LU8vHT0s")

    def test_opt_in_trial_prepares_one_book_and_video_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            plan=root/"learning-plan.json"
            plan.write_text(json.dumps({"approved_urls":[]}),encoding="utf-8")
            with patch("suryadev_trial.read_plan",return_value={}), \
                 patch("suryadev_resources.snapshot",return_value={"available":True}), \
                 patch("suryadev_parallel.plan_capacity",return_value={"safe":True,"max_total":2}), \
                 patch("suryadev_trial.VideoReview") as video, \
                 patch("suryadev_trial.acquire_book",return_value="e"*64) as acquire, \
                 patch("suryadev_trial.approve_book",return_value={
                     "status":"approved","book_id":"book-"+"e"*64}) as approve:
                video.return_value.approve_source.return_value={"status":"approved"}
                data=prepare_trial(root,root)
                video.return_value.approve_source.assert_called_once_with(VIDEO)
                video.return_value.set_auto.assert_called_once_with(True)
                acquire.assert_called_once_with(BOOK,root.resolve()/"trial-sources"/"thinkpython2.pdf")
                self.assertEqual(data["book"],"indexed_and_approved_for_model_reading")
                self.assertEqual(data["learning_verified"],False)
                self.assertEqual(data["rishi_exam_verified"],False)
                approve.assert_called_once()

    def test_zero_evidence_never_leads_to_exam_or_mastery(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            lib=Library(root)
            try:
                data=audit_trial(root,lib.db)
                self.assertEqual(data["book"]["model_lines_processed"],0)
                self.assertEqual(data["video"]["candidate_chunks"],0)
                self.assertFalse(data["rishi_exam_verified"])
                self.assertEqual(eligible_questions(root,lib.db,data),[])
                exam=AutomaticTrialExam(root,model="test",model_lock=threading.Lock(),
                    observe=lambda *a: self.fail("Never call model without evidence"))
                try:
                    state=exam.tick(db=lib.db,capacity={"safe":True,"max_total":3,
                        "active_total":0})
                    self.assertEqual(state["attempts"],[])
                    self.assertIsNone(exam.future)
                finally: exam.close()
            finally: lib.db.close()

    def test_provisional_exam_rubric_not_rishi_mastery(self):
        self.assertTrue(grade("Playwright works with Chromium, Firefox and WebKit.",
                              ("chromium","firefox","webkit")))
        self.assertFalse(grade("Chromium and Firefox only.",
                               ("chromium","firefox","webkit")))
        self.assertFalse(grade("I am uncertain.",("python 3",)))
        with tempfile.TemporaryDirectory() as folder:
            e=AutomaticTrialExam(folder,model="mock",model_lock=threading.Lock(),
                observe=lambda _m,_q:"The engines are Chromium, Firefox and WebKit.")
            try:
                result=e._evaluate({"id":"video-engines","source":"video",
                    "q":"Name the three engines","terms":("chromium","firefox","webkit"),
                    "evidence_sha256":"d"*64,"source_locator":"captions"})
                self.assertTrue(result["rubric_passed"])
                self.assertFalse(result["independent_rishi_verified"])
                self.assertEqual(result["status"],"provisional_recall_pass")
            finally:e.close()


if __name__=="__main__":
    unittest.main()
