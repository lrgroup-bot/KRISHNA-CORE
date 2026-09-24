import json
import re
import tempfile
import unittest
from pathlib import Path

from krishna_core.automation_bus import AutomationBus
from krishna_core.kabach import KabachAgent
from krishna_core.development_operator import DevelopmentOperator
from krishna_core.model_scout import ModelCandidate, ModelScout
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.remote_access import PrivateRemotePolicy
from krishna_core.shared_action_bus import SharedActionBus
from krishna_core.spark_x25 import SparkX25Manager


class FullAuditHardeningTests(unittest.TestCase):
    def _bus(self, resolver=None):
        return SharedActionBus(
            AutomationBus(),
            PolicyKernel(Path(tempfile.gettempdir()) / "krishna-full-audit-policy"),
            permission_resolver=resolver,
        )

    def test_idempotency_replay_reauthorizes_and_rejects_context_or_payload_collision(self):
        calls = []
        def resolver(spec, context):
            if context.get("source") == "pc":
                return True, "local owner"
            needed = set(spec.permissions)
            granted = set(context.get("permissions") or [])
            return needed.issubset(granted), "missing permission"

        bus = self._bus(resolver)
        bus.register(
            "audit.write",
            lambda payload, ctx: calls.append(dict(payload)) or {"ok": True, "value": payload.get("value")},
            permissions=("audit.write",),
            sources=("pc", "agent"),
        )
        first = bus.dispatch(
            "audit.write", {"value": 1}, source="pc", actor="owner", idempotency_key="same-key"
        )
        replay = bus.dispatch(
            "audit.write", {"value": 1}, source="pc", actor="owner", idempotency_key="same-key"
        )
        self.assertEqual(first["action_id"], replay["action_id"])
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(len(calls), 1)

        with self.assertRaises(PermissionError):
            bus.dispatch(
                "audit.write", {"value": 1}, source="agent", actor="worker",
                permissions=(), idempotency_key="same-key",
            )
        with self.assertRaises(ValueError):
            bus.dispatch(
                "audit.write", {"value": 2}, source="pc", actor="owner", idempotency_key="same-key"
            )
        self.assertEqual(len(calls), 1)

    def test_sensitive_action_fields_are_redacted_without_hiding_safe_token_metrics(self):
        bus = self._bus()
        bus.register("audit.echo", lambda payload, ctx: {"ok": True})
        out = bus.dispatch(
            "audit.echo",
            {
                "access_token": "aaa",
                "client-secret": "bbb",
                "authorization_header": "Bearer ccc",
                "nested": {"refreshToken": "ddd", "token_count": 123},
            },
        )
        payload = out["payload"]
        self.assertEqual(payload["access_token"], "[REDACTED]")
        self.assertEqual(payload["client-secret"], "[REDACTED]")
        self.assertEqual(payload["authorization_header"], "[REDACTED]")
        self.assertEqual(payload["nested"]["refreshToken"], "[REDACTED]")
        self.assertEqual(payload["nested"]["token_count"], 123)

    def test_kabach_high_risk_tool_requires_approval_but_can_run_when_approved(self):
        kabach = object.__new__(KabachAgent)
        denied = kabach.inspect_tool(
            "filesystem", "delete_file", permissions=("filesystem",), approved=False
        )
        self.assertFalse(denied["allowed"])
        self.assertIn("explicit_approval_required", denied["evidence"])

        allowed = kabach.inspect_tool(
            "filesystem", "delete_file", permissions=("filesystem",), approved=True
        )
        self.assertTrue(allowed["allowed"])
        self.assertEqual(allowed["risk"], "high")
        self.assertIn("high_risk_operation", allowed["evidence"])

    def test_mobile_client_api_paths_are_remote_allowlisted_or_explicitly_public(self):
        repo_root = Path(__file__).resolve().parents[2]
        mobile = (repo_root / "mobile_v3" / "MainActivity.java").read_text(encoding="utf-8")
        paths = set(re.findall(r'["\'](/api/[A-Za-z0-9_./-]+)', mobile))
        public = {"/api/mobile/pair/request"}
        policy = PrivateRemotePolicy()
        missing = sorted(path for path in paths if path not in public and not policy.mobile_route_allowed(path))
        self.assertEqual(missing, [], "mobile API path missing from paired-device allowlist: " + ", ".join(missing))

    def test_development_candidates_use_configured_promotion_staging_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "project"
            staging = root / "runtime" / ".krishna_state" / "promotion-candidates"
            source.mkdir(parents=True)
            (source / "app.py").write_text("print('old')\n", encoding="utf-8")
            dev = DevelopmentOperator(None, staging_root=staging)
            staged = dev.stage(source, [{"path": "app.py", "content": "print('new')\n"}])
            candidate = Path(staged["candidate_root"]).resolve()
            candidate.relative_to(staging.resolve())
            self.assertEqual((candidate / "app.py").read_text(encoding="utf-8"), "print('new')\n")

    def test_server_generic_exception_handlers_do_not_echo_exception_messages(self):
        repo_root = Path(__file__).resolve().parents[2]
        server = (repo_root / "core" / "krishna_core" / "server.py").read_text(encoding="utf-8")
        leaking = re.findall(
            r'except Exception as exc:\s*\n(?:\s+.*\n){0,4}?\s*return self\._json\(500, \{"error": ?str\(exc\)\}\)',
            server,
        )
        self.assertEqual(leaking, [], "generic HTTP 500 handlers must not echo internal exception messages")

    def test_model_scout_incompatible_version_fails_closed_and_preserves_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "model-scout.json"
            original = json.dumps({"schema": 1, "version": "old-version", "models": {"keep": {"routing_enabled": True}}})
            path.write_text(original, encoding="utf-8")
            scout = ModelScout(path)
            self.assertTrue(scout.load_error)
            with self.assertRaises(RuntimeError):
                scout.evaluate(ModelCandidate("local/new", quality=1.0, benchmark_ref="bench"))
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_spark_incompatible_lifecycle_schema_or_version_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scout = ModelScout(root / "model-scout.json")
            manager = SparkX25Manager(root / "spark", scout)
            incompatible = {
                "schema": 2,
                "version": "spark-x25-old",
                "models": {"spark-x2.5-4b": {"stage": "ROUTING_ENABLED", "routing_enabled": True}},
            }
            before = json.dumps(incompatible, indent=2)
            manager.lifecycle_path.write_text(before, encoding="utf-8")
            with self.assertRaises(RuntimeError):
                manager.status()
            self.assertEqual(manager.lifecycle_path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
