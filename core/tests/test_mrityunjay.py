from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from krishna_core.mrityunjay import MrityunjaySelfHealBot


@dataclass
class _Policy:
    role: str = "active"
    verification_checks: tuple[str, ...] = ("python-tests",)


class _Projects:
    def __init__(self, policy=None):
        self.policy = policy or _Policy()

    def get(self, name):
        return self.policy if name == "KRISHNA" else None


class _EventBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, topic, handler):
        self.handlers.setdefault(topic, []).append(handler)


class _Dispatcher:
    def __init__(self, run_result, apply_result=None):
        self.run_result = run_result
        self.apply_result = apply_result or {}
        self.calls = []

    def __call__(self, action, payload=None, **context):
        self.calls.append({"action": action, "payload": dict(payload or {}), "context": dict(context)})
        if action == "self_heal.run":
            return {"status": "completed", "result": dict(self.run_result)}
        if action == "self_heal.apply":
            return {"status": "completed", "result": dict(self.apply_result)}
        raise AssertionError(action)


class MrityunjayTests(unittest.TestCase):
    def test_safe_verified_source_patch_can_auto_apply(self):
        run = {
            "status": "verified_promotion_ready",
            "phase": "promotion_ready",
            "verified": True,
            "candidate_root": "candidate",
            "promotion": {
                "promotion_token": "token-1",
                "diff": {"added": [], "changed": ["core/krishna_core/foo.py"], "removed": [], "file_count": 1},
            },
        }
        apply = {
            "verified": True,
            "rolled_back": False,
            "promotion": {"promoted": True, "rolled_back": False},
            "post_apply_verification": {"passed": True},
        }
        dispatcher = _Dispatcher(run, apply)
        with tempfile.TemporaryDirectory() as td:
            bot = MrityunjaySelfHealBot(td, dispatcher, _Projects())
            result = bot.heal_now("KRISHNA", force=True)

        self.assertEqual(result["status"], "healed")
        self.assertTrue(result["verified"])
        self.assertTrue(result["live_project_modified"])
        self.assertEqual([x["action"] for x in dispatcher.calls], ["self_heal.run", "self_heal.apply"])
        apply_call = dispatcher.calls[1]
        self.assertTrue(apply_call["context"]["approved"])
        self.assertEqual(apply_call["context"]["source"], "system")
        self.assertEqual(apply_call["context"]["actor"], "mrityunjay")

    def test_control_plane_change_is_quarantined_not_auto_applied(self):
        run = {
            "status": "verified_promotion_ready",
            "phase": "promotion_ready",
            "verified": True,
            "candidate_root": "candidate",
            "promotion": {
                "promotion_token": "token-risk",
                "diff": {"added": [], "changed": ["core/krishna_core/server.py"], "removed": [], "file_count": 1},
            },
        }
        dispatcher = _Dispatcher(run)
        with tempfile.TemporaryDirectory() as td:
            bot = MrityunjaySelfHealBot(td, dispatcher, _Projects())
            result = bot.heal_now("KRISHNA", force=True)

        self.assertEqual(result["status"], "quarantined")
        self.assertFalse(result["live_project_modified"])
        self.assertEqual([x["action"] for x in dispatcher.calls], ["self_heal.run"])
        self.assertTrue(any("control-plane" in reason for reason in result["auto_apply"]["reasons"]))

    def test_deletions_and_frontend_framework_changes_are_not_auto_applied(self):
        deletion = MrityunjaySelfHealBot.auto_apply_eligibility({
            "added": [], "changed": [], "removed": ["core/krishna_core/old.py"], "file_count": 1,
        })
        self.assertFalse(deletion["eligible"])
        self.assertIn("automatic deletion is forbidden", deletion["reasons"])

        spatial = MrityunjaySelfHealBot.auto_apply_eligibility({
            "added": [], "changed": ["app/spatial-ui/src/App.tsx"], "removed": [], "file_count": 1,
        })
        self.assertFalse(spatial["eligible"])
        self.assertTrue(any("high-risk path blocked" in reason for reason in spatial["reasons"]))

    def test_healthy_run_never_calls_apply(self):
        dispatcher = _Dispatcher({
            "status": "healthy",
            "phase": "complete",
            "verified": True,
            "live_project_modified": False,
        })
        with tempfile.TemporaryDirectory() as td:
            bot = MrityunjaySelfHealBot(td, dispatcher, _Projects())
            result = bot.heal_now("KRISHNA", force=True)
        self.assertEqual(result["status"], "healthy")
        self.assertEqual([x["action"] for x in dispatcher.calls], ["self_heal.run"])

    def test_failure_event_is_queued_for_active_project(self):
        bus = _EventBus()
        dispatcher = _Dispatcher({"status": "healthy", "verified": True})
        with tempfile.TemporaryDirectory() as td:
            bot = MrityunjaySelfHealBot(td, dispatcher, _Projects(), event_bus=bus)
            self.assertIn("TEST_FAILED", bus.handlers)
            out = bus.handlers["TEST_FAILED"][0]({
                "event_id": "e1",
                "topic": "TEST_FAILED",
                "source": "verification",
                "payload": {"project": "KRISHNA", "check": "python-tests"},
            })
            self.assertTrue(out["queued"])
            self.assertEqual(bot.status()["queue_depth"], 1)

    def test_status_declares_bounded_autonomous_repair_policy(self):
        with tempfile.TemporaryDirectory() as td:
            bot = MrityunjaySelfHealBot(td, _Dispatcher({"status": "healthy"}), _Projects())
            status = bot.status()
        self.assertEqual(status["name"], "MRITYUNJAY")
        self.assertTrue(status["automatic_low_risk_apply"])
        self.assertTrue(status["transactional_rollback_required"])
        self.assertIn("high-risk", status["human_intervention"])


class MrityunjayWiringContractTests(unittest.TestCase):
    def test_orchestrator_and_server_wire_mrityunjay(self):
        root = Path(__file__).resolve().parents[2]
        orchestrator = (root / "core" / "krishna_core" / "orchestrator.py").read_text(encoding="utf-8")
        server = (root / "core" / "krishna_core" / "server.py").read_text(encoding="utf-8")
        for token in (
            "MrityunjaySelfHealBot",
            '"mrityunjay.status"',
            '"mrityunjay.trigger"',
            '"mrityunjay.heal"',
            '"mrityunjay","permanent KRISHNA self-heal and recovery supervisor"',
        ):
            self.assertIn(token, orchestrator)
        self.assertIn("_mrityunjay = orch.mrityunjay", server)
        self.assertIn("_mrityunjay.start()", server)
        self.assertIn('("mrityunjay", _mrityunjay.stop)', server)


if __name__ == "__main__":
    unittest.main()
