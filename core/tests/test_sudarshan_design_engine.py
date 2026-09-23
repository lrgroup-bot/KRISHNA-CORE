import tempfile
import unittest
from pathlib import Path

from krishna_core.sudarshan_design_engine import (
    AcceptanceGovernor, DesignDrift, DesignGenome, DesignJob, SkillRouter, SudarshanDesignEngine,
)


class SudarshanDesignEngineTests(unittest.TestCase):
    def test_selective_router(self):
        skills=SkillRouter().select(DesignJob("frontend",reference_image=True))
        self.assertIn("image-to-code",skills)
        self.assertIn("playwright-cli",skills)
        self.assertNotIn("stagehand",skills)

    def test_design_genome_is_structured_and_persistable(self):
        with tempfile.TemporaryDirectory() as td:
            genome=DesignGenome(color={"accent":"indigo"},geometry={"radius":12})
            path=Path(td)/"design-genome.json"
            genome.save(path)
            text=path.read_text(encoding="utf-8")
            self.assertIn("krishna.design-genome.v1",text)
            self.assertIn("accent",text)

    def test_nested_drift_is_detected(self):
        result=DesignDrift().compare({"geometry":{"radius":8}},{"geometry":{"radius":12}})
        self.assertFalse(result["pass"])
        self.assertIn("geometry.radius",result["differences"])

    def test_acceptance_is_hard_gate(self):
        checks={name:True for name in AcceptanceGovernor.REQUIRED}
        checks["accessibility"]=False
        verdict=AcceptanceGovernor().evaluate(checks)
        self.assertFalse(verdict["verified"])
        self.assertIn("accessibility",verdict["failed"])

    def test_engine_plan_requires_vishvakarma_context(self):
        with tempfile.TemporaryDirectory() as td:
            plan=SudarshanDesignEngine(td).plan(DesignJob("dashboard",existing_ui=True))
            self.assertTrue(plan["vishvakarma_required"])
            self.assertIn("redesign-existing-projects",plan["skills"])


if __name__=="__main__":
    unittest.main()
