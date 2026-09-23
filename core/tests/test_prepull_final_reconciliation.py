import tempfile
import unittest
from pathlib import Path

from krishna_core.model_scout import ModelCandidate, ModelScout
from krishna_core.rishi_council import RishiCouncil
from krishna_core.sudarshan_design_engine import DesignJob, SudarshanDesignEngine
from krishna_core.vishvakarma_learning import ResearchLesson, VishvakarmaLearning


class FinalReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[2]

    def test_vishvakarma_is_permanent_council_member(self):
        ids={row["id"] for row in RishiCouncil().list()}
        self.assertIn("vishvakarma",ids)

    def test_verified_vishvakarma_knowledge_enters_design_plan(self):
        with tempfile.TemporaryDirectory() as td:
            learning=VishvakarmaLearning(Path(td)/"knowledge")
            learning.verify(ResearchLesson(
                source="repo@commit",source_version="abc",license="MIT",
                topic="dashboard",lesson="Keep keyboard focus visible",
                evidence="verified browser accessibility evidence",confidence=0.9,
            ))
            engine=SudarshanDesignEngine(Path(td)/"design",knowledge=learning)
            plan=engine.plan(DesignJob("dashboard",topic="dashboard"))
            self.assertTrue(plan["knowledge_bound"])
            self.assertEqual(len(plan["verified_vishvakarma_findings"]),1)

    def test_model_scout_recommendation_has_no_routing_or_billing_authority(self):
        with tempfile.TemporaryDirectory() as td:
            scout=ModelScout(Path(td)/"models.json")
            scout.evaluate(ModelCandidate(
                "local/a",task="coding",quality=0.95,latency_ms=50,
                ram_bytes=1024,vram_bytes=0,benchmark_ref="bench-1",
            ))
            rows=scout.recommend("coding",limit=5)
            self.assertEqual(rows[0]["model_id"],"local/a")
            status=scout.status()
            self.assertFalse(status["cloud_billing_authority"])
            self.assertFalse(status["routing_authority"])

    def test_shared_action_and_readonly_http_surfaces_are_wired(self):
        orch=(self.repo/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        server=(self.repo/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        for needle in (
            '"design.plan"','"design.drift"','"design.acceptance"','"design.ui.next"',
            '"vishvakarma.retrieve"','"vishvakarma.learn"','"vishvakarma.verify"',
            '"model.scout.evaluate"','"model.scout.recommend"',
            '"project.brain.provision"','"project.brain.status"','"project.brain.record"',
        ):
            self.assertIn(needle,orch)
        for needle in ('"/api/design/status"','"/api/design/knowledge"','"/api/model-scout"','"/api/project-brain"'):
            self.assertIn(needle,server)

    def test_spatial_ui_has_design_panel_without_sidebar_clutter(self):
        app=(self.repo/"app"/"spatial-ui"/"src"/"App.tsx").read_text(encoding="utf-8")
        self.assertIn("Design Intelligence",app)
        self.assertIn("fetch('/api/design/status'",app)
        sidebar=app.split('<nav aria-label="Main Menu">',1)[1].split('</nav>',1)[0]
        self.assertIn("KRISHNA",sidebar)
        self.assertIn("Sudarshan",sidebar)
        self.assertIn("Plugins",sidebar)
        self.assertNotIn("Vishvakarma",sidebar)
        self.assertNotIn("Design Intelligence",sidebar)


if __name__=="__main__":
    unittest.main()
