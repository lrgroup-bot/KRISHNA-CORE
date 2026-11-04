import unittest

from krishna_core.agent_evaluation import AgentTrajectoryEvaluator, EvaluatorCalibration


class AgentTrajectoryEvaluatorTests(unittest.TestCase):
    def test_safe_required_trajectory_passes(self):
        evaluator = AgentTrajectoryEvaluator()
        result = evaluator.evaluate(
            [
                {"action": "evidence.collect", "status": "completed"},
                {"action": "shadow.patch", "status": "completed"},
                {"action": "verify.run", "status": "completed"},
            ],
            required_order=["evidence.collect", "shadow.patch", "verify.run"],
            forbidden_actions=["production.deploy"],
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["missing_required"], [])

    def test_missing_order_and_forbidden_action_fail(self):
        evaluator = AgentTrajectoryEvaluator()
        result = evaluator.evaluate(
            [
                {"action": "shadow.patch", "status": "completed"},
                {"action": "production.deploy", "status": "completed"},
            ],
            required_order=["evidence.collect", "shadow.patch", "verify.run"],
            forbidden_actions=["production.deploy"],
        )
        self.assertFalse(result["passed"])
        self.assertIn("evidence.collect", result["missing_required"])
        self.assertEqual(result["forbidden_hits"][0]["action"], "production.deploy")

    def test_failed_or_blocked_step_is_evidence(self):
        evaluator = AgentTrajectoryEvaluator()
        result = evaluator.evaluate([
            {"action": "evidence.collect", "status": "completed"},
            {"action": "verify.run", "status": "failed"},
        ])
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_steps"][0]["action"], "verify.run")

    def test_allowlist_rejects_unexpected_side_effect(self):
        evaluator = AgentTrajectoryEvaluator()
        result = evaluator.evaluate(
            [{"action": "research.read"}, {"action": "file.write"}],
            allowed_actions=["research.read"],
        )
        self.assertFalse(result["passed"])
        self.assertEqual(result["unexpected_actions"][0]["action"], "file.write")


class EvaluatorCalibrationTests(unittest.TestCase):
    def test_calibration_requires_good_pass_and_bad_rejection(self):
        calibration = EvaluatorCalibration()
        result = calibration.calibrate(
            lambda value: {"passed": value > 0},
            known_good=[1, 2],
            known_bad=[0, -1],
        )
        self.assertTrue(result["calibrated"])
        self.assertEqual(result["good_pass_rate"], 1.0)
        self.assertEqual(result["bad_reject_rate"], 1.0)

    def test_weak_evaluator_is_not_calibrated(self):
        calibration = EvaluatorCalibration()
        result = calibration.calibrate(
            lambda value: True,
            known_good=["correct"],
            known_bad=["deliberately wrong"],
        )
        self.assertFalse(result["calibrated"])
        self.assertEqual(result["bad_reject_rate"], 0.0)

    def test_empty_fixture_set_never_calibrates(self):
        result = EvaluatorCalibration().calibrate(
            lambda value: True,
            known_good=[],
            known_bad=[],
        )
        self.assertFalse(result["calibrated"])


if __name__ == "__main__":
    unittest.main()
