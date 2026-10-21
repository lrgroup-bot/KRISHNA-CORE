"""Model-proposed Rishi exams cannot invent citations or self-certify mastery."""
import json
from pathlib import Path
import tempfile
import unittest

from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.brahma_exam_scheduler import BrahmaExamScheduler
from krishna_core.brahma_rishi_exam_author import RishiExamAuthor

URL="https://www.example.org/technical/datasheet"

class Memory:
    def audit(self,*args,**kw):pass

def sample_questions(url=URL):
    data=[("t1","theory","why","Why does this regulator fail under excessive thermal load?"),
          ("t2","theory","how","How does the switching circuit control current during startup?"),
          ("t3","theory","contradiction","Which contradictory results falsify the initial fault diagnosis?"),
          ("p1","practical","experiment","Design a reproducible safe simulation of the failure mechanism."),
          ("p2","practical","transfer","Apply that testing approach to an unseen regulator board design.")]
    return [{"id":i,"kind":kind,"competency":skill,
             "question":q,"rubric":"Require a reproducible explanation supported by independent evidence and measurable tests.",
             "source_refs":[url]} for i,kind,skill,q in data]

class Inference:
    def __init__(self,url=URL):self.url=url;self.calls=[]
    def infer(self,**kw):
        self.calls.append(kw)
        return {"response":json.dumps({"questions":sample_questions(self.url)}),
                "done":True,"inference_local":True,"knowledge_verified":False}

class RishiExamAuthorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.brain=BrahmagyanRuntime(root/"brain",object(),Memory())
        self.m=self.brain.create_mission("KRISHNA","Power electronics voltage regulators")
        self.brain.record_claim(self.m["mission_id"],
                                "The switching regulator has measurable thermal operating limits",
                                [{"url":URL,"primary":True,"title":"Datasheet"}])
        self.schedule=BrahmaExamScheduler(root/"schedules",self.brain,clock=lambda:1000.0)
        self.assignment=self.schedule.plan(as_of="2026-10-21")["new"][0]
    def tearDown(self):self.tmp.cleanup()

    def test_issued_exam_requires_real_approved_provenance_and_authorization(self):
        inference=Inference()
        author=RishiExamAuthor(self.brain,self.schedule,inference)
        draft=author.draft(self.assignment)
        self.assertEqual(draft["state"],"draft_needs_rishi_approval")
        self.assertFalse(draft["knowledge_verified"])
        self.assertFalse(draft["rishi_identity_authenticated"])
        self.assertEqual(inference.calls[0]["role"],"rishi_exam_author")
        with self.assertRaises(PermissionError):
            author.register_approved_draft(draft)
        accepted=author.register_approved_draft(draft,issuer_approved=True)
        self.assertTrue(accepted["registered"])
        self.assertEqual(accepted["independent_grader_required"],self.assignment["review_by_rishi"])
        self.assertEqual(self.brain.daily_exam_status(self.m["mission_id"])["exams"][0]["issued_by_rishi_id"],
                         self.assignment["issued_by_rishi"])

    def test_fake_source_rejected_even_after_model_generated_it(self):
        author=RishiExamAuthor(self.brain,self.schedule,Inference("https://evil.example/fake"))
        with self.assertRaisesRegex(ValueError,"invented"):
            author.draft(self.assignment)
        self.assertFalse(self.schedule.status()["automatic_grading"])

    def test_no_source_claim_blocks_model_invocation(self):
        self.brain.state["missions"][self.m["mission_id"]]["claim_ids"]=[]
        inference=Inference()
        draft=RishiExamAuthor(self.brain,self.schedule,inference).draft(self.assignment)
        self.assertEqual(draft["state"],"blocked_missing_reviewable_evidence")
        self.assertEqual(len(inference.calls),0)

if __name__=="__main__":
    unittest.main()
