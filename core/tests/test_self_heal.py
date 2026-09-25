import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

from krishna_core.development_operator import DevelopmentOperator
from krishna_core.self_heal import KrishnaSelfHealRuntime


class _ParallelDevelopment:
    def __init__(self, barrier):
        self.barrier = barrier
        self.staging_root = None

    def verify(self, root, checks):
        self.barrier.wait(timeout=2)
        return {"verified": True, "steps": [{"name": x, "ok": True} for x in checks]}


class _ParallelPerfection:
    def __init__(self, barrier):
        self.barrier = barrier

    def browser_audit(self, url, viewports=None):
        self.barrier.wait(timeout=2)
        return {"ok": True, "viewports": [], "geometry_ok": True}


class _NoopRouter:
    pass


class _RepairRouter:
    def __init__(self):
        self.calls = []

    def local_model_status(self, task="general"):
        model = "qwen2.5-coder:7b" if task == "coding" else "qwen3.5:4b"
        return {"selected_model": model, "primary_model": model}

    def local(self, prompt, model=None, task="general", keep_alive=None):
        self.calls.append({"model": model, "task": task, "keep_alive": keep_alive, "prompt": prompt})
        if task == "coding":
            return json.dumps({
                "summary": "fix objective defect",
                "files": [{"path": "app.py", "content": "VALUE = 2\n"}],
            })
        return "Root cause is the incorrect VALUE constant in app.py."

    def available(self):
        return []


class _FallbackRepairRouter:
    def __init__(self):
        self.calls = []

    def local_model_status(self, task="general"):
        return {
            "selected_model": "qwen3.5:4b",
            "primary_model": "qwen3.5:4b",
            "installed_candidates": ["qwen3.5:4b", "gemma3:1b"],
            "service_available": True,
            "available": True,
        }

    def local(self, prompt, model=None, task="general", keep_alive=None):
        self.calls.append({
            "model": model,
            "task": task,
            "keep_alive": keep_alive,
        })
        if model == "qwen3.5:4b":
            raise RuntimeError("model requires more memory")
        return "fallback diagnosis"


class _CloudReviewRouter:
    def __init__(self):
        self.prompts = []

    def available(self):
        return [{
            "provider": "openrouter-free",
            "available": True,
            "local": False,
            "free_only": True,
        }]

    def ask(self, provider, prompt):
        self.prompts.append((provider, prompt))
        return '{"verdict":"reviewed","concerns":[],"suggested_check":"none"}'


class _ReviewerDiscoveryFailRouter:
    def available(self):
        raise RecursionError("maximum recursion depth exceeded")


