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


class _Development:
    def __init__(self):
        self.head = "old-head"
        self.branch = "fix/krishna-ui-runtime-verification"
        self.clean = True
        self.resets = []

    def git_snapshot(self, root):
        return {
            "ok": True,
            "branch": self.branch,
            "head": self.head,
            "clean": self.clean,
            "status": "",
        }

    def commit_local(self, root, message, files):
        self.head = "new-head"
        self.clean = True
        return {
            "ok": True,
            "snapshot": self.git_snapshot(root),
            "files": list(files),
            "message": message,
        }

    def reset_verified_head(self, root, target_head, expected_current_head=None):
        if expected_current_head and self.head != expected_current_head:
            return {"ok": False, "blocked": True}
        self.resets.append((self.head, target_head))
        self.head = target_head
        self.clean = True
        return {"ok": True, "snapshot": self.git_snapshot(root)}


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
    def test_safe_verified_krishna_patch_commits_then_schedules_guardian_restart(self):
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
            "post_apply_verification": {"passed": True, "frontend_skipped": True},
        }
        dispatcher = _Dispatcher(run, apply)
        development = _Development()
        restarts = []
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            source.mkdir()
            bot = MrityunjaySelfHealBot(
                Path(td) / "state",
                dispatcher,
                _Projects(),
                development=development,
                source_root=source,
            )
            bot.bind_restart(lambda handoff: restarts.append(dict(handoff)) or {"scheduled": True})
            result = bot.heal_now("KRISHNA", force=True)
            handoff = Path(result["handoff"])
            self.assertTrue(handoff.is_file())

        self.assertEqual(result["status"], "upgrade_restart_scheduled")
        self.assertTrue(result["verified"])
        self.assertFalse(result["live_project_modified"])
        self.assertTrue(result["source_committed"])
        self.assertEqual(result["source_previous_commit"], "old-head")
        self.assertEqual(result["source_new_commit"], "new-head")
        self.assertEqual([x["action"] for x in dispatcher.calls], ["self_heal.run", "self_heal.apply"])
        self.assertIsNone(dispatcher.calls[1]["payload"]["frontend_url"])
        self.assertEqual(len(restarts), 1)
        self.assertEqual(restarts[0]["previous_commit"], "old-head")
        self.assertEqual(restarts[0]["new_commit"], "new-head")

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

    def test_krishna_upgrade_without_clean_git_restart_handoff_is_quarantined(self):
        run = {
            "status": "verified_promotion_ready",
            "phase": "promotion_ready",
            "verified": True,
            "promotion": {
                "promotion_token": "token-2",
                "diff": {"added": [], "changed": ["core/krishna_core/foo.py"], "removed": [], "file_count": 1},
            },
        }
        dispatcher = _Dispatcher(run)
        with tempfile.TemporaryDirectory() as td:
            bot = MrityunjaySelfHealBot(td, dispatcher, _Projects())
            result = bot.heal_now("KRISHNA", force=True)
        self.assertEqual(result["status"], "quarantined")
        self.assertIn("Git/development handoff", result["reason"])
        self.assertEqual([x["action"] for x in dispatcher.calls], ["self_heal.run"])

    def test_restart_handoff_failure_resets_autonomous_commit(self):
        run = {
            "status": "verified_promotion_ready",
            "phase": "promotion_ready",
            "verified": True,
            "promotion": {
                "promotion_token": "token-3",
                "diff": {"added": [], "changed": ["core/krishna_core/foo.py"], "removed": [], "file_count": 1},
            },
        }
        apply = {"verified": True, "rolled_back": False, "promotion": {"promoted": True}}
        dispatcher = _Dispatcher(run, apply)
        development = _Development()
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "source"
            source.mkdir()
            bot = MrityunjaySelfHealBot(
                Path(td) / "state",
                dispatcher,
                _Projects(),
                development=development,
                source_root=source,
            )
            bot.bind_restart(lambda handoff: {"scheduled": False})
            result = bot.heal_now("KRISHNA", force=True)
        self.assertEqual(result["status"], "rolled_back")
        self.assertTrue(result["rolled_back"])
        self.assertEqual(development.head, "old-head")
        self.assertEqual(development.resets, [("new-head", "old-head")])

    def test_action_failed_wakes_mrityunjay_but_self_heal_failure_does_not_loop(self):
        bus = _EventBus()
        dispatcher = _Dispatcher({"status": "healthy", "verified": True})
        with tempfile.TemporaryDirectory() as td:
            bot = MrityunjaySelfHealBot(td, dispatcher, _Projects(), event_bus=bus)
            self.assertIn("action.failed", bus.handlers)
            queued = bus.handlers["action.failed"][0]({
                "event_id": "a1",
                "topic": "action.failed",
                "source": "shared-action-bus",
                "payload": {"project": "KRISHNA", "action": "project.audit.run", "actor": "worker"},
            })
            self.assertTrue(queued["queued"])
            before = bot.status()["queue_depth"]
            ignored = bus.handlers["action.failed"][0]({
                "event_id": "a2",
                "topic": "action.failed",
                "source": "shared-action-bus",
                "payload": {"project": "KRISHNA", "action": "self_heal.run", "actor": "mrityunjay"},
            })
            self.assertIsNone(ignored)
            self.assertEqual(bot.status()["queue_depth"], before)

    def test_sensitive_subsystem_change_is_quarantined(self):
        result = MrityunjaySelfHealBot.auto_apply_eligibility({
            "added": [],
            "changed": ["core/krishna_core/security_soc.py"],
            "removed": [],
            "file_count": 1,
        })
        self.assertFalse(result["eligible"])
        self.assertTrue(any("sensitive subsystem" in reason for reason in result["reasons"]))

    def test_new_files_are_quarantined_for_clean_rollback(self):
        result = MrityunjaySelfHealBot.auto_apply_eligibility({
            "added": ["core/krishna_core/new_worker.py"],
            "changed": [],
            "removed": [],
            "file_count": 1,
        })
        self.assertFalse(result["eligible"])
        self.assertIn("automatic new file creation is forbidden", result["reasons"])

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
        self.assertIn("orch.mrityunjay.bind_restart(_schedule_mrityunjay_restart)", server)
        start=(root/"scripts"/"START_KRISHNA.ps1").read_text(encoding="utf-8")
        self.assertIn("Complete-MrityunjayHandoff", start)
        self.assertIn("Restore-MrityunjayPreviousSource", start)
        self.assertIn("push origin $branch", start)
        self.assertIn("verified deployment/acceptance failed", start)
        self.assertIn("ls-remote origin", start)
        self.assertIn("retaining handoff for retry rather than guessing rollback", start)


if __name__ == "__main__":
    unittest.main()
