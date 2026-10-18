"""Integration checks against KRISHNA's *real* action bus and project bootstrap.

No REA/MiroFish services or model calls are needed; the adapter is injected.
These tests prove permission boundaries and canonical handoffs, not engine accuracy.
"""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from krishna_core.automation_bus import AutomationBus
from krishna_core.permission_runtime import PermissionRuntime
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.project_bootstrap import REQUIRED_CONTEXT
from krishna_core.shared_action_bus import SharedActionBus
from krishna_core.sudarshan_project_orchestrator import SudarshanProjectOrchestrator
from krishna_core.sudarshan_canonical_integration import SudarshanCanonicalIntegration

EVIDENCE = "sha256:" + "a" * 64


class PendingMemory:
    def __init__(self):
        self.entries = {}

    def gyan_pending(self, approval_id):
        return self.entries.get(approval_id)


class GyanStub:
    def __init__(self):
        self.memory = PendingMemory()
        self.calls = []

    def propose(self, project, topic, lesson, evidence=None, confidence=0.0,
                source="", verified=False, memory_kind="", provenance=None):
        approval_id = "review-%d" % (len(self.calls) + 1)
        self.calls.append({"project": project, "topic": topic, "verified": verified,
                           "confidence": confidence, "kind": memory_kind,
                           "source": source, "evidence": evidence})
        self.memory.entries[approval_id] = {
            "project": project, "topic": topic, "source": source, "verified": verified,
            "status": "pending", "evidence": evidence,
        }
        return {"approval_id": approval_id, "stored": False}


class BrahmagyanStub:
    def __init__(self):
        self.missions = []

    def create_mission(self, project, topic, **kwargs):
        self.missions.append({"project": project, "topic": topic, **kwargs})
        return {"mission_id": "mission-%d" % len(self.missions)}


class CanonicalBridgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.project = "TEST-PROJECT"
        self.repo = str(Path(self.folder.name).resolve())
        self.context = {key: "test" for key in REQUIRED_CONTEXT}
        self.context["repository"] = self.repo
        self.gyan = GyanStub()
        self.brahmagyan = BrahmagyanStub()
        self.executions = []
        def runner(engine, spec, *, authorized):
            self.executions.append((engine, spec, authorized))
            return SimpleNamespace(engine=engine, status="passed",
                                   evidence_id=EVIDENCE, summary="Unverified local observation")
        self.runner = runner
        self.bridge = SudarshanCanonicalIntegration(
            SudarshanProjectOrchestrator(), self.gyan, self.brahmagyan,
            runner=self.runner)
        self.bus = SharedActionBus(
            AutomationBus(), PolicyKernel(Path(self.folder.name) / "policy"),
            permission_resolver=PermissionRuntime().authorize)
        self.bridge.register(self.bus)
        self.payload = {
            "project_id": self.project, "project_context": self.context,
            "engine": "REA", "topic": "Button behavior",
            "spec": {"root": self.repo, "target": self.repo,
                     "rea_executable": "/not-executed-by-mock"},
        }

    def dispatch(self, action, payload, *, approved=True, source="pc",
                 project=None, permissions=(), idempotency_key=None):
        return self.bus.dispatch(
            action, payload, project=project or self.project,
            source=source, approved=approved, permissions=permissions,
            idempotency_key=idempotency_key)

    def test_approved_rea_observation_queues_unverified_canonical_knowledge(self):
        receipt = self.dispatch("sudarshan.research.observe", self.payload)
        result = receipt["result"]
        self.assertEqual(result["state"], "PENDING_GYAN_APPROVAL")
        self.assertEqual(result["evidence_id"], EVIDENCE)
        self.assertFalse(result["release_ready"])
        self.assertEqual(len(self.gyan.calls), 1)
        self.assertFalse(self.gyan.calls[0]["verified"])
        self.assertEqual(self.gyan.calls[0]["kind"], "evidence")
        self.assertEqual(self.gyan.calls[0]["source"], "sudarshan:REA")
        self.assertEqual(len(self.executions), 1)

    def test_unapproved_source_is_blocked_before_adapter_execution(self):
        with self.assertRaises(PermissionError):
            self.dispatch("sudarshan.research.observe", self.payload, approved=False)
        self.assertEqual(self.executions, [])

    def test_agents_cannot_bypass_local_owner_source(self):
        with self.assertRaises(PermissionError):
            self.dispatch("sudarshan.research.observe", self.payload, source="agent",
                          approved=True, permissions=("research.inspect", "memory.write"))
        self.assertEqual(self.executions, [])

    def test_project_scope_and_incomplete_bootstrap_block(self):
        with self.assertRaises(PermissionError):
            self.dispatch("sudarshan.research.observe", self.payload, project="OTHER")
        modified = dict(self.payload, project_context={})
        with self.assertRaises(PermissionError):
            self.dispatch("sudarshan.research.observe", modified)
        self.assertEqual(self.executions, [])

    def test_rea_root_must_match_project_repository(self):
        changed = dict(self.payload, spec={
            "root": str(Path(self.folder.name).parent), "target": self.repo,
            "rea_executable": "/not-executed-by-mock"})
        with self.assertRaises(PermissionError):
            self.dispatch("sudarshan.research.observe", changed)
        self.assertEqual(self.executions, [])

    def test_mirofish_project_scope_must_match(self):
        changed = dict(self.payload, engine="MiroFish",
                       spec={"project_id": "OTHER", "simulation_id": "sim1"})
        with self.assertRaises(PermissionError):
            self.dispatch("sudarshan.research.observe", changed)
        changed["spec"] = {"project_id": self.project, "simulation_id": "sim1"}
        result = self.dispatch("sudarshan.research.observe", changed)["result"]
        self.assertEqual(result["engine"], "MiroFish")
        self.assertEqual(self.gyan.calls[-1]["source"], "sudarshan:MiroFish")

    def test_only_digest_backed_success_is_accepted(self):
        self.bridge.runner = lambda engine, spec, *, authorized: SimpleNamespace(
            engine=engine, status="passed", evidence_id="sample", summary="fake")
        with self.assertRaises(ValueError):
            self.dispatch("sudarshan.research.observe", self.payload)
        self.assertFalse(self.gyan.calls)

    def test_failed_adapter_creates_no_gyan_proposal(self):
        self.bridge.runner = lambda engine, spec, *, authorized: SimpleNamespace(
            engine=engine, status="not_tested", evidence_id="", summary="no runtime")
        with self.assertRaises(RuntimeError):
            self.dispatch("sudarshan.research.observe", self.payload)
        self.assertFalse(self.gyan.calls)

    def test_pending_evidence_routes_to_real_brahmagyan_interface(self):
        pending = self.dispatch("sudarshan.research.observe", self.payload)["result"]
        handoff = self.dispatch("sudarshan.research.mission", {
            "project_id": self.project, "approval_id": pending["approval_id"]})["result"]
        self.assertEqual(handoff["state"], "RESEARCH_PLANNED")
        self.assertEqual(handoff["mission_id"], "mission-1")
        self.assertEqual(handoff["evidence_ids"], [EVIDENCE])
        self.assertFalse(handoff["gyan_promoted"])
        self.assertEqual(self.brahmagyan.missions[0]["knowledge_track"], "engineering")
        self.assertEqual(self.brahmagyan.missions[0]["target_level"], "L3")

    def test_cross_project_pending_research_rejected(self):
        pending = self.dispatch("sudarshan.research.observe", self.payload)["result"]
        self.gyan.memory.entries[pending["approval_id"]]["project"] = "OTHER"
        with self.assertRaises(PermissionError):
            self.dispatch("sudarshan.research.mission", {
                "project_id": self.project, "approval_id": pending["approval_id"]})
        self.assertEqual(self.brahmagyan.missions, [])

    def test_replay_uses_existing_action_bus_idempotency(self):
        first = self.dispatch("sudarshan.research.observe", self.payload,
                              idempotency_key="observe-one")
        again = self.dispatch("sudarshan.research.observe", self.payload,
                              idempotency_key="observe-one")
        self.assertEqual(first["action_id"], again["action_id"])
        self.assertTrue(again["idempotent_replay"])
        self.assertEqual(len(self.executions), 1)


if __name__ == "__main__":
    unittest.main()