class SelfHealTests(unittest.TestCase):
    def test_frontend_and_backend_verification_start_in_parallel(self):
        barrier = threading.Barrier(2)
        runtime = KrishnaSelfHealRuntime(
            _NoopRouter(),
            _ParallelDevelopment(barrier),
            _ParallelPerfection(barrier),
        )
        result = runtime.verify_parallel(".", ["pytest"], "http://127.0.0.1:8766", full=False)
        self.assertTrue(result["parallel"])
        self.assertTrue(result["passed"])
        self.assertTrue(result["backend"]["verified"])
        self.assertTrue(result["frontend"]["passed"])

    def test_direct_ollama_diagnosis_then_coding_repair_uses_one_shot_models(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            project.mkdir()
            (project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            staging = root / "staging"

            router = _RepairRouter()
            development = DevelopmentOperator(Mock(), staging_root=staging)
            runtime = KrishnaSelfHealRuntime(router, development, Mock())
            runtime.model_review = Mock(return_value=[])

            initial = {
                "parallel": True,
                "passed": False,
                "backend": {"verified": False, "steps": [{"name": "pytest", "ok": False}]},
                "frontend": {"available": False, "passed": True},
            }
            narrow = {
                "parallel": True,
                "passed": True,
                "backend": {"verified": True, "steps": [{"name": "pytest", "ok": True}]},
                "frontend": {"available": False, "passed": True},
            }
            full = {
                "parallel": True,
                "passed": True,
                "backend": {"verified": True, "steps": [{"name": "pytest", "ok": True}]},
                "frontend": {"available": False, "passed": True},
            }
            runtime.verify_parallel = Mock(side_effect=[initial, narrow, full])

            result = runtime.run(
                project="KRISHNA",
                project_root=str(project),
                checks=["pytest"],
                frontend_url=None,
                privacy="local_only",
                components=["app"],
                max_rounds=1,
            )

            self.assertEqual(result["status"], "verified_candidate")
            self.assertTrue(result["verified"])
            candidate = Path(result["candidate_root"])
            self.assertEqual((candidate / "app.py").read_text(encoding="utf-8"), "VALUE = 2\n")
            self.assertEqual(router.calls[0]["model"], "qwen3.5:4b")
            self.assertEqual(router.calls[0]["task"], "reasoning")
            self.assertEqual(router.calls[0]["keep_alive"], 0)
            self.assertEqual(router.calls[1]["model"], "qwen2.5-coder:7b")
            self.assertEqual(router.calls[1]["task"], "coding")
            self.assertEqual(router.calls[1]["keep_alive"], 0)

    def test_direct_local_falls_back_to_next_installed_model(self):
        router = _FallbackRepairRouter()
        runtime = KrishnaSelfHealRuntime(router, Mock(), Mock())
        result = runtime._direct_local("diagnose", "reasoning")
        self.assertEqual(result["model"], "gemma3:1b")
        self.assertEqual(result["text"], "fallback diagnosis")
        self.assertEqual(
            [call["model"] for call in router.calls],
            ["qwen3.5:4b", "gemma3:1b"],
        )
        self.assertTrue(all(call["keep_alive"] == 0 for call in router.calls))

    def test_failed_narrow_repair_discards_candidate_and_preserves_live_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            project.mkdir()
            live = project / "app.py"
            live.write_text("VALUE = 1\n", encoding="utf-8")
            staging = root / "staging"

            router = _RepairRouter()
            development = DevelopmentOperator(Mock(), staging_root=staging)
            runtime = KrishnaSelfHealRuntime(router, development, Mock())
            runtime.model_review = Mock(return_value=[])

            failed = {
                "parallel": True,
                "passed": False,
                "backend": {"verified": False, "steps": [{"name": "pytest", "ok": False}]},
                "frontend": {"available": False, "passed": True},
            }
            runtime.verify_parallel = Mock(side_effect=[failed, failed])

            result = runtime.run(
                project="KRISHNA",
                project_root=str(project),
                checks=["pytest"],
                frontend_url=None,
                privacy="local_only",
                max_rounds=1,
            )

            self.assertEqual(result["status"], "rejected")
            self.assertTrue(result["rolled_back"])
            self.assertEqual(live.read_text(encoding="utf-8"), "VALUE = 1\n")
            self.assertEqual(list(staging.glob("candidate-*")), [])

    def test_verification_lane_recursion_is_reported_without_repair_or_live_mutation(self):
        class _RecursiveDevelopment:
            staging_root = None
            def verify(self, root, checks):
                raise RecursionError("maximum recursion depth exceeded")

        class _HealthyFrontend:
            def browser_audit(self, url, viewports=None):
                return {"ok": True, "viewports": [], "geometry_ok": True}
            def accessibility_verify(self, url):
                return {"passed": True}
            def performance_verify(self, report, required=False):
                return {"passed": True}
            def browser_chaos_verify(self, url):
                return {"passed": True}

        runtime = KrishnaSelfHealRuntime(_NoopRouter(), _RecursiveDevelopment(), _HealthyFrontend())
        result = runtime.run(
            project="KRISHNA",
            project_root=".",
            checks=["python-tests"],
            frontend_url="http://127.0.0.1:8766",
            privacy="local_only",
            max_rounds=1,
        )
        self.assertEqual(result["status"], "verification_error")
        self.assertFalse(result["verified"])
        self.assertFalse(result["live_project_modified"])
        self.assertEqual(result["initial_verification"]["verification_errors"][0]["lane"], "backend")
        self.assertEqual(result["initial_verification"]["verification_errors"][0]["type"], "RecursionError")

    def test_candidate_stage_recursion_returns_phase_safe_error(self):
        class _RecursiveStageDevelopment:
            staging_root = None
            def stage(self, root, files):
                raise RecursionError("maximum recursion depth exceeded")

        runtime = KrishnaSelfHealRuntime(_NoopRouter(), _RecursiveStageDevelopment(), Mock())
        runtime.verify_parallel = Mock(return_value={
            "parallel": True,
            "passed": False,
            "verification_errors": [],
            "backend": {"verified": False, "steps": [{"name": "python-tests", "ok": False}]},
            "frontend": {"available": False, "passed": True},
        })
        result = runtime.run(
            project="KRISHNA",
            project_root=".",
            checks=["python-tests"],
            frontend_url=None,
            privacy="local_only",
            max_rounds=1,
        )
        self.assertEqual(result["status"], "self_heal_error")
        self.assertEqual(result["phase"], "candidate_stage")
        self.assertEqual(result["error"]["type"], "RecursionError")
        self.assertFalse(result["live_project_modified"])

    def test_reviewer_discovery_recursion_is_advisory_only(self):
        runtime = KrishnaSelfHealRuntime(_ReviewerDiscoveryFailRouter(), Mock(), Mock())
        rows = runtime.model_review("KRISHNA", "local_only", {
            "parallel": True,
            "passed": True,
            "backend": {"verified": True, "steps": []},
            "frontend": {"available": False, "passed": True},
        })
        self.assertEqual(rows[0]["provider"], "reviewer-discovery")
        self.assertFalse(rows[0]["ok"])
        self.assertIn("RecursionError", rows[0]["error"])

    def test_stage_inside_project_krishna_state_does_not_recurse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "project"
            root.mkdir()
            (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            state = root / ".krishna_state"
            state.mkdir()
            (state / "runtime.json").write_text('{"secret":"transient"}', encoding="utf-8")
            staging = state / "promotion-candidates"

            development = DevelopmentOperator(Mock(), staging_root=staging)
            staged = development.stage(root, [])

            candidate = Path(staged["candidate_root"])
            self.assertTrue((candidate / "app.py").is_file())
            self.assertFalse((candidate / ".krishna_state").exists())
            staged_candidates=list(staging.glob("candidate-*"))
            self.assertEqual(len(staged_candidates),1)
            self.assertTrue(os.path.samefile(staged_candidates[0],candidate))

    def test_cloud_review_receives_sanitized_verification_only(self):
        router = _CloudReviewRouter()
        runtime = KrishnaSelfHealRuntime(router, Mock(), Mock())
        report = {
            "parallel": True,
            "passed": False,
            "backend": {
                "verified": False,
                "steps": [{"name": "pytest", "ok": False, "detail": "SECRET_SOURCE_XYZ"}],
            },
            "frontend": {"available": True, "passed": False, "browser": {"ok": False}},
        }
        rows = runtime.model_review("KRISHNA", "approved_cloud", report)
        self.assertEqual(rows[0]["provider"], "openrouter-free")
        self.assertTrue(rows[0]["sanitized"])
        self.assertNotIn("SECRET_SOURCE_XYZ", router.prompts[0][1])


if __name__ == "__main__":
    unittest.main()
