from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from krishna_core.amcc_controller import AMCCController


class AMCCControllerTests(unittest.TestCase):
    def make(self, root: Path) -> AMCCController:
        return AMCCController(root / "amcc")

    def test_high_risk_signal_aborts_without_granting_authority(self):
        with tempfile.TemporaryDirectory() as td:
            amcc = self.make(Path(td))
            decision = amcc.evaluate("KRISHNA", "Apply a risky change", {"risk": 0.95})
            self.assertEqual(decision["mode"], "ABORT")
            self.assertFalse(decision["execute"])
            self.assertEqual(decision["retry_budget"], 0)
            self.assertIn("permissions", decision["safety_authority"])

    def test_repeated_failure_switches_strategy_then_escalates(self):
        with tempfile.TemporaryDirectory() as td:
            amcc = self.make(Path(td))
            project, goal = "KRISHNA", "Repair runtime"
            amcc.record_outcome(project, goal, "failed", error="one")
            amcc.record_outcome(project, goal, "rejected", error="two")
            explore = amcc.evaluate(project, goal)
            self.assertEqual(explore["mode"], "EXPLORE")
            self.assertEqual(explore["strategy"], "strategy_switch")

            amcc.record_outcome(project, goal, "failed", error="three")
            amcc.record_outcome(project, goal, "failed", error="four")
            escalate = amcc.evaluate(project, goal)
            self.assertEqual(escalate["mode"], "ESCALATE")
            self.assertEqual(escalate["strategy"], "specialist_root_cause_research")

    def test_success_resets_failure_streak(self):
        with tempfile.TemporaryDirectory() as td:
            amcc = self.make(Path(td))
            project, goal = "KRISHNA", "Verify repair"
            amcc.record_outcome(project, goal, "failed")
            amcc.record_outcome(project, goal, "failed")
            self.assertEqual(amcc.evaluate(project, goal)["mode"], "EXPLORE")
            state = amcc.record_outcome(project, goal, "verified", progress=1.0)
            self.assertEqual(state["failure_streak"], 0)
            self.assertNotEqual(amcc.evaluate(project, goal)["mode"], "EXPLORE")

    def test_resource_pressure_prefers_recovery_when_not_urgent(self):
        with tempfile.TemporaryDirectory() as td:
            amcc = self.make(Path(td))
            decision = amcc.evaluate(
                "KRISHNA", "Background research",
                {"resource_pressure": 0.95, "urgency": 0.30},
            )
            self.assertEqual(decision["mode"], "RECOVER")
            self.assertTrue(decision["execute"])

    def test_urgent_high_value_goal_intensifies(self):
        with tempfile.TemporaryDirectory() as td:
            amcc = self.make(Path(td))
            decision = amcc.evaluate(
                "KRISHNA", "Restore production service",
                {
                    "goal_value": 1.0,
                    "owner_priority": 1.0,
                    "expected_success": 0.8,
                    "urgency": 0.95,
                    "risk": 0.1,
                    "resource_pressure": 0.1,
                },
            )
            self.assertEqual(decision["mode"], "INTENSIFY")
            self.assertGreater(decision["control_intensity"], 0.5)

    def test_state_survives_controller_restart(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = self.make(root)
            first.record_outcome("KRISHNA", "Persistent goal", "failed")
            second = self.make(root)
            status = second.status(project="KRISHNA")
            self.assertEqual(status["goal_count"], 1)
            self.assertEqual(status["goals"][0]["failure_streak"], 1)

    def test_signals_are_clamped(self):
        with tempfile.TemporaryDirectory() as td:
            amcc = self.make(Path(td))
            decision = amcc.evaluate(
                "KRISHNA", "Clamp inputs",
                {"goal_value": 9, "risk": -5, "failure_streak": -3},
            )
            self.assertEqual(decision["signals"]["goal_value"], 1.0)
            self.assertEqual(decision["signals"]["risk"], 0.0)
            self.assertEqual(decision["signals"]["failure_streak"], 0)


if __name__ == "__main__":
    unittest.main()
