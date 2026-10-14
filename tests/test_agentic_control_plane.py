from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from krishna_core.agentic_control_plane import (
    AgenticEngineeringControlPlane,
    AgenticPreToolPolicy,
)


class _Scheduler:
    def plan(self, tasks, **kwargs):
        return {
            "tasks": list(tasks),
            "deadline_minutes": kwargs["deadline_minutes"],
            "local_execution_slots": kwargs["local_slots"],
            "execution_truth": {"code_execution_host": kwargs["execution_host"]},
        }


class _Verifier:
    def judge(self, checks, evidence=None):
        failed = [x for x in checks if x.get("passed") is False]
        return {
            "status": "FAIL" if failed else "PASS",
            "passed": not failed,
            "checks": checks,
            "evidence": list(evidence or []),
        }


class AgenticControlPlaneTests(unittest.TestCase):
    def test_pretool_blocks_force_push_and_merge(self):
        policy = AgenticPreToolPolicy()
        self.assertEqual(
            policy.evaluate(tool_name="bash", tool_args={"command": "git push --force origin x"})["permissionDecision"],
            "deny",
        )
        self.assertEqual(
            policy.evaluate(tool_name="bash", tool_args={"command": "gh pr merge 22 --squash"})["permissionDecision"],
            "deny",
        )

    def test_pretool_blocks_secret_file_edits(self):
        policy = AgenticPreToolPolicy()
        decision = policy.evaluate(tool_name="edit", tool_args={"path": "core/.env", "content": "x"})
        self.assertEqual(decision["permissionDecision"], "deny")

    def test_additive_mission_artifacts_and_final_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            plane = AgenticEngineeringControlPlane(tmp, scheduler=_Scheduler(), verifier=_Verifier())
            mission = plane.new_mission("KRISHNA", "test additive agentic layer", provider="copilot")
            plan = plane.plan_engineering(
                mission,
                [{"id": "t1", "role": "developer", "estimate_minutes": 5}],
                deadline_minutes=30,
                local_slots=1,
                execution_host="isolated_test",
            )
            self.assertEqual(plan["local_execution_slots"], 1)

            not_ready = plane.finalize(mission)
            self.assertFalse(not_ready["ready_for_governed_promotion"])

            plane.record(mission, "TEST_RESULTS", {"passed": True, "tests": 3})
            verdict = plane.independent_review(
                mission,
                checks=[{"name": "unit", "passed": True}],
                evidence=["test-log"],
            )
            self.assertTrue(verdict["passed"])

            ready = plane.finalize(mission)
            self.assertTrue(ready["ready_for_governed_promotion"])
            self.assertFalse(ready["auto_merge"])
            self.assertEqual(ready["missing_required_artifacts"], [])

    def test_provider_contract_has_no_authority(self):
        contract = AgenticEngineeringControlPlane.provider_contract("codex")
        self.assertTrue(contract["optional"])
        self.assertFalse(contract["billable_dependency_allowed"])
        self.assertFalse(contract["merge_authority"])
        self.assertFalse(contract["may_be_required_for_runtime"])


if __name__ == "__main__":
    unittest.main()
