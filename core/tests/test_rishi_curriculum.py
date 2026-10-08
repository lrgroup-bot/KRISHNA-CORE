import tempfile
import unittest
from pathlib import Path

from krishna_core.rishi_council import RishiCouncil
from krishna_core.rishi_curriculum import (
    CurriculumRishiLearningLedger,
    CURRICULUM_RESEARCH_BASIS,
    STAGES,
)
from krishna_core.rishi_learning import RishiLearningLedger


class MemoryStub:
    def __init__(self):
        self.audit_rows=[]
        self.rows=[]
    def audit(self,*args):
        self.audit_rows.append(args)
    def remember(self,*args):
        self.rows.append(args)


class RishiCurriculumTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/"learning"
        self.memory=MemoryStub()
        self.council=RishiCouncil()
        self.ledger=RishiLearningLedger(self.root,self.council,self.memory)

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_learning_ledger_is_curriculum_enhanced_drop_in(self):
        self.assertIsInstance(self.ledger,CurriculumRishiLearningLedger)
        self.assertEqual(len(self.council.list()),31)
        matrix=self.ledger.topic_matrix()
        self.assertTrue(matrix["curriculum"]["permanent"])
        self.assertEqual(matrix["curriculum"]["unit_count"],31*len(STAGES))
        self.assertEqual(
            [x["id"] for x in matrix["curriculum"]["stages"]],
            ["foundation","core","advanced","frontier","synthesis"],
        )

    def test_every_permanent_rishi_has_five_evidence_gated_units(self):
        for profile in self.council.list():
            curriculum=self.ledger.curriculum(profile["id"])
            self.assertEqual(len(curriculum["units"]),5)
            self.assertEqual([x["stage"] for x in curriculum["units"]],[x["id"] for x in STAGES])
            for unit in curriculum["units"]:
                self.assertTrue(unit["subjects"])
                self.assertTrue(unit["objectives"])
                self.assertTrue(unit["source_kinds"])
                self.assertTrue(unit["assessment"]["exam_alone_is_not_mastery"])

    def test_key_specialists_have_progressive_subject_maps(self):
        sushruta=self.ledger.curriculum("sushruta")
        by_stage={x["stage"]:x for x in sushruta["units"]}
        self.assertIn("anatomy",by_stage["foundation"]["subjects"])
        self.assertIn("surgery",by_stage["core"]["subjects"])
        self.assertIn("biomaterials",by_stage["advanced"]["subjects"])
        self.assertIn("regenerative medicine",by_stage["frontier"]["subjects"])

        kanada={x["stage"]:x for x in self.ledger.curriculum("kanada")["units"]}
        self.assertIn("thermodynamics",kanada["foundation"]["subjects"])
        self.assertIn("materials science",kanada["core"]["subjects"])
        self.assertIn("nanoscience",kanada["frontier"]["subjects"])

        panini={x["stage"]:x for x in self.ledger.curriculum("panini")["units"]}
        self.assertIn("Sanskrit",panini["foundation"]["subjects"])
        self.assertIn("NLP",panini["frontier"]["subjects"])
        self.assertIn("philological provenance",panini["synthesis"]["subjects"])

    def test_source_plans_reuse_gyan_sagar_without_network_execution(self):
        s=self.ledger.curriculum_source_plan("sushruta","sushruta:foundation",12)
        self.assertFalse(s["network_executed"])
        self.assertTrue(s["zero_spend"])
        self.assertEqual(s["source_fabrics"],["rishi-gyan-sagar","rishi-deep-sources"])
        self.assertTrue({"europe-pmc","pmc","ncbi-bookshelf"} & set(s["source_ids"]))

        p=self.ledger.curriculum_source_plan("panini","panini:foundation",12)
        self.assertTrue({"sarit","dcs"} & set(p["source_ids"]))

    def test_balanced_daily_assignment_moves_to_another_rishi_after_direct_learning(self):
        first=self.ledger.next_learning_assignment()
        self.assertIn("unit_id",first)
        self.assertIn("source_plan",first)
        self.ledger.record_finding(
            first["rishi_id"],first["subject"],"direct curriculum evidence",
            role="lead",maturity="L1",evidence_status="candidate",confidence=.6,source_count=1,
        )
        second=self.ledger.next_learning_assignment()
        self.assertNotEqual(first["rishi_id"],second["rishi_id"])

    def test_exam_cannot_create_mastery_without_required_evidence(self):
        unit="sushruta:foundation"
        exam=self.ledger.curriculum_record_exam(
            "sushruta",unit,.95,reviewers=["gautama"],evidence=[{"kind":"assessment"}],
        )
        self.assertTrue(exam["passed"])
        self.assertFalse(exam["unit_progress"]["mastered"])
        self.assertEqual(exam["unit_progress"]["status"],"assessment_passed_evidence_pending")

        self.ledger.record_finding(
            "sushruta","anatomy physiology pathology clinical research",
            "Foundation evidence collected with explicit limitations.",
            role="lead",maturity="L2",evidence_status="candidate",confidence=.72,source_count=2,
        )
        progress=self.ledger.curriculum_academy.unit_progress("sushruta",unit)
        self.assertTrue(progress["evidence_ready"])
        self.assertTrue(progress["exam_passed"])
        self.assertTrue(progress["mastered"])

    def test_core_stage_requires_verified_finding_and_foundation_mastery(self):
        self.ledger.record_finding(
            "sushruta","anatomy physiology pathology clinical research","foundation direct",
            role="lead",maturity="L2",evidence_status="candidate",confidence=.7,source_count=2,
        )
        self.ledger.curriculum_record_exam("sushruta","sushruta:foundation",.9,reviewers=["gautama"])

        self.ledger.record_finding(
            "sushruta","diagnostics surgery medical devices medical imaging","core candidate",
            role="lead",maturity="L2",evidence_status="candidate",confidence=.7,source_count=2,
        )
        self.ledger.record_finding(
            "sushruta","diagnostics surgery medical devices medical imaging","core verified evidence",
            role="lead",maturity="L4",evidence_status="strongly_supported",confidence=.9,source_count=4,
        )
        before=self.ledger.curriculum_academy.unit_progress("sushruta","sushruta:core")
        self.assertTrue(before["evidence_ready"])
        self.assertFalse(before["mastered"])
        out=self.ledger.curriculum_record_exam("sushruta","sushruta:core",82,reviewers=["gautama"])
        self.assertTrue(out["passed"])
        self.assertTrue(out["unit_progress"]["mastered"])

    def test_synthesis_assessment_requires_vyasa_and_gautama(self):
        out=self.ledger.curriculum_record_exam(
            "panini","panini:synthesis",.95,reviewers=["gautama"],
        )
        self.assertFalse(out["passed"])
        self.assertIn("veda-vyasa",out["missing_reviewers"])

    def test_exam_and_session_state_persist(self):
        self.ledger.curriculum_record_exam(
            "kanada","kanada:foundation",.8,reviewers=["gautama"],notes="first exam",
        )
        self.ledger.curriculum_record_study(
            "kanada","kanada:foundation",mission_id="m-1",run_id="run-1",source_ids=["openalex"],
        )
        reloaded=RishiLearningLedger(self.root,self.council,self.memory)
        exam=reloaded.curriculum_academy._latest_exam("kanada","kanada:foundation")
        self.assertIsNotNone(exam)
        self.assertEqual(exam["notes"],"first exam")
        queue=reloaded.curriculum_daily_queue(5)
        self.assertIn("research",queue)
        self.assertIn("assessments",queue)

    def test_dashboard_is_planning_only_and_has_no_resident_worker(self):
        out=self.ledger.curriculum_dashboard(6)
        self.assertEqual(out["total_rishis"],31)
        self.assertEqual(out["total_units"],155)
        self.assertEqual(out["resident_workers"],0)
        self.assertLessEqual(len(out["daily_queue"]["research"]),6)
        self.assertIn("spends no money",out["daily_queue"]["policy"])

    def test_curriculum_research_basis_is_explicit_and_structural(self):
        authorities={x["authority"] for x in CURRICULUM_RESEARCH_BASIS}
        self.assertTrue(any("Medical Commission" in x for x in authorities))
        self.assertTrue(any("Technical Education" in x for x in authorities))
        self.assertTrue(any("Sanskrit University" in x for x in authorities))
        for row in CURRICULUM_RESEARCH_BASIS:
            self.assertTrue(row["principles"])
            self.assertTrue(row["url"].startswith("https://"))


if __name__=="__main__":
    unittest.main()
