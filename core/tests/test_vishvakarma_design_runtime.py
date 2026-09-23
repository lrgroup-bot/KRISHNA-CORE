import tempfile
import unittest
from pathlib import Path

from krishna_core.rishi_council import RishiCouncil
from krishna_core.sudarshan_design_engine import AcceptanceGovernor, DesignDrift, DesignJob, SudarshanDesignEngine
from krishna_core.sudarshan_project_orchestrator import SudarshanProjectOrchestrator
from krishna_core.sudarshan_ui_pipeline import UIEvidence, UIPipeline
from krishna_core.vishvakarma_curriculum import CURRICULUM
from krishna_core.vishvakarma_learning import ResearchLesson, VishvakarmaLearning
from krishna_core.vishvakarma_rishi import VishvakarmaRishi


class VishvakarmaDesignRuntimeTests(unittest.TestCase):
    def test_vishvakarma_is_permanent_council_profile_with_role_boundary(self):
        row=RishiCouncil().get("vishvakarma")
        self.assertEqual(row["display_name"],"Rishi Vishvakarma")
        self.assertIn("design systems",row["domains"])
        self.assertTrue(any("not claims of historical practice" in x for x in row["evidence_rules"]))

    def test_candidate_learning_is_not_verified_until_review(self):
        with tempfile.TemporaryDirectory() as td:
            rishi=VishvakarmaRishi(Path(td)/"rishi")
            learning=VishvakarmaLearning(Path(td)/"learning",rishi)
            lesson=ResearchLesson(
                "repo","abc123","MIT","ui",
                "Visible keyboard focus is required","accessibility regression",
            )
            candidate=learning.ingest(lesson)
            self.assertTrue(candidate["brahma_review_required"])
            self.assertEqual(rishi.retrieve("keyboard",verified_only=True),[])
            verified=learning.verify(lesson)
            self.assertEqual(verified["status"],"verified")
            self.assertEqual(len(rishi.retrieve("keyboard",verified_only=True)),1)

    def test_design_engine_drift_acceptance_and_repair_loop(self):
        with tempfile.TemporaryDirectory() as td:
            engine=SudarshanDesignEngine(td)
            self.assertIn("Playwright CLI",CURRICULUM)
            self.assertIn("image-to-code",engine.plan(DesignJob("frontend",reference_image=True))["skills"])
            self.assertFalse(DesignDrift().compare(
                {"geometry":{"radius":8}},{"geometry":{"radius":12}}
            )["pass"])
            checks={x:True for x in AcceptanceGovernor.REQUIRED}
            checks["accessibility"]=False
            self.assertFalse(engine.acceptance.evaluate(checks)["verified"])
            out=UIPipeline(engine,max_repairs=2).next_action(checks,UIEvidence())
            self.assertEqual(out["action"],"repair-and-retest")

    def test_project_design_dispatch_requires_verified_vishvakarma_knowledge(self):
        with tempfile.TemporaryDirectory() as td:
            rishi=VishvakarmaRishi(Path(td)/"rishi")
            engine=SudarshanDesignEngine(Path(td)/"design",knowledge=rishi)
            project=SudarshanProjectOrchestrator(vishvakarma=rishi,design_engine=engine)
            checks={
                "vishvakarma_knowledge":True,"design_spec":True,"functional":True,
                "visual":True,"responsive":True,"accessibility":True,"security":True,
            }
            blocked=project.dispatch("ui",checks)
            self.assertEqual(blocked["state"],"BLOCKED_VISHVAKARMA_KNOWLEDGE")
            learning=VishvakarmaLearning(Path(td)/"learning",rishi)
            learning.verify(ResearchLesson(
                "design-system","v1","MIT","ui",
                "Use explicit component states and visible focus",
                "verified component-state review",
            ))
            ready=project.dispatch("ui",checks)
            self.assertEqual(ready["state"],"READY")
            self.assertEqual(ready["brief"]["consulted"],"Rishi Vishvakarma")


if __name__=="__main__":
    unittest.main()
