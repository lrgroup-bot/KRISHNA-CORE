"""Offline checks for single owner-approved trial and source-gated autonomous exams."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from suryadev import Library
from suryadev_trial import BOOK, VIDEO, TRIAL_RECORD, audit_trial, prepare_trial
from suryadev_trial_exam import AutomaticTrialExam, eligible_questions, grade
from suryadev_book_reader import BookLedger
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

    def test_first_boot_fixed_trial_creates_initial_approved_plan(self):
        # Existing source approvals are not a prerequisite for the two
        # specific resources the owner selected for the reproducible trial.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertFalse((root/"learning-plan.json").exists())
            with patch("suryadev_resources.snapshot",return_value={"available":True}), \
                 patch("suryadev_parallel.plan_capacity",
                       return_value={"safe":True,"max_total":2}), \
                 patch("suryadev_trial.acquire_book",return_value="a"*64), \
                 patch("suryadev_trial.approve_book",return_value={
                     "status":"approved","book_id":"book-"+"a"*64}):
                result=prepare_trial(root,root)
            self.assertEqual(result["video"],"approved_for_automatic_observation")
            self.assertEqual(result["book"],"indexed_and_approved_for_model_reading")
            source_plan=json.loads((root/"learning-plan.json").read_text(encoding="utf-8"))
            self.assertEqual(source_plan["approved_urls"],[VIDEO])
            self.assertEqual(source_plan["allowed_source_hosts"],["www.youtube.com"])

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

    def test_book_exam_reads_verified_model_coverage_from_separate_ledger(self):
        # The main assignments SQLite database has no book_lines table.
        # A completed Ollama journal must make source-gated questions eligible
        # without mixing the two databases or counting mere indexing as study.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            lib=Library(root)
            ledger=BookLedger(root)
            try:
                book_file=root/"owner-approved-test-book.txt"
                book_file.write_text(
                    "The second edition uses Python 3.\n"
                    "The turtle graphics chapter uses the turtle library.",
                    encoding="utf-8")
                imported=ledger.import_book(book_file)
                atomic_json(root,TRIAL_RECORD,{"book_id":imported["book_id"]})
                collected=audit_trial(root,lib.db)
                self.assertEqual(collected["book"]["indexed_lines"],2)
                self.assertEqual(collected["book"]["model_lines_processed"],0)
                self.assertEqual(eligible_questions(root,lib.db,collected),[])
                ledger.read(imported["book_id"],model="mock-local",
                            use_ollama=True,lines_per_step=2,max_steps=1,
                            observe=lambda _prompt,_model:"Processed both source lines.")
                learned=audit_trial(root,lib.db)
                self.assertEqual(learned["book"]["journal_integrity"],"passed")
                self.assertEqual(learned["book"]["model_lines_processed"],2)
                questions=eligible_questions(root,lib.db,learned)
                self.assertEqual(
                    {item["id"] for item in questions if item["source"]=="book"},
                    {"book-python3","book-turtle"})
                self.assertFalse(learned["rishi_exam_verified"])
            finally:
                ledger.close()
                lib.db.close()

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
