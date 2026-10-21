"""Evidence-backed BRAHMAGYAN daily examinations and L7 mastery gate."""
import tempfile
import unittest
from pathlib import Path
from krishna_core.brahmagyan import BrahmagyanRuntime

class Stub:
    def audit(self,*args,**kwargs):pass

class Gyan:pass

def questions():
    specs=[
        ("t1","theory","why","Why does this circuit fail when supply voltage drops?"),
        ("t2","theory","how","How does the regulator maintain output under varying loads?"),
        ("t3","theory","contradiction","Compare the contradictory measurements and identify a falsification experiment."),
        ("p1","practical","experiment","Construct a falsifiable test for a regulator using simulated inputs."),
        ("p2","practical","transfer","Demonstrate the repair approach on an unseen board model."),
    ]
    return [{"id":qid,"kind":kind,"competency":competency,"question":prompt,
             "rubric":"Evaluate evidence, causality, falsifiability and reproducible detail.",
             "source_refs":["https://example.org/paper#section-2"]}
            for qid,kind,competency,prompt in specs]

def results(theory=92,practical=96):
    output=[]
    for q in questions():
        row={"id":q["id"],"score":theory if q["kind"]=="theory" else practical,
             "evaluation":"Independent evidence-based grading documents the method and observations.",
             "response":"The answer explains the causal mechanism, counterexamples, test results and evidence.",
             "evidence_refs":["https://example.org/lab#measurement-1"]}
        if q["kind"]=="practical":
            row.update(artifact_sha256="a"*64,
                       test_results=["PASS: verified expected versus actual measurements"])
        output.append(row)
    return output

class DailyExamTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.bg=BrahmagyanRuntime(Path(self.tmp.name),Gyan(),Stub())
        self.m=self.bg.create_mission("KRISHNA","Voltage regulator faults",knowledge_track="engineering")
    def tearDown(self):self.tmp.cleanup()

    def test_difficult_exam_requires_sources_why_how_conflicts_and_practical(self):
        with self.assertRaisesRegex(ValueError,"Rishi issuer"):
            self.bg.create_daily_exam(self.m["mission_id"],questions())
        with self.assertRaisesRegex(ValueError,"existing Rishi"):
            self.bg.create_daily_exam(self.m["mission_id"],questions(),issued_by="suryadev")
        with self.assertRaisesRegex(ValueError,"5..30"):
            self.bg.create_daily_exam(self.m["mission_id"],questions()[:4],issued_by="vishvakarma")
        missing=[dict(x) for x in questions()]
        missing[0]["source_refs"]=[]
        with self.assertRaisesRegex(ValueError,"source references"):
            self.bg.create_daily_exam(self.m["mission_id"],missing,issued_by="vishvakarma")
        exam=self.bg.create_daily_exam(self.m["mission_id"],questions(),"2026-10-21",issued_by="vishvakarma")
        self.assertEqual(exam["status"],"prepared")
        self.assertEqual(exam["issued_by_rishi_id"],"vishvakarma")
        self.assertEqual(exam["registered_by"],"brahmagyan_ledger")
        with self.assertRaisesRegex(ValueError,"independent Rishi"):
            self.bg.record_daily_exam_attempt(exam["exam_id"],results(),"vishvakarma","independent_rishi_review")
        self.assertFalse(self.bg.daily_exam_status(self.m["mission_id"])["mastery_gate_satisfied"])
        with self.assertRaisesRegex(ValueError,"already exists"):
            self.bg.create_daily_exam(self.m["mission_id"],questions(),"2026-10-21",issued_by="vishvakarma")
        with self.assertRaisesRegex(ValueError,"independent"):
            self.bg.record_daily_exam_attempt(exam["exam_id"],results(),"suryadev","human_review")
        altered=results()
        del altered[3]["artifact_sha256"]
        with self.assertRaisesRegex(ValueError,"artifact"):
            self.bg.record_daily_exam_attempt(exam["exam_id"],altered,"gautama","independent_rishi_review")
        bad=self.bg.record_daily_exam_attempt(exam["exam_id"],results(70,96),"gautama","independent_rishi_review")
        self.assertFalse(bad["passed"])
        good=self.bg.record_daily_exam_attempt(exam["exam_id"],results(),"bharadvaja","independent_rishi_review")
        self.assertTrue(good["passed"])
        self.assertFalse(good["independence_verified"])
        self.assertFalse(self.bg.daily_exam_status(self.m["mission_id"])["mastery_gate_satisfied"])
        with self.assertRaises(PermissionError):
            self.bg.verify_daily_exam_attempt(exam["exam_id"],good["attempt_id"],
                evidence_receipt={"source":"simulated_test"})
        self.bg.bind_exam_verifier(lambda exam,attempt,receipt: {
            "reviewer_identity_verified":True,
            "practical_artifacts_replayed":True,
            "test_run_id":"separate-lab-run-0001"})
        verified=self.bg.verify_daily_exam_attempt(exam["exam_id"],good["attempt_id"],
            evidence_receipt={"source":"simulated_test","artifact_digest":"a"*64})
        self.assertTrue(verified["verified"])
        self.assertTrue(self.bg.daily_exam_status(self.m["mission_id"])["mastery_gate_satisfied"])
        reloaded=BrahmagyanRuntime(Path(self.tmp.name),Gyan(),Stub())
        self.assertEqual(reloaded.daily_exam_status(self.m["mission_id"])["passed_recorded"],1)

    def test_l7_refuses_synthesis_without_passing_practical_theory_exam(self):
        claim=self.bg.record_claim(self.m["mission_id"],"Supply regulation can be tested",[
            {"title":"Primary","url":"https://example.org/paper","primary":True}
        ])
        cid=claim["claim_id"]
        self.bg.advance_claim(cid,"L1")
        self.bg.advance_claim(cid,"L2",{"context_summary":"Mechanisms and limits examined"})
        self.bg.advance_claim(cid,"L3",{"verified_by":"gautama"})
        self.bg.add_evidence(cid,"supporting",{"title":"Replication","url":"https://example.net/replication","primary":True})
        self.bg.advance_claim(cid,"L4",{"verified_by":"gautama","cross_check_notes":["independent replication"]})
        self.bg.advance_claim(cid,"L5",{"application_notes":["Applied measurements"]})
        self.bg.advance_claim(cid,"L6",{"test_evidence":["reproducible bench-test evidence"]})
        with self.assertRaisesRegex(ValueError,"daily exam"):
            self.bg.advance_claim(cid,"L7",{"synthesis":"Complete synthesis","teach_back":"Explain mechanism"})
        exam=self.bg.create_daily_exam(self.m["mission_id"],questions(),"2026-10-21",issued_by="vishvakarma")
        attempt=self.bg.record_daily_exam_attempt(exam["exam_id"],results(),"gautama","independent_rishi_review")
        with self.assertRaisesRegex(ValueError,"independently verified"):
            self.bg.advance_claim(cid,"L7",{"synthesis":"Complete synthesis","teach_back":"Explain mechanism"})
        self.bg.bind_exam_verifier(lambda exam,attempt,receipt: {
            "reviewer_identity_verified":True,"practical_artifacts_replayed":True,
            "test_run_id":"simulated-separate-rishi-run-002"})
        self.bg.verify_daily_exam_attempt(exam["exam_id"],attempt["attempt_id"],
            evidence_receipt={"lab":"simulated verified separate process"})
        promoted=self.bg.advance_claim(cid,"L7",{"synthesis":"Complete synthesis","teach_back":"Explain mechanism"})
        self.assertEqual(promoted["maturity"],"L7")

if __name__=="__main__":
    unittest.main()
