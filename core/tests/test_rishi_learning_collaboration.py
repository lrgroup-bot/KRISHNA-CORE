import tempfile
import unittest
from pathlib import Path

from krishna_core.brahmagyan import BrahmagyanRuntime
from krishna_core.garuda import GarudaAgent, WebCandidate
from krishna_core.rishi_council import RishiCouncil
from krishna_core.rishi_learning import (
    RishiLearningLedger, CouncilCollaborationEngine,
    RISHI_RESEARCH_CHARTERS, CLASSICAL_SOURCE_REGISTRY,
)


class MemoryStub:
    def __init__(self):
        self.audit_rows=[]
        self.rows=[]
    def audit(self,*args):
        self.audit_rows.append(args)
    def remember(self,*args):
        self.rows.append(args)


class GyanStub:
    def propose(self,*args,**kwargs):
        return {"approval_id":"g1","stored":False,"requires_user_approval":True}


class GitHubStub:
    def search(self,*args,**kwargs):
        return {"candidates":[]}


class ClassicalGarudaStub(GarudaAgent):
    def __init__(self):
        super().__init__(GitHubStub(),MemoryStub())
    def _web(self,query,limit=10):
        return [
            WebCandidate(
                "Brihadaranyaka Upanishad",
                "https://vedicheritage.gov.in/upanishads/brihadaranyakopanishad/",
                "Principal Upanishadic source page.",
                "web",5,False,
            ),
            WebCandidate(
                "Unrelated page",
                "https://example.com/not-vedic",
                "Should be filtered.",
                "web",9,False,
            ),
        ]


class RishiLearningCollaborationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=MemoryStub()
        self.council=RishiCouncil()
        self.ledger=RishiLearningLedger(Path(self.tmp.name)/"learning",self.council,self.memory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_permanent_rishis_have_explicit_subject_charters(self):
        council_ids={x["id"] for x in self.council.list()}
        self.assertEqual(set(RISHI_RESEARCH_CHARTERS),council_ids)
        matrix=self.ledger.topic_matrix()
        self.assertEqual(len(matrix["rishis"]),len(council_ids))
        for row in matrix["rishis"]:
            self.assertTrue(row["primary_subjects"])
            self.assertTrue(row["frontier_focus"])
            self.assertTrue(row["classical_lens"])

    def test_requested_core_subject_ownership_is_visible(self):
        matrix={x["rishi_id"]:x for x in self.ledger.topic_matrix()["rishis"]}
        self.assertIn("DNA",matrix["kashyapa"]["primary_subjects"])
        self.assertIn("biomedical engineering",matrix["sushruta"]["primary_subjects"])
        self.assertIn("physics",matrix["kanada"]["primary_subjects"])
        self.assertIn("artificial intelligence",matrix["vishwamitra"]["primary_subjects"])
        self.assertIn("logic",matrix["gautama"]["primary_subjects"])
        self.assertIn("linguistics",matrix["panini"]["primary_subjects"])

    def test_classical_registry_keeps_text_track_separate_from_science(self):
        self.assertIn("Brihadaranyaka",CLASSICAL_SOURCE_REGISTRY["principal_upanishads"])
        self.assertIn("Rigveda",CLASSICAL_SOURCE_REGISTRY["layers"])
        self.assertIn("never count as experimental proof",CLASSICAL_SOURCE_REGISTRY["policy"])

    def test_dashboard_shows_learned_findings_and_evidence_state(self):
        self.ledger.record_finding(
            "kashyapa","DNA repair","A repair pathway was associated with genomic stability.",
            claim_id="c1",mission_id="m1",track="modern_science",
            maturity="L4",evidence_status="strongly_supported",confidence=.82,source_count=4,role="lead",
        )
        row=self.ledger.profile("kashyapa")
        self.assertEqual(row["finding_count"],1)
        self.assertEqual(row["findings"][0]["maturity"],"L4")
        self.assertEqual(row["findings"][0]["evidence_status"],"strongly_supported")
        dashboard=self.ledger.dashboard()
        k=[x for x in dashboard["rishis"] if x["rishi_id"]=="kashyapa"][0]
        self.assertEqual(k["direct_finding_count"],1)
        self.assertTrue(k["recent_findings"])

    def test_all_council_members_receive_shared_mission_knowledge(self):
        bg=BrahmagyanRuntime(Path(self.tmp.name)/"bg",GyanStub(),self.memory)
        mission=bg.create_mission(
            "KRISHNA","DNA repair and aging","What is known?",
            rishi_id="kashyapa",knowledge_track="modern_science",
        )
        claim=bg.record_claim(mission["mission_id"],"DNA repair capacity changes with cellular state",[
            {"title":"Study","url":"https://example.org/study","primary":True,"source_family":"lab-a"}
        ],knowledge_track="modern_science")
        out=self.ledger.ingest_mission(bg,mission["mission_id"],all_council=True)
        self.assertEqual(len(out["participants"]),len(self.council.list()))
        for profile in self.council.list():
            row=self.ledger.profile(profile["id"])
            self.assertEqual(row["finding_count"],1)
        lead=self.ledger.profile("kashyapa")
        other=self.ledger.profile("panini")
        self.assertEqual(lead["findings"][0]["role"],"lead")
        self.assertEqual(other["findings"][0]["role"],"council_knowledge_support")

    def test_shared_knowledge_does_not_falsely_complete_bootstrap(self):
        for profile in self.council.list():
            self.ledger.record_finding(
                profile["id"],"shared topic","shared finding",
                role="council_knowledge_support",
            )
        status=self.ledger.bootstrap_status()
        self.assertFalse(status["complete"])
        self.assertEqual(status["ready_count"],0)
        self.assertIsNotNone(status["next_assignment"])

    def test_balanced_bootstrap_prioritizes_least_trained_rishi(self):
        first=self.ledger.next_learning_assignment()
        self.ledger.record_finding(
            first["rishi_id"],first["subject"],"direct result",
            role="lead",maturity="L2",evidence_status="provisional",
        )
        second=self.ledger.next_learning_assignment()
        self.assertNotEqual(first["rishi_id"],second["rishi_id"])

    def test_council_collaboration_includes_every_rishi_but_only_selected_are_live(self):
        engine=CouncilCollaborationEngine(self.ledger,self.council,memory=self.memory)
        mission={
            "mission_id":"m1","lead_rishi":"kashyapa",
            "topic":"DNA aging","question":"What mechanisms matter?"
        }
        row=engine.prepare(mission,active_rishis=["kashyapa","sushruta","gautama","veda-vyasa"])
        self.assertEqual(len(row["all_rishis"]),len(self.council.list()))
        packets={x["rishi_id"]:x for x in row["knowledge_packets"]}
        self.assertEqual(packets["kashyapa"]["contribution_mode"],"active_live_support")
        self.assertEqual(packets["panini"]["contribution_mode"],"stored_knowledge_support")
        self.assertIn("dual_track_rule",row["classical_plan"])

    def test_classical_scout_filters_to_provenance_constrained_source(self):
        g=ClassicalGarudaStub()
        out=g.classical_scout("KRISHNA","consciousness self",4)
        self.assertTrue(out["web"])
        self.assertTrue(all("vedicheritage.gov.in" in x["url"] for x in out["web"]))
        self.assertEqual(out["classical_protocol"]["scientific_evidence_weight"],0)
        self.assertIn("never verifies",out["classical_protocol"]["rule"])

    def test_http_and_orchestrator_visibility_surfaces_exist(self):
        root=Path(__file__).resolve().parents[1]
        orch=(root/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        server=(root/"krishna_core"/"server.py").read_text(encoding="utf-8")
        for token in (
            "RishiLearningLedger",
            "CouncilCollaborationEngine",
            "brahmagyan.rishi.topics",
            "brahmagyan.rishi.learning",
            "brahmagyan.rishi.collaboration",
        ):
            self.assertIn(token,orch)
        self.assertIn("/api/brahmagyan/rishis/topics",server)
        self.assertIn("/api/brahmagyan/rishis/learning",server)
        self.assertIn("/api/brahmagyan/rishis/collaboration",server)


if __name__=="__main__":
    unittest.main()
