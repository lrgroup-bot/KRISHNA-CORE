"""BRAHMA schedules Rishi exams and spaced recall without self-grading."""
import tempfile
import unittest
from pathlib import Path
from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.brahma_exam_scheduler import BrahmaExamScheduler

class Memory:
    def audit(self,*args,**kwargs):pass

class ExamScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.brain=BrahmagyanRuntime(root/"brain",object(),Memory())
        self.m=self.brain.create_mission("KRISHNA","Semiconductor circuit failures")
        self.scheduler=BrahmaExamScheduler(root/"schedule",self.brain,clock=lambda:1000.0)
    def tearDown(self):self.temp.cleanup()

    def test_daily_plan_is_repeatable_and_separates_examiners(self):
        plan=self.scheduler.plan(as_of="2026-10-21",include_unready=True)
        self.assertEqual(plan["created"],1)
        row=plan["new"][0]
        self.assertNotEqual(row["issued_by_rishi"],row["review_by_rishi"])
        self.assertFalse(row["knowledge_verified"])
        self.assertEqual(self.scheduler.plan(as_of="2026-10-21",include_unready=True)["created"],0)
        self.assertEqual(self.scheduler.due(as_of="2026-10-21")["pending"],1)
        self.assertFalse(self.scheduler.status()["automatic_question_generation"])

    def test_no_exam_without_real_evidence_by_default(self):
        self.assertEqual(self.scheduler.plan(as_of="2026-10-21")["created"],0)
        self.assertEqual(self.scheduler.status()["count"],0)

    def test_invalid_exam_id_does_not_close_assignment(self):
        row=self.scheduler.plan(as_of="2026-10-21",include_unready=True)["new"][0]
        with self.assertRaises((KeyError,ValueError)):
            self.scheduler.register_issued_exam(row["assignment_id"],"missing")
        self.assertEqual(self.scheduler.due(as_of="2026-10-21")["pending"],1)

    def test_recall_from_pass_date_and_no_colliding_daily_exam(self):
        assignment=self.scheduler.plan(as_of="2026-10-21",include_unready=True)["new"][0]
        kinds=[("theory","why"),("theory","how"),("theory","contradiction"),
               ("practical","experiment"),("practical","transfer")]
        questions=[{"id":"q"+str(i),"kind":kind,"competency":skill,
                    "question":"Explain or demonstrate a falsifiable engineering mechanism, with alternatives.",
                    "rubric":"Check exact causal predictions, reproducibility and all supported measurements.",
                    "source_refs":["https://www.example.com/primary"]}
                   for i,(kind,skill) in enumerate(kinds)]
        exam=self.brain.create_daily_exam(self.m["mission_id"],questions,"2026-10-21",
                                           issued_by=assignment["issued_by_rishi"])
        self.scheduler.register_issued_exam(assignment["assignment_id"],exam["exam_id"])
        rows=[]
        for q in questions:
            x={"id":q["id"],"score":95,
               "response":"The candidate provides testable steps, measurements, counterexamples and source evidence.",
               "evaluation":"An independent reviewer compared the stated result to predicted measurable evidence.",
               "evidence_refs":["https://www.example.com/primary"]}
            if q["kind"]=="practical":
                x.update(artifact_sha256="a"*64,
                         test_results=["PASS: controlled simulation measurement recorded"])
            rows.append(x)
        self.brain.record_daily_exam_attempt(exam["exam_id"],rows,
                assignment["review_by_rishi"],"independent_rishi_review")
        new=self.scheduler.plan(as_of="2026-10-22",include_unready=True)["new"]
        self.assertEqual({x["exam_date"] for x in new if x["phase"]=="recall"},
                         {"2026-10-22","2026-10-28","2026-11-20"})
        self.assertFalse(any(x["phase"]=="initial" and x["exam_date"]=="2026-10-22"
                             for x in new))
        self.assertEqual(self.scheduler.plan(as_of="2026-10-22",include_unready=True)["created"],0)


if __name__=="__main__":
    unittest.main()
