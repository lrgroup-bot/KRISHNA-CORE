"""Pinned ECC references add guidance without authority or provider changes."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from krishna_core.ecc_workflows import _ROOT, bounded_worker_hint, copied_sources_verified, workflow_for_task
from krishna_core.ephemeral_workers import EphemeralWorkerRuntime
from krishna_core.plugin_runtime import PluginRegistry


class EccLiveAdoptionTests(unittest.TestCase):
    def test_exact_copy_and_tamper_fail_closed(self):
        self.assertTrue(copied_sources_verified())
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "ecc"
            shutil.copytree(_ROOT, copy)
            skill = copy / "skills" / "contract-first" / "SKILL.md"
            skill.write_bytes(skill.read_bytes() + b"\nchanged")
            guidance = workflow_for_task("backend", root=copy)
            self.assertEqual("unavailable", guidance["status"])
            self.assertEqual([], guidance["selected_skills"])
            self.assertEqual("", bounded_worker_hint(guidance))

    def test_plugin_is_local_read_only_and_free(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = PluginRegistry(temp)
            item = next(row for row in registry.list() if row["id"] == "ecc-workflows")
            self.assertEqual("native_ready", item["runtime_state"])
            self.assertEqual(["workflow.advice.read"], item["permissions"])
            self.assertTrue(item["enabled"])
            self.assertTrue(item["free"])

    def test_approved_local_worker_receives_reviewed_hint_only(self):
        class Router:
            prompt = ""
            def coding_plan(self, privacy):
                assert privacy == "local_only"
                return [{"provider": "local-fixture", "model": "fixture", "local": True}]
            def ask(self, provider, prompt):
                assert provider == "local-fixture"
                self.prompt = prompt
                return json.dumps({"summary": "candidate", "findings": []})
        class Memory:
            def remember(self, *args):
                pass
        class Kabach:
            def gate_external_evidence(self, text, source):
                return {"allowed": True}
        router = Router()
        worker = EphemeralWorkerRuntime(router, Memory(), Kabach(), max_workers=1)
        request = {"status": "approved", "approved_by": "KRISHNA",
                   "requested_count": 1, "role": "backend", "manager": "SUDARSHAN"}
        receipt = worker.execute("LR_Group", request, "Read local API contract", "local_only")
        self.assertTrue(receipt["destroyed"])
        self.assertIn("identify consumer provider and authoritative contract", router.prompt)
        self.assertIn("advisory only", router.prompt)
        self.assertNotIn("activate_paid_api", router.prompt)
        self.assertFalse(workflow_for_task("backend")["execution_authorized"])

    def test_unapproved_worker_still_rejected(self):
        worker = EphemeralWorkerRuntime(None, None, None)
        with self.assertRaises(PermissionError):
            worker.execute("LR_Group", {"status": "requested", "role": "backend"}, "task", "local_only")


if __name__ == "__main__":
    unittest.main()
