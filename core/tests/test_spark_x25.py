import re
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from krishna_core.model_scout import ModelCandidate, ModelScout
from krishna_core.spark_x25 import SparkX25Manager


class CountingGovernor:
    def __init__(self):
        self.entries = 0

    @contextmanager
    def job(self, timeout=0):
        self.entries += 1
        yield


def fake_runner(prompt, ctx):
    needle = re.search(r"KRN-[A-F0-9]{20}", prompt)
    if needle:
        text = needle.group(0)
    elif "project.inspect" in prompt:
        text = '{"action":"project.inspect","arguments":{"project":"LRS Motors"}}'
    elif "Return action STOP" in prompt:
        text = '{"action":"STOP","arguments":{}}'
    else:
        text = "ok"
    return {
        "text": text,
        "elapsed_s": 0.01,
        "tokens_per_s": 42.0,
        "eval_count": 10,
        "eval_duration_ns": 250_000_000,
    }


class SparkX25Tests(unittest.TestCase):
    def make_manager(self, td, governor=None):
        root = Path(td)
        scout = ModelScout(root / "model-scout.json")
        manager = SparkX25Manager(
            root / "spark",
            scout,
            resource_governor=governor,
        )
        return manager, scout

    @staticmethod
    def healthy_ollama(installed=None):
        return {
            "available": True,
            "version": "0.34.1",
            "minimum_version": "0.34.1",
            "architecture_supported": True,
            "installed_models": list(installed or []),
            "model_root": r"E:\\Krishna-The GOD\\ollama-models",
            "windows_e_drive_policy_ok": True,
            "default_windows_model_root": r"E:\\Krishna-The GOD\\ollama-models",
            "error": None,
        }

    def test_official_metadata_stays_candidate_only(self):
        with tempfile.TemporaryDirectory() as td:
            manager, _ = self.make_manager(td)
            meta = manager.candidate_metadata("spark-x2.5-4b")
            mobile = manager.mobile_plan()
            self.assertEqual(meta["family"], "Spark-X2.5")
            self.assertEqual(meta["license"], "Apache-2.0")
            self.assertFalse(meta["vision"])
            self.assertFalse(meta["audio"])
            self.assertFalse(meta["cloud"])
            self.assertFalse(meta["tool_calling"]["verified"])
            self.assertFalse(meta["long_context"]["verified"])
            self.assertIn("litert", meta["runtime_support"]["not_verified_upstream"])
            self.assertFalse(mobile["packaged_in_apk"])
            self.assertFalse(mobile["automatic_download"])
            self.assertFalse(mobile["runtime_verified_in_krishna_mobile"])
            self.assertIn("UNVERIFIED", mobile["litert_status"])

    def test_discovery_is_idempotent_and_preserves_promoted_scout_state(self):
        with tempfile.TemporaryDirectory() as td:
            manager, scout = self.make_manager(td)
            key = "spark-x2.5-4b"
            spec = manager.SPECS[key]
            accepted = scout.evaluate(ModelCandidate(
                model_id=spec.model_id,
                source="local",
                task=spec.intended_role.lower(),
                license=manager.LICENSE,
                local_capable=True,
                quality=0.95,
                latency_ms=100,
                benchmark_ref="bench-existing",
            ))
            self.assertTrue(accepted["accepted"])
            scout.promote(
                spec.model_id,
                review_ref="review-existing",
                verification_ref="verify-existing",
            )
            lifecycle = manager._load_lifecycle()
            state = lifecycle["models"][key]
            state.update({
                "stage": "ROUTING_ENABLED",
                "benchmark_ref": "bench-existing",
                "reviewed": True,
                "verified": True,
                "routing_enabled": True,
                "review_ref": "review-existing",
                "verification_ref": "verify-existing",
            })
            manager._save_lifecycle(lifecycle)
            manager.ollama_status = lambda: self.healthy_ollama([])

            first = manager.discover()
            second = manager.discover()
            row = scout.rows[spec.model_id]
            saved = manager._load_lifecycle()["models"][key]

            self.assertEqual(row["benchmark_ref"], "bench-existing")
            self.assertTrue(row["reviewed"])
            self.assertTrue(row["verified"])
            self.assertTrue(row["routing_enabled"])
            self.assertEqual(saved["stage"], "ROUTING_ENABLED")
            self.assertEqual(saved["review_ref"], "review-existing")
            self.assertEqual(saved["verification_ref"], "verify-existing")
            self.assertTrue(first["candidates"][key]["lifecycle"]["routing_enabled"])
            self.assertTrue(second["candidates"][key]["lifecycle"]["routing_enabled"])

    def test_discovery_marks_installed_model_downloaded_without_promoting(self):
        with tempfile.TemporaryDirectory() as td:
            manager, scout = self.make_manager(td)
            key = "spark-x2.5-4b"
            model = manager.SPECS[key].model_id
            manager.ollama_status = lambda: self.healthy_ollama([model + ":latest"])
            result = manager.discover()

            self.assertEqual(result["candidates"][key]["lifecycle"]["stage"], "DOWNLOADED")
            self.assertFalse(result["candidates"][key]["lifecycle"]["routing_enabled"])
            self.assertFalse(scout.rows[model]["accepted"])
            self.assertEqual(scout.routing_candidates(), [])

    def test_real_benchmark_requires_installed_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            manager, _ = self.make_manager(td)
            manager.ollama_status = lambda: self.healthy_ollama([])
            with self.assertRaises(RuntimeError):
                manager.benchmark("spark-x2.5-4b")

    def test_benchmark_uses_governor_and_persists_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            governor = CountingGovernor()
            manager, _ = self.make_manager(td, governor=governor)
            report = manager.benchmark(
                "spark-x2.5-4b",
                runner=fake_runner,
                device="unit-test",
                quantization="test-q",
            )
            self.assertEqual(governor.entries, 1)
            self.assertEqual(report["tool_json"]["score"], 1.0)
            self.assertEqual(report["long_context"]["pass_rate"], 1.0)
            self.assertTrue(report["benchmark_id"].startswith("spark-"))
            self.assertFalse(report["promotion_ready"])
            self.assertTrue((manager.benchmarks / "spark-x2.5-4b.json").exists())
            state = manager._load_lifecycle()["models"]["spark-x2.5-4b"]
            self.assertEqual(state["stage"], "BENCHMARKED")
            self.assertFalse(state["routing_enabled"])

    def test_review_verify_and_enable_routing_are_separate_gates(self):
        with tempfile.TemporaryDirectory() as td:
            manager, scout = self.make_manager(td, governor=CountingGovernor())
            key = "spark-x2.5-4b"
            manager.benchmark(key, runner=fake_runner)
            reviewed = manager.review(
                key,
                coding_score=1.0,
                agent_score=1.0,
                multilingual_score=1.0,
                review_ref="review-001",
                verification_ref="verify-001",
            )
            self.assertEqual(reviewed["lifecycle"]["stage"], "REVIEWED")
            self.assertFalse(reviewed["lifecycle"]["verified"])
            self.assertFalse(reviewed["lifecycle"]["routing_enabled"])

            with self.assertRaises(RuntimeError):
                manager.enable_routing(
                    key,
                    review_ref="review-001",
                    verification_ref="verify-001",
                )

            verified = manager.verify(
                key,
                review_ref="review-001",
                verification_ref="verify-001",
            )
            self.assertEqual(verified["lifecycle"]["stage"], "VERIFIED")
            self.assertFalse(verified["lifecycle"]["routing_enabled"])

            enabled = manager.enable_routing(
                key,
                review_ref="review-001",
                verification_ref="verify-001",
            )
            self.assertEqual(enabled["lifecycle"]["stage"], "ROUTING_ENABLED")
            self.assertTrue(enabled["lifecycle"]["routing_enabled"])
            candidates = scout.routing_candidates(limit=10)
            self.assertEqual([x["model_id"] for x in candidates], [manager.SPECS[key].model_id])

    def test_install_plan_never_downloads(self):
        with tempfile.TemporaryDirectory() as td:
            manager, _ = self.make_manager(td)
            manager.ollama_status = lambda: self.healthy_ollama([])
            plan = manager.install_plan("spark-x2.5-4b")
            self.assertFalse(plan["automatic_download"])
            self.assertTrue(plan["approval_required"])
            self.assertTrue(plan["storage_policy"]["do_not_use_c_drive"])
            self.assertEqual(plan["preconditions"]["ollama_minimum"], "0.34.1")


