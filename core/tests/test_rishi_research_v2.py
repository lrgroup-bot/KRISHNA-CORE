import tempfile
import unittest
from pathlib import Path

from krishna_core.brahmagyan import BrahmagyanRuntime


class MemoryStub:
    def __init__(self):
        self.audit_rows=[]
        self.memory=[]
    def audit(self,action,status,details):
        self.audit_rows.append((action,status,details))
    def remember(self,project,kind,content,metadata=None):
        self.memory.append((project,kind,content,metadata or {}))


class GyanStub:
    def __init__(self):
        self.proposals=[]
    def propose(self,*args,**kwargs):
        row={"approval_id":"g1","args":args,"kwargs":kwargs}
        self.proposals.append(row)
        return {"approval_id":"g1","stored":False,"requires_user_approval":True}


class RishiResearchV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=MemoryStub()
        self.gyan=GyanStub()
        self.bg=BrahmagyanRuntime(Path(self.tmp.name),self.gyan,self.memory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_mission_has_sequential_research_phases(self):
        m=self.bg.create_mission("KRISHNA","Materials reliability",rishi_id="kanada",knowledge_track="modern_science")
        self.assertEqual(m["phase"],"scope")
        m=self.bg.advance_phase(m["mission_id"],"literature",[{"kind":"plan"}])
        self.assertEqual(m["phase"],"literature")
        with self.assertRaises(ValueError):
            self.bg.advance_phase(m["mission_id"],"challenge")

    def test_perspective_plan_uses_multiple_rishi_lenses(self):
        m=self.bg.create_mission("KRISHNA","Quantum sensing materials",knowledge_track="modern_science")
        out=self.bg.perspective_plan(m["mission_id"],5)
        ids={x["rishi_id"] for x in out["perspectives"]}
        self.assertIn("gautama",ids)
        self.assertIn("veda-vyasa",ids)
        self.assertGreaterEqual(len(ids),3)
        live=self.bg.mission(m["mission_id"])
        self.assertEqual(len(live["perspectives"]),len(out["perspectives"]))
        self.assertGreaterEqual(len(live["research_questions"]),len(out["perspectives"]))

    def test_source_family_audit_detects_false_independence(self):
        m=self.bg.create_mission("KRISHNA","Clinical evidence",rishi_id="sushruta",knowledge_track="modern_science")
        c=self.bg.record_claim(m["mission_id"],"Claim",[
            {"title":"Study A","identifier":"doi:a","primary":True,"source_family":"lab-x"}
        ],knowledge_track="modern_science")
        self.bg.add_evidence(c["claim_id"],"supporting",{
            "title":"Study B","identifier":"doi:b","primary":True,"source_family":"lab-x"
        })
        audit=self.bg.evidence_audit(c["claim_id"])
        self.assertEqual(audit["supporting_source_count"],2)
        self.assertEqual(audit["independent_support_families"],1)
        self.assertTrue(any("independent" in x for x in audit["issues"]))

    def test_named_citation_review_is_auditable_not_truth_score(self):
        m=self.bg.create_mission("KRISHNA","Astronomy evidence",rishi_id="atri",knowledge_track="modern_science")
        c=self.bg.record_claim(m["mission_id"],"Observed claim",[
            {"title":"Observation","identifier":"obs:1","primary":True}
        ],knowledge_track="modern_science")
        sid=c["sources"][0]["source_id"]
        audit=self.bg.citation_review(
            c["claim_id"],sid,True,"supports","gautama",
            "Quoted passage directly supports the narrow observation.","gautama-manual-v1"
        )
        self.assertEqual(audit["citation_audited_count"],1)
        self.assertEqual(audit["citation_verified_count"],1)
        self.assertIn("not infallible truth",audit["verifier_policy"])

    def test_retracted_support_blocks_trusted_promotion(self):
        m=self.bg.create_mission("KRISHNA","Biomedical evidence",rishi_id="sushruta",knowledge_track="modern_science")
        c=self.bg.record_claim(m["mission_id"],"Biomedical claim",[
            {"title":"Retracted primary","identifier":"doi:r","primary":True,"retracted":True}
        ],knowledge_track="modern_science")
        c=self.bg.advance_claim(c["claim_id"],"L1",{})
        c=self.bg.advance_claim(c["claim_id"],"L2",{"context_summary":"Context"})
        c=self.bg.advance_claim(c["claim_id"],"L3",{"verified_by":"gautama"})
        self.bg.add_evidence(c["claim_id"],"supporting",{
            "title":"Independent support","identifier":"doi:s","primary":True
        })
        c=self.bg.advance_claim(c["claim_id"],"L4",{
            "verified_by":"gautama","cross_check_notes":["independent source checked"],
            "evidence_status":"strongly_supported","confidence":.8,
        })
        self.bg.compile_claim(c["claim_id"])
        ready=self.bg.promotion_readiness(c["claim_id"])
        self.assertFalse(ready["trusted_ready"])
        self.assertEqual(ready["evidence_audit"]["retracted_support_count"],1)

    def test_debate_is_selective_not_default(self):
        simple=self.bg.create_mission("KRISHNA","Simple grammar question",rishi_id="panini")
        self.assertFalse(self.bg.debate_policy(simple["mission_id"])["recommended"])
        dual=self.bg.create_mission("KRISHNA","Yoga and neuroscience",rishi_id="patanjali")
        policy=self.bg.debate_policy(dual["mission_id"])
        self.assertTrue(policy["recommended"])
        self.assertTrue(any("dual evidence" in x for x in policy["reasons"]))

    def test_debate_preserves_grounding_review_and_dissent(self):
        m=self.bg.create_mission("KRISHNA","AI reliability",rishi_id="jamadagni",knowledge_track="engineering")
        c=self.bg.record_claim(m["mission_id"],"Reliability claim",[
            {"title":"Test report","identifier":"test:1","primary":True}
        ],knowledge_track="engineering")
        d=self.bg.open_debate(
            m["mission_id"],"Is the system sufficiently reliable?",
            participants=["jamadagni","bharadvaja","gautama","veda-vyasa"],stakes="high"
        )
        t1=self.bg.record_debate_turn(d["debate_id"],"jamadagni","Failure coverage is incomplete.",[c["claim_id"]],["Need crash recovery evidence"])
        self.assertEqual(t1["grounding"],"claim_linked")
        self.bg.record_debate_turn(d["debate_id"],"bharadvaja","Run a fault-injection benchmark.",[c["claim_id"]])
        with self.assertRaises(ValueError):
            self.bg.close_debate(d["debate_id"],"Premature",{})
        closed=self.bg.close_debate(
            d["debate_id"],
            "Evidence supports further testing before a stronger conclusion.",
            {"evidence_sufficient":False,"notes":"Current test set is incomplete."},
            unresolved=["Need crash recovery fault injection"]
        )
        self.assertEqual(closed["status"],"closed")
        self.assertEqual(closed["gautama_review"]["reviewer"],"gautama")
        self.assertEqual(len(closed["unresolved"]),1)

    def test_dossier_is_diagnostic_and_preserves_open_questions(self):
        m=self.bg.create_mission("KRISHNA","Language model evaluation",rishi_id="panini",knowledge_track="engineering")
        self.bg.perspective_plan(m["mission_id"],4)
        c=self.bg.record_claim(m["mission_id"],"Evaluation claim",[
            {"title":"Benchmark","identifier":"bench:1","primary":True}
        ],knowledge_track="engineering")
        dossier=self.bg.dossier(m["mission_id"])
        self.assertEqual(dossier["scorecard"]["claim_count"],1)
        self.assertGreater(dossier["scorecard"]["research_questions"],0)
        self.assertIn("does not collapse research quality",dossier["scorecard"]["policy"])
        self.assertEqual(dossier["claims"][0]["claim_id"],c["claim_id"])

    def test_orchestrator_exposes_v2_actions_through_sudarshan(self):
        source=(Path(__file__).resolve().parents[1]/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for action in (
            "brahmagyan.phase.advance",
            "brahmagyan.perspectives.plan",
            "brahmagyan.evidence.audit",
            "brahmagyan.citation.review",
            "brahmagyan.debate.policy",
            "brahmagyan.debate.open",
            "brahmagyan.debate.turn",
            "brahmagyan.debate.close",
            "brahmagyan.dossier",
        ):
            self.assertIn(action,source)


if __name__=="__main__":
    unittest.main()
