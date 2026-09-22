import tempfile
import unittest
from pathlib import Path

from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.rishi_council import RishiCouncil


class MemoryStub:
    def __init__(self):self.audit_rows=[];self.memory=[]
    def audit(self,action,status,details):self.audit_rows.append((action,status,details))
    def remember(self,project,kind,content,metadata=None):self.memory.append((project,kind,content,metadata or {}))


class GyanStub:
    def __init__(self):self.proposals=[]
    def propose(self,*args,**kwargs):
        row={"approval_id":"g1","args":args,"kwargs":kwargs}
        self.proposals.append(row)
        return {"approval_id":"g1","stored":False,"requires_user_approval":True}


class BrahmagyanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=MemoryStub();self.gyan=GyanStub()
        self.bg=BrahmagyanRuntime(Path(self.tmp.name),self.gyan,self.memory)

    def tearDown(self):self.tmp.cleanup()

    def test_council_is_permanent_profiles_not_running_processes(self):
        status=RishiCouncil().status()
        self.assertEqual(status["permanent_profiles"],28)
        self.assertEqual(status["running_processes"],0)
        ids={x["id"] for x in status["members"]}
        for needed in ("veda-vyasa","gautama","vishwamitra","sushruta","charaka","panini"):
            self.assertIn(needed,ids)
        self.assertIn("historical association",status["policy"])

    def test_mission_defaults_to_deep_L8_and_dual_track_when_needed(self):
        m=self.bg.create_mission("KRISHNA","Vedic cosmology and modern astrophysics")
        self.assertEqual(m["target_level"],"L8")
        self.assertTrue(m["dual_track_required"])
        self.assertIn("gautama",m["review_flow"])
        self.assertIn("veda-vyasa",m["review_flow"])
        with self.assertRaises(ValueError):
            self.bg.record_claim(m["mission_id"],"mixed claim",[
                {"title":"paper","identifier":"doi:x","primary":True}
            ],knowledge_track="general")

    def test_claim_cannot_skip_deep_maturity_gates(self):
        m=self.bg.create_mission("KRISHNA","Genetics research",rishi_id="kashyapa",knowledge_track="modern_science")
        c=self.bg.record_claim(m["mission_id"],"A testable genetics claim",[
            {"title":"Primary paper","identifier":"doi:1","primary":True,"source_type":"paper"}
        ],knowledge_track="modern_science")
        with self.assertRaises(ValueError):
            self.bg.advance_claim(c["claim_id"],"L2",{"context_summary":"x"})
        c=self.bg.advance_claim(c["claim_id"],"L1",{})
        with self.assertRaises(ValueError):
            self.bg.advance_claim(c["claim_id"],"L2",{})
        c=self.bg.advance_claim(c["claim_id"],"L2",{"context_summary":"Methods and scope understood."})
        with self.assertRaises(ValueError):
            self.bg.advance_claim(c["claim_id"],"L3",{"verified_by":"veda-vyasa"})
        c=self.bg.advance_claim(c["claim_id"],"L3",{"verified_by":"gautama","confidence":.8})
        self.bg.add_evidence(c["claim_id"],"supporting",{
            "title":"Independent replication","identifier":"doi:2","primary":True,"source_type":"paper"
        })
        c=self.bg.advance_claim(c["claim_id"],"L4",{
            "verified_by":"gautama","cross_check_notes":["independent replication checked"],
            "evidence_status":"strongly_supported","confidence":.9,
        })
        self.assertEqual(c["maturity"],"L4")
        with self.assertRaises(PermissionError):
            self.bg.compile_claim(c["claim_id"],"gautama")
        self.bg.compile_claim(c["claim_id"],"veda-vyasa")
        ready=self.bg.promotion_readiness(c["claim_id"])
        self.assertTrue(ready["trusted_ready"])
        out=self.bg.propose_to_gyan(c["claim_id"])
        self.assertTrue(out["readiness"]["trusted_ready"])
        self.assertEqual(len(self.gyan.proposals),1)
        self.assertTrue(self.gyan.proposals[0]["kwargs"]["verified"])

    def test_contradiction_is_preserved_and_must_be_resolved(self):
        m=self.bg.create_mission("KRISHNA","Materials science",rishi_id="kanada",knowledge_track="modern_science")
        c=self.bg.record_claim(m["mission_id"],"Material claim",[
            {"title":"Primary A","identifier":"doi:a","primary":True}
        ],knowledge_track="modern_science")
        c=self.bg.advance_claim(c["claim_id"],"L1",{})
        c=self.bg.advance_claim(c["claim_id"],"L2",{"context_summary":"Context understood"})
        c=self.bg.advance_claim(c["claim_id"],"L3",{"verified_by":"gautama"})
        self.bg.add_evidence(c["claim_id"],"supporting",{"title":"Primary B","identifier":"doi:b","primary":True})
        self.bg.add_evidence(c["claim_id"],"contradicting",{"title":"Contrary study","identifier":"doi:c","primary":True})
        c=self.bg.advance_claim(c["claim_id"],"L4",{
            "verified_by":"gautama","cross_check_notes":["conflict identified"],
            "evidence_status":"contested","confidence":.5,
        })
        self.bg.compile_claim(c["claim_id"])
        self.assertFalse(self.bg.promotion_readiness(c["claim_id"])["trusted_ready"])
        resolved=self.bg.resolve_contradiction(c["claim_id"],0,"Contrary study used a different material phase.","strongly_supported")
        self.assertTrue(resolved["contradicting_evidence"][0]["resolved_at"])
        self.assertTrue(self.bg.promotion_readiness(c["claim_id"])["trusted_ready"])
        self.assertIn("resolution",resolved["contradicting_evidence"][0])

    def test_temporal_supersession_preserves_both_states(self):
        m=self.bg.create_mission("KRISHNA","Technology version history",rishi_id="veda-vyasa")
        a=self.bg.record_claim(m["mission_id"],"Version A is current",[{"title":"Spec A","identifier":"spec:a","primary":True}],valid_from="2026-01-01")
        b=self.bg.record_claim(m["mission_id"],"Version B is current",[{"title":"Spec B","identifier":"spec:b","primary":True}],valid_from="2026-09-01")
        out=self.bg.supersede_claim(a["claim_id"],b["claim_id"])
        self.assertEqual(out["previous"]["current_state"],"superseded")
        self.assertEqual(out["previous"]["replaced_by"],b["claim_id"])
        self.assertEqual(out["current"]["previous_state"],a["claim_id"])

    def test_curiosity_and_background_learning_are_priority_and_resource_bounded(self):
        q=self.bg.add_curiosity("KRISHNA","What does KRISHNA not yet know?",{
            "relevance":1,"project":1,"knowledge_gap":1,"resource_cost":.2
        })
        self.assertGreater(q["priority"],0)
        self.assertFalse(self.bg.background_decision(80,40,False)["allowed"])
        self.assertFalse(self.bg.background_decision(10,40,True)["allowed"])
        allowed=self.bg.background_decision(10,40,False)
        self.assertTrue(allowed["allowed"])
        self.assertIsNotNone(allowed["next_question"])
        self.assertIn("no autonomous background daemon",allowed["policy"])

    def test_shishya_plan_is_temporary_multi_wave_and_resource_bounded(self):
        m=self.bg.create_mission("KRISHNA","Oncology evidence review",rishi_id="sushruta",knowledge_track="modern_science")
        plan=self.bg.shishya_plan(
            m["mission_id"],
            ["Molecular Biology","Oncology","Clinical Trials","Pharmacology","Evidence Review"],
            10,
        )
        self.assertEqual(plan["requested_count"],10)
        self.assertGreaterEqual(plan["wave_count"],2)
        self.assertLessEqual(max(len(x) for x in plan["waves"]),8)
        self.assertTrue(plan["ephemeral"])
        self.assertTrue(plan["approval_required"])
        self.assertEqual(plan["retention_policy"],"findings_and_provenance_only")
        self.assertIn("failed approaches",plan["preserve_before_retirement"])

    def test_gap_engine_generates_missing_questions_and_can_queue_them(self):
        m=self.bg.create_mission("KRISHNA","AI reliability",rishi_id="jamadagni",knowledge_track="engineering")
        c=self.bg.record_claim(m["mission_id"],"System is reliable",[],knowledge_track="engineering")
        out=self.bg.gap_questions(c["claim_id"],queue=True)
        self.assertTrue(any("primary source" in q for q in out["questions"]))
        self.assertTrue(any("contradicts" in q for q in out["questions"]))
        self.assertGreater(len(out["queued"]),0)

    def test_new_permanent_rishi_is_proposal_only_with_duplication_check(self):
        duplicate=self.bg.propose_council_specialist("genetics","Genomics specialist","persistent genomics workload")
        self.assertEqual(duplicate["status"],"needs_duplication_review")
        self.assertTrue(duplicate["duplicate_candidates"])
        novel=self.bg.propose_council_specialist("cryogenic tribology","Cryogenic Tribology Scholar","persistent uncovered engineering domain")
        self.assertEqual(novel["status"],"candidate")
        self.assertIn("proposal only",novel["policy"])

    def test_deep_prompt_refuses_forced_ancient_modern_equivalence(self):
        m=self.bg.create_mission("KRISHNA","Yoga and neuroscience",rishi_id="patanjali",knowledge_track="general")
        prompt=self.bg.deep_prompt(m["mission_id"])
        self.assertIn("Do deep source-faithful research",prompt)
        self.assertIn("separate labeled tracks",prompt)
        self.assertIn("Never force modern discoveries into ancient texts",prompt)


if __name__=="__main__":
    unittest.main()
