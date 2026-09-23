import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.ai_role_policy import AIRolePolicyStore
from krishna_core.router import ModelRouter


class AIRolePolicyStoreTests(unittest.TestCase):
    def test_defaults_are_auto_and_persist_owner_assignment(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"roles.json"
            store=AIRolePolicyStore(path)
            self.assertEqual(store.get("coding")["mode"],"auto")
            row=store.set("coding","prefer","ollama","qwen2.5:3b")
            self.assertEqual(row["provider"],"ollama")
            self.assertEqual(row["model"],"qwen2.5:3b")
            again=AIRolePolicyStore(path)
            self.assertEqual(again.get("coding")["provider"],"ollama")
            self.assertEqual(again.get("coding")["model"],"qwen2.5:3b")

    def test_auto_clears_assignment(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            store.set("vision","pin","openrouter-free")
            row=store.set("vision","auto")
            self.assertEqual(row["mode"],"auto")
            self.assertIsNone(row["provider"])

    def test_prefer_and_pin_require_provider(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            with self.assertRaises(ValueError):
                store.set("coding","pin")
            with self.assertRaises(ValueError):
                store.set("coding","prefer")

    def test_nonlocal_model_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            with self.assertRaises(ValueError):
                store.set("reasoning","pin","openrouter-free","some-model")


class AIRoleRoutingTests(unittest.TestCase):
    def _router(self,store):
        router=ModelRouter()
        router.bind_role_policy(store)
        router.available=lambda:[
            {"provider":"ollama","available":True,"local":True,"model":"default-local","free_only":True},
            {"provider":"gpt4all","available":False,"local":True,"model":"auto","free_only":True},
            {"provider":"openrouter-free","available":True,"local":False,"model":"dynamic","free_only":True},
            {"provider":"direct-free:cloudflare-workers-ai","available":True,"local":False,"model":"verified","free_only":True},
            {"provider":"gateway:declared-free","available":True,"local":False,"model":"declared","free_only":True},
        ]
        return router

    def test_pin_local_model_uses_selected_model_and_no_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            store.set("coding","pin","ollama","qwen2.5-coder:7b")
            router=self._router(store)
            calls=[]
            def governed(provider,prompt,privacy="approved_cloud",free_only=False,
                         project="KRISHNA",actor="model-router",model=None):
                calls.append((provider,model,privacy))
                return "coded"
            router._governed_ask=governed
            out=router.route("implement",role="coding",privacy="local_only")
            self.assertEqual(out["provider"],"ollama")
            self.assertEqual(out["model"],"qwen2.5-coder:7b")
            self.assertEqual(out["role_mode"],"pin")
            self.assertEqual(calls,[("ollama","qwen2.5-coder:7b","local_only")])

    def test_auto_reasoning_uses_role_specific_openrouter_after_local_failure(self):
        class OpenRouter:
            def configured(self):return True
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            router=self._router(store)
            router.bind_openrouter_free(OpenRouter())
            calls=[]
            def governed(provider,prompt,privacy="approved_cloud",free_only=False,
                         project="KRISHNA",actor="model-router",model=None):
                calls.append(provider)
                if provider in {"ollama","gpt4all"}:raise RuntimeError("local unavailable")
                if provider=="openrouter-free:reasoning":return "reasoned"
                raise AssertionError(provider)
            router._governed_ask=governed
            out=router.route("hard problem",role="reasoning",privacy="approved_cloud")
            self.assertEqual(out["provider"],"openrouter-free:reasoning")
            self.assertEqual(out["text"],"reasoned")
            self.assertIn("openrouter-free:reasoning",calls)

    def test_pin_cloud_is_blocked_by_local_only_privacy(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            store.set("research","pin","openrouter-free")
            router=self._router(store)
            with self.assertRaisesRegex(RuntimeError,"pinned"):
                router.route("private material",role="research",privacy="local_only")

    def test_declared_free_gateway_cannot_be_automatic_role_when_paid_cloud_off(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            store.set("research","pin","gateway:declared-free")
            router=self._router(store)
            with patch.dict(os.environ,{"KRISHNA_ALLOW_PAID_CLOUD":"0"},clear=False):
                with self.assertRaisesRegex(RuntimeError,"pinned"):
                    router.route("public research",role="research",privacy="approved_cloud")

    def test_coding_plan_uses_different_role_assignments(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            store.set("implementation","pin","ollama","coder-local")
            store.set("architecture_review","prefer","openrouter-free")
            router=self._router(store)
            plan={x["role"]:x for x in router.coding_plan("approved_cloud",free_only=True)}
            self.assertEqual(plan["implementation"]["provider"],"ollama")
            self.assertEqual(plan["implementation"]["model"],"coder-local")
            self.assertEqual(plan["architecture_review"]["provider"],"openrouter-free")
            self.assertEqual(plan["architecture_review"]["route_provider"],"openrouter-free:reasoning")


if __name__=="__main__":
    unittest.main()
