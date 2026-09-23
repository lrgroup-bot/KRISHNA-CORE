import tempfile
import unittest
from pathlib import Path

from krishna_core.sudarshan_design_engine import DesignGenome, SudarshanDesignEngine
from krishna_core.sudarshan_project_orchestrator import SudarshanProjectOrchestrator
from krishna_core.vishvakarma_learning import ResearchLesson, VishvakarmaLearning


class FinalDesignToolingTests(unittest.TestCase):
    def test_design_genome_includes_accessibility(self):
        self.assertIn("accessibility",DesignGenome.SECTIONS)

    def test_optional_design_tooling_is_live_but_non_authoritative(self):
        with tempfile.TemporaryDirectory() as td:
            engine=SudarshanDesignEngine(Path(td)/"design")
            status=engine.status()
            self.assertIn("tooling",status)
            self.assertIn("storybook_required_states",status["tooling"])
            self.assertFalse(status["tooling"]["stagehand"]["available"])
            self.assertIn("Vishvakarma",status["authority"])

    def test_live_bound_design_work_blocks_until_verified_knowledge_exists(self):
        with tempfile.TemporaryDirectory() as td:
            learning=VishvakarmaLearning(Path(td)/"learning")
            engine=SudarshanDesignEngine(Path(td)/"design",knowledge=learning)
            project=SudarshanProjectOrchestrator(engine)
            checks={
                "vishvakarma_knowledge":True,"design_spec":True,"functional":True,
                "visual":True,"responsive":True,"accessibility":True,"security":True,
            }
            blocked=project.dispatch("ui",checks)
            self.assertEqual(blocked["state"],"BLOCKED_VISHVAKARMA_KNOWLEDGE")
            learning.verify(ResearchLesson(
                source="design-system",source_version="v1",license="MIT",topic="ui",
                lesson="Use visible keyboard focus and explicit component states",
                evidence="verified component-state review",confidence=0.9,
            ))
            ready=project.dispatch("ui",checks)
            self.assertEqual(ready["state"],"READY")
            self.assertTrue(ready["design_plan"]["verified_vishvakarma_findings"])


if __name__=="__main__":
    unittest.main()
