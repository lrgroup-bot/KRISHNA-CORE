import os
import unittest
from unittest.mock import patch

from krishna_core.hybrid_implementation import execute_hybrid_implementation


class HybridImplementationTests(unittest.TestCase):
    def adapters(self, calls, verified=True):
        def research(**kwargs):
            calls.append("research")
            return {"verified_free": verified, "summary": "Public API docs",
                    "sources": [{"url": "https://example.org/docs", "title": "Docs"}]}
        def plan(**kwargs):
            calls.append("plan")
            return {"steps": ["local review"]}
        def build(**kwargs):
            self.assertTrue(kwargs["isolated"])
            calls.append("build")
            return {"artifact": "isolated"}
        def test(**kwargs):
            calls.append("test")
            return {"passed": True}
        def learn(**kwargs):
            calls.append("learn")
            return {"stored": True}
        return dict(research=research, local_plan=plan, local_build=build,
                    local_test=test, local_learn=learn)

    @patch.dict(os.environ, {"KRISHNA_STRICT_ZERO_CREDIT": "1"})
    def test_requires_public_context_approval(self):
        calls = []
        result = execute_hybrid_implementation(
            task="Research", project="KRISHNA", approved_public_context=False,
            **self.adapters(calls))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(calls, [])

    @patch.dict(os.environ, {"KRISHNA_STRICT_ZERO_CREDIT": "1"})
    def test_requires_verified_free_provider(self):
        calls = []
        result = execute_hybrid_implementation(
            task="Research", project="KRISHNA", approved_public_context=True,
            **self.adapters(calls, verified=False))
        self.assertEqual(result["reason"], "cloud_free_not_verified")
        self.assertEqual(calls, ["research"])

    @patch.dict(os.environ, {"KRISHNA_STRICT_ZERO_CREDIT": "1"})
    def test_build_requires_explicit_approval(self):
        calls = []
        result = execute_hybrid_implementation(
            task="Research", project="KRISHNA", approved_public_context=True,
            **self.adapters(calls))
        self.assertEqual(result["status"], "awaiting_approval")
        self.assertEqual(calls, ["research", "plan"])

    @patch.dict(os.environ, {"KRISHNA_STRICT_ZERO_CREDIT": "1"})
    def test_approved_workflow_runs_local_build_and_tests(self):
        calls = []
        result = execute_hybrid_implementation(
            task="Research", project="KRISHNA", approved_public_context=True,
            approve_build=True, **self.adapters(calls))
        self.assertEqual(result["status"], "verified")
        self.assertEqual(calls, ["research", "plan", "build", "test", "learn"])

    @patch.dict(os.environ, {"KRISHNA_STRICT_ZERO_CREDIT": "0"})
    def test_paid_mode_is_rejected(self):
        with self.assertRaises(PermissionError):
            execute_hybrid_implementation(
                task="Research", project="KRISHNA", approved_public_context=True,
                **self.adapters([]))


if __name__ == "__main__":
    unittest.main()
