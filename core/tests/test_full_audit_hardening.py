import json
import re
import tempfile
import unittest
from pathlib import Path

from krishna_core.automation_bus import AutomationBus
from krishna_core.bhumiputra import BhumiputraAgent
from krishna_core.field_perception import FieldPerceptionPolicy
from krishna_core.kabach import KabachAgent
from krishna_core.development_operator import DevelopmentOperator
from krishna_core.durable_queue import DurableQueue
from krishna_core.model_scout import ModelCandidate, ModelScout
from krishna_core.model_gateway import ModelGatewayRegistry
from krishna_core.mission_budget import MissionBudgetManager
from krishna_core.mission_engine import MissionEngine
from krishna_core.narad import NaradRuntime
from krishna_core.narad.credentials import NaradCredentialVault
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.remote_access import PrivateRemotePolicy
from krishna_core.router import ModelRouter
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

    def test_idempotency_receipt_survives_restart_and_failed_execution_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "core.db"
            calls = []
            bus1 = SharedActionBus(AutomationBus(), PolicyKernel(root / "policy1"), idempotency_db_path=db)
            bus1.register("audit.once", lambda payload, ctx: calls.append("first") or {"ok": True})
            first = bus1.dispatch("audit.once", {"x": 1}, idempotency_key="persist-key")
            bus1.close()

            bus2 = SharedActionBus(AutomationBus(), PolicyKernel(root / "policy2"), idempotency_db_path=db)
            bus2.register("audit.once", lambda payload, ctx: calls.append("second") or {"ok": True})
            replay = bus2.dispatch("audit.once", {"x": 1}, idempotency_key="persist-key")
            self.assertTrue(replay["idempotent_replay"])
            self.assertEqual(replay["action_id"], first["action_id"])
            self.assertEqual(calls, ["first"])

            bus2.register("audit.fail", lambda payload, ctx: (_ for _ in ()).throw(RuntimeError("boom")))
            with self.assertRaises(RuntimeError):
                bus2.dispatch("audit.fail", {"x": 2}, idempotency_key="failed-key")
            bus2.close()

            retry_calls = []
            bus3 = SharedActionBus(AutomationBus(), PolicyKernel(root / "policy3"), idempotency_db_path=db)
            bus3.register("audit.fail", lambda payload, ctx: retry_calls.append("rerun") or {"ok": True})
            with self.assertRaises(RuntimeError):
                bus3.dispatch("audit.fail", {"x": 2}, idempotency_key="failed-key")
            self.assertEqual(retry_calls, [])
            bus3.close()

    def test_failed_action_receipts_do_not_persist_exception_message_secrets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bus = SharedActionBus(
                AutomationBus(), PolicyKernel(root / "policy"),
                idempotency_db_path=root / "core.db",
            )
            bus.register(
                "audit.secret-fail",
                lambda payload, ctx: (_ for _ in ()).throw(RuntimeError("provider leaked api_key=TOPSECRET123")),
            )
            with self.assertRaises(RuntimeError):
                bus.dispatch("audit.secret-fail", {"x": 1}, idempotency_key="secret-fail")
            receipt = bus.recent(1)[0]
            self.assertEqual(receipt["error"], "RuntimeError")
            self.assertNotIn("TOPSECRET123", json.dumps(receipt))
            durable = bus._idempotency_store.get("secret-fail")
            self.assertNotIn("TOPSECRET123", json.dumps(durable))
            bus.close()

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
                "promotion_token": "candidate-transaction-id",
            },
        )
        payload = out["payload"]
        self.assertEqual(payload["access_token"], "[REDACTED]")
        self.assertEqual(payload["client-secret"], "[REDACTED]")
        self.assertEqual(payload["authorization_header"], "[REDACTED]")
        self.assertEqual(payload["nested"]["refreshToken"], "[REDACTED]")
        self.assertEqual(payload["nested"]["token_count"], 123)
        self.assertEqual(payload["promotion_token"], "candidate-transaction-id")

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
        self.assertFalse(policy.mobile_route_allowed("/api/mobile/control"), "conversation-only mobile must not expose legacy remote-control API")

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

    def test_hawkeye_metadata_secret_redaction_is_recursive_and_persisted(self):
        cleaned = FieldPerceptionPolicy.redact_sensitive_value({
            "password": "dont-store-me",
            "nested": {"refreshToken": "token-value", "note": "api_key=abcd1234"},
            "items": [{"authorization": "Bearer xyz"}, "otp=998877"],
        })
        raw = json.dumps(cleaned)
        self.assertNotIn("dont-store-me", raw)
        self.assertNotIn("token-value", raw)
        self.assertNotIn("abcd1234", raw)
        self.assertNotIn("998877", raw)

        with tempfile.TemporaryDirectory() as td:
            agent = BhumiputraAgent(Path(td))
            receipt = agent.store_mobile_evidence("session-1", b"fake-image", "image/jpeg", {
                "password": "mobile-secret", "heading": 123,
                "nested": {"access_token": "private-token"},
            })
            meta_path = agent.evidence_dir / (receipt["evidence_id"] + ".json")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            encoded = json.dumps(meta)
            self.assertNotIn("mobile-secret", encoded)
            self.assertNotIn("private-token", encoded)
            self.assertEqual(meta["sensor_context"]["password"], "[SECRET REDACTED]")
            self.assertEqual(meta["sensor_context"]["heading"], 123)

    def test_model_gateway_persisted_state_and_runtime_url_validation_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "gateways.json"
            bad = {
                "schema": 1,
                "profiles": [{
                    "id": "bad", "name": "bad", "base_url": "http://169.254.169.254",
                    "model": "x", "secret_id": "secret", "free_only": True,
                    "enabled": True, "created_at": 1.0,
                }],
            }
            original = json.dumps(bad)
            path.write_text(original, encoding="utf-8")
            gateway = ModelGatewayRegistry(path)
            self.assertTrue(gateway.load_error)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

            wrong_schema = json.dumps({"schema": 99, "profiles": []})
            path.write_text(wrong_schema, encoding="utf-8")
            gateway = ModelGatewayRegistry(path)
            self.assertTrue(gateway.load_error)
            self.assertEqual(path.read_text(encoding="utf-8"), wrong_schema)

    def test_direct_free_automatic_fallback_uses_governed_model_action(self):
        class Direct:
            def configured(self): return True
            def complete(self, *args, **kwargs):
                raise AssertionError("automatic fallback must not bypass governed model action")

        class Control:
            def __init__(self): self.calls = []
            def action(self, action, payload, **kwargs):
                self.calls.append((action, dict(payload), dict(kwargs)))
                provider = payload.get("provider")
                if provider in {"ollama", "gpt4all"}:
                    raise RuntimeError("local unavailable")
                if provider == "direct-free:cloudflare-workers-ai":
                    return {"result": {
                        "provider": provider, "text": "governed-ok",
                        "zero_cost_proof": {"verified": True},
                    }}
                raise AssertionError(provider)

        router = ModelRouter()
        router.bind_direct_free(Direct())
        control = Control()
        router.bind_sudarshan(control)
        out = router.route("safe public prompt", privacy="approved_cloud", free_only=True)
        self.assertEqual(out["text"], "governed-ok")
        self.assertTrue(out["zero_cost_verified"])
        direct_calls = [x for x in control.calls if x[1].get("provider") == "direct-free:cloudflare-workers-ai"]
        self.assertEqual(len(direct_calls), 1)
        self.assertEqual(direct_calls[0][0], "model.complete")

    def test_durable_queue_and_mission_corruption_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "core.db"
            queue = DurableQueue(db)
            row = queue.enqueue("mission.create", {"goal": "safe"}, permissions=("mission.write",))
            with queue.lock:
                queue.db.execute("UPDATE durable_queue SET payload=? WHERE queue_id=?", ("{bad-json", row["queue_id"]))
                queue.db.commit()
            with self.assertRaises(RuntimeError):
                queue.get(row["queue_id"])
            queue.close()

            missions = MissionEngine(db)
            mission = missions.create("safe", resource_budget={"max_tool_calls": 2})
            with missions.lock:
                missions.db.execute("UPDATE missions SET resource_budget=? WHERE mission_id=?", ("[]", mission["mission_id"]))
                missions.db.commit()
            with self.assertRaises(RuntimeError):
                missions.get(mission["mission_id"])
            missions.close()

    def test_narad_credential_metadata_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "credentials.json"
            original = json.dumps({"schema": 99, "credentials": []})
            path.write_text(original, encoding="utf-8")
            vault = NaradCredentialVault(path)
            self.assertTrue(vault.load_error)
            with self.assertRaises(RuntimeError):
                vault.register("x", "provider", "KRISHNA_TEST_SECRET")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_narad_state_schema_and_high_assurance_promotion_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state = root / "narad.json"
            original = json.dumps({"schema": 99, "workflows": [], "history": []})
            state.write_text(original, encoding="utf-8")
            broken = NaradRuntime(PolicyKernel(root / "policy-bad"), AutomationBus(), state_path=state)
            self.assertTrue(broken.load_error)
            with self.assertRaises(RuntimeError):
                broken.create_workflow("x", {"type": "manual"}, [{"action": "mission.create"}])
            self.assertEqual(state.read_text(encoding="utf-8"), original)

            state.unlink()
            narad = NaradRuntime(PolicyKernel(root / "policy-good"), AutomationBus(), state_path=state)
            workflow = narad.create_workflow("x", {"type": "manual"}, [{"action": "mission.create"}])
            wid = workflow["id"]
            narad.promote(wid, "candidate")
            narad.promote(wid, "sandbox")
            with self.assertRaises(PermissionError):
                narad.promote(wid, "verified", verified=True, approved=False)
            promoted = narad.promote(wid, "verified", verified=True, approved=True)
            self.assertEqual(promoted["state"], "verified")

    def test_mission_budget_corrupt_state_and_negative_consumption_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "core.db"
            budgets = MissionBudgetManager(db)
            budgets.configure("m1", {"max_tool_calls": 10})
            with budgets.lock:
                budgets.db.execute("UPDATE mission_budgets SET usage_json=? WHERE mission_id=?", ("{bad-json", "m1"))
                budgets.db.commit()
            with self.assertRaises(RuntimeError):
                budgets.status("m1")
            with budgets.lock:
                budgets.db.execute("UPDATE mission_budgets SET usage_json=? WHERE mission_id=?", (json.dumps({"tool_calls": 1}), "m1"))
                budgets.db.commit()
            with self.assertRaises(ValueError):
                budgets.consume("m1", "tool_calls", -1)
            self.assertEqual(budgets.status("m1")["usage"]["tool_calls"], 1)
            budgets.close()

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
