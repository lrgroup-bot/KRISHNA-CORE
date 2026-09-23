import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.ai_role_policy import AIRolePolicyStore
from krishna_core.router import ModelRouter


class AIRolePolicyStoreTests(unittest.TestCase):
    def test_rishi_and_lab_roles_exist_and_default_to_auto(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            roles={x["role"]:x for x in store.list()}
            for role in (
                "rishi_research","rishi_counter_evidence","rishi_debate",
                "gautama_review","bharadvaja_test_plan","lab_hypothesis",
                "lab_result_analysis","vyasa_synthesis",
            ):
                self.assertIn(role,roles)
                self.assertEqual(roles[role]["mode"],"auto")
            self.assertEqual(roles["rishi_research"]["auto_strategy"],"local_first")
            self.assertEqual(roles["gautama_review"]["auto_strategy"],"verified_cloud_first")

    def test_assignment_persists_and_auto_resets(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"roles.json"
            store=AIRolePolicyStore(path)
            store.set("lab_hypothesis","prefer","ollama","qwen2.5:3b")
            again=AIRolePolicyStore(path)
            self.assertEqual(again.get("lab_hypothesis")["provider"],"ollama")
            self.assertEqual(again.get("lab_hypothesis")["model"],"qwen2.5:3b")
            again.set("lab_hypothesis","auto")
            self.assertIsNone(AIRolePolicyStore(path).get("lab_hypothesis")["provider"])

    def test_nonlocal_model_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            with self.assertRaises(ValueError):
                store.set("gautama_review","pin","openrouter-free","fixed-cloud-model")


class RoleAwareRouterTests(unittest.TestCase):
    def _router(self,store):
        router=ModelRouter()
        router.bind_role_policy(store)
        router.available=lambda:[
            {"provider":"ollama","available":True,"local":True,"model":"local","free_only":True},
            {"provider":"gpt4all","available":False,"local":True,"model":"auto","free_only":True},
            {"provider":"openrouter-free","available":True,"local":False,"model":"dynamic","free_only":True,
             "automatic_zero_cost_eligible":True},
            {"provider":"direct-free:cloudflare-workers-ai","available":True,"local":False,"model":"verified","free_only":True,
             "automatic_zero_cost_eligible":True},
            {"provider":"gateway:owner-labelled-free","available":True,"local":False,"model":"declared","free_only":True,
             "automatic_zero_cost_eligible":False},
        ]
        return router

    def test_research_is_local_first_but_gautama_is_verified_cloud_first(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            router=self._router(store)
            research=router.role_plan("rishi_research","approved_cloud",True)
            review=router.role_plan("gautama_review","approved_cloud",True)
            self.assertEqual(research[0]["provider"],"ollama")
            self.assertEqual(review[0]["provider"],"openrouter-free:reasoning")
            self.assertNotIn("gateway:owner-labelled-free",{x["provider"] for x in review})

    def test_local_only_forces_every_rishi_role_local(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            router=self._router(store)
            for role in ("rishi_research","gautama_review","vyasa_synthesis","lab_result_analysis"):
                plan=router.role_plan(role,"local_only",True)
                self.assertTrue(plan)
                self.assertTrue(all(x["local"] for x in plan))

    def test_pinned_declared_free_gateway_is_blocked_while_paid_cloud_off(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            store.set("vyasa_synthesis","pin","gateway:owner-labelled-free")
            router=self._router(store)
            with patch.dict(os.environ,{"KRISHNA_ALLOW_PAID_CLOUD":"0"},clear=False):
                with self.assertRaisesRegex(RuntimeError,"pinned"):
                    router.route("synthesize",role="vyasa_synthesis",privacy="approved_cloud")

    def test_independent_review_pair_uses_local_and_verified_free_cloud(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            router=self._router(store)
            calls=[]
            def governed(provider,prompt,privacy="approved_cloud",free_only=False,
                         project="KRISHNA",actor="model-router",model=None):
                calls.append((provider,privacy,actor))
                if provider=="ollama":return '{"observations":["local"],"interpretation":"local"}'
                if provider=="openrouter-free:reasoning":
                    return '{"observations":["cloud"],"interpretation":"cloud"}'
                raise RuntimeError(provider)
            router._governed_ask=governed
            pair=router.independent_review_pair(
                "review evidence",privacy="approved_cloud",role="lab_result_analysis",
            )
            self.assertTrue(pair["independent_pair"])
            self.assertEqual(pair["local_review"]["provider"],"ollama")
            self.assertEqual(pair["independent_cloud_review"]["provider"],"openrouter-free:reasoning")

    def test_independent_review_pair_never_sends_local_only_data_to_cloud(self):
        with tempfile.TemporaryDirectory() as td:
            store=AIRolePolicyStore(Path(td)/"roles.json")
            router=self._router(store)
            calls=[]
            def governed(provider,*args,**kwargs):
                calls.append(provider)
                if provider=="ollama":return "local"
                raise AssertionError("cloud must not run")
            router._governed_ask=governed
            pair=router.independent_review_pair(
                "private evidence",privacy="local_only",role="lab_result_analysis",
            )
            self.assertFalse(pair["independent_pair"])
            self.assertIsNone(pair["independent_cloud_review"])
            self.assertEqual(calls,["ollama"])


if __name__=="__main__":
    unittest.main()
