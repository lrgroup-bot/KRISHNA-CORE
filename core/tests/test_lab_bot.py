import tempfile
import unittest
from pathlib import Path

from krishna_core.lab_bot import LabBot


class LabBotTests(unittest.TestCase):
    def _request(self, bot, **overrides):
        payload={
            "rishi":"kanada",
            "hypothesis":"A controlled physical stimulus changes the measured response.",
            "objective":"Test the hypothesis against a comparison condition.",
            "domain":"physics",
            "mode":"simulation",
            "controls":["negative control"],
            "measurements":["response amplitude"],
            "success_criteria":["predefined effect exceeds measurement uncertainty"],
            "source_refs":["paper:example"],
        }
        payload.update(overrides)
        return bot.request(payload)

    def test_rishi_request_becomes_durable_experiment_and_simulates(self):
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            exp=self._request(bot)
            self.assertTrue((Path(td)/(exp["experiment_id"]+".json")).is_file())
            result=bot.simulate(exp["experiment_id"])
            self.assertEqual(result["status"],"SIMULATED")
            self.assertTrue(result["verification"]["passed"])
            self.assertFalse(result["result"]["physical"])

    def test_incomplete_design_fails_dry_run_verification(self):
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            exp=self._request(bot,controls=[],measurements=[])
            result=bot.simulate(exp["experiment_id"])
            self.assertEqual(result["status"],"DESIGN_INCOMPLETE")
            self.assertFalse(result["verification"]["passed"])

    def test_physical_execution_requires_review_and_registered_physical_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            exp=self._request(bot,mode="measurement",adapter="bench-meter")
            with self.assertRaises(PermissionError):
                bot.execute(exp["experiment_id"])

            bot.review(exp["experiment_id"],protocol_reviewed=True,owner_approved=True)
            with self.assertRaises(RuntimeError):
                bot.execute(exp["experiment_id"])

            bot.register_adapter(
                "bench-meter",
                capabilities=("measure",),
                domains=("physics",),
                physical=True,
                handler=lambda record,context:{"observed":1.23,"unit":"arb"},
            )
            result=bot.execute(exp["experiment_id"])
            self.assertEqual(result["status"],"EXECUTED_PENDING_VERIFICATION")
            self.assertEqual(result["result"]["observed"],1.23)

    def test_reviewed_bio_chem_domains_require_facility_and_human_operator(self):
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            exp=self._request(
                bot,domain="biology",mode="wet_lab",adapter="approved-lab",
            )
            bot.register_adapter(
                "approved-lab",
                capabilities=("execute_reviewed_protocol",),
                domains=("biology",),
                physical=True,
                handler=lambda record,context:{"completed":True},
            )
            bot.review(exp["experiment_id"],protocol_reviewed=True,owner_approved=True)
            with self.assertRaises(PermissionError):
                bot.execute(exp["experiment_id"])
            bot.review(
                exp["experiment_id"],protocol_reviewed=True,owner_approved=True,
                facility_approved=True,human_operator_confirmed=True,
            )
            result=bot.execute(exp["experiment_id"])
            self.assertEqual(result["status"],"EXECUTED_PENDING_VERIFICATION")

    def test_physical_nanotechnology_requires_facility_and_human_operator(self):
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            exp=self._request(
                bot,domain="nanotechnology",mode="fabrication",adapter="nano-fab",
            )
            bot.register_adapter(
                "nano-fab",
                capabilities=("fabricate_reviewed_candidate",),
                domains=("nanotechnology",),
                physical=True,
                handler=lambda record,context:{"completed":True},
            )
            bot.review(exp["experiment_id"],protocol_reviewed=True,owner_approved=True)
            with self.assertRaises(PermissionError):
                bot.execute(exp["experiment_id"])
            bot.review(
                exp["experiment_id"],protocol_reviewed=True,owner_approved=True,
                facility_approved=True,human_operator_confirmed=True,
            )
            result=bot.execute(exp["experiment_id"])
            self.assertEqual(result["status"],"EXECUTED_PENDING_VERIFICATION")

    def test_status_declares_adapter_and_verification_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            status=LabBot(Path(td)).status()
            self.assertEqual(status["version"],"krishna-lab-bot-v1")
            self.assertTrue(status["policy"]["rishi_can_request"])
            self.assertTrue(status["policy"]["physical_execution_requires_approval"])
            self.assertFalse(status["policy"]["raw_shell_or_unregistered_hardware_commands"])


if __name__=="__main__":
    unittest.main()
