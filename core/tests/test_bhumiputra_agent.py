import tempfile
import unittest
from pathlib import Path

from krishna_core.bhumiputra import BhumiputraAgent


class BhumiputraAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = BhumiputraAgent(Path(self.tmp.name) / "bhumiputra")
        self.square = [
            {"lat": 20.3000, "lon": 85.8000},
            {"lat": 20.3000, "lon": 85.8010},
            {"lat": 20.3010, "lon": 85.8010},
            {"lat": 20.3010, "lon": 85.8000},
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_boundary_metrics_are_positive(self):
        out = self.agent.boundary_metrics(self.square)
        self.assertGreater(out["area_m2"], 1)
        self.assertGreater(out["perimeter_m"], 1)
        self.assertEqual(out["point_count"], 4)

    def test_survey_plan_is_isolated_and_truthful_about_subsurface(self):
        out = self.agent.plan_survey(self.square, project="KRISHNA")
        self.assertFalse(out["execution"]["main_loop_blocking"])
        self.assertEqual(out["execution"]["heavy_compute"], "isolated worker/process only")
        self.assertIn("never claim verified", out["confidence_policy"]["subsurface_resource"])
        self.assertTrue(self.agent.get_survey(out["survey_id"]))

    def test_field_observation_is_persisted(self):
        survey = self.agent.plan_survey(self.square)
        receipt = self.agent.record_observation(
            survey["survey_id"],
            {"type": "road-width", "payload": {"width_m": 6.8}, "confidence": "measured"},
        )
        self.assertEqual(receipt["count"], 1)
        stored = self.agent.get_survey(survey["survey_id"])
        self.assertEqual(stored["observations"][0]["payload"]["width_m"], 6.8)

    def test_degenerate_boundary_rejected(self):
        with self.assertRaises(ValueError):
            self.agent.boundary_metrics([
                {"lat": 20.3, "lon": 85.8},
                {"lat": 20.3, "lon": 85.8},
                {"lat": 20.3, "lon": 85.8},
            ])


if __name__ == "__main__":
    unittest.main()