class SparkIntegrationContractTests(unittest.TestCase):
    def test_orchestrator_uses_existing_model_scout_and_action_bus(self):
        core = Path(__file__).resolve().parents[1] / "krishna_core"
        source = (core / "orchestrator.py").read_text(encoding="utf-8")
        self.assertIn("SparkX25Manager(", source)
        self.assertIn("self.agi.model_scout", source)
        self.assertIn("self.router.bind_model_scout(self.agi.model_scout)", source)
        init_start = source.index("self.spark_x25 = SparkX25Manager(")
        init_end = source.index("self.sudarshan_projects =", init_start)
        self.assertNotIn("self.spark_x25.discover()", source[init_start:init_end])
        for action in (
            "model.spark.status",
            "model.spark.discover",
            "model.spark.install_plan",
            "model.spark.benchmark",
            "model.spark.review",
            "model.spark.verify",
            "model.spark.enable_routing",
            "model.spark.mobile_plan",
        ):
            self.assertIn(f'"{action}"', source)
        self.assertIn('"model.spark.enable_routing",model_spark_enable_routing_action', source)
        self.assertIn("requires_approval=True", source)

    def test_server_exposes_read_only_spark_endpoints_only(self):
        core = Path(__file__).resolve().parents[1] / "krishna_core"
        source = (core / "server.py").read_text(encoding="utf-8")
        self.assertIn('"/api/models/spark-x25/status"', source)
        self.assertIn('"/api/models/spark-x25/install-plan"', source)
        self.assertNotIn('post_path == "/api/models/spark-x25/enable-routing"', source)
        self.assertNotIn('post_path == "/api/models/spark-x25/install"', source)

    def test_router_consumes_only_routing_enabled_candidates(self):
        core = Path(__file__).resolve().parents[1] / "krishna_core"
        source = (core / "router.py").read_text(encoding="utf-8")
        scout = (core / "model_scout.py").read_text(encoding="utf-8")
        self.assertIn("self.model_scout.routing_candidates(", source)
        self.assertIn('if not row.get("routing_enabled"):continue', scout)
        self.assertIn("ollama-model:", source)


if __name__ == "__main__":
    unittest.main()
