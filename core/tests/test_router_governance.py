import os
import unittest
from unittest.mock import patch

from krishna_core.router import ModelRouter


class FakeControlPlane:
    def __init__(self):
        self.calls=[]
    def action(self,action,payload,**kwargs):
        self.calls.append((action,dict(payload),dict(kwargs)))
        return {
            "action_id":"a1","status":"completed","verified":True,
            "result":{"provider":payload["provider"],"model":"fake","text":"governed"},
        }


class GovernedRouterTests(unittest.TestCase):
    def test_route_uses_sudarshan_when_bound(self):
        router=ModelRouter()
        gate=FakeControlPlane()
        router.bind_sudarshan(gate)
        out=router.route("hello",privacy="local_only",project="KUBER",actor="conversation")
        self.assertEqual(out,{"provider":"ollama","text":"governed"})
        self.assertEqual(len(gate.calls),1)
        action,payload,kwargs=gate.calls[0]
        self.assertEqual(action,"model.complete")
        self.assertEqual(payload["privacy"],"local_only")
        self.assertEqual(kwargs["project"],"KUBER")
        self.assertEqual(kwargs["actor"],"conversation")
        self.assertEqual(kwargs["source"],"system")

    def test_route_does_not_call_direct_ask_when_sudarshan_bound(self):
        router=ModelRouter()
        gate=FakeControlPlane()
        router.bind_sudarshan(gate)
        router.ask=lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("direct ask bypass"))
        out=router.route("hello",privacy="local_only",project="KRISHNA")
        self.assertEqual(out["text"],"governed")


class FreeCloudDefaultTests(unittest.TestCase):
    def test_coding_plan_excludes_paid_cloud_by_default(self):
        router=ModelRouter()
        router.available=lambda:[
            {"provider":"ollama","available":True,"local":True,"model":"local","free_only":True},
            {"provider":"openrouter-free","available":True,"local":False,"model":"dynamic","free_only":True},
            {"provider":"direct-free:cloudflare-workers-ai","available":True,"local":False,"model":"verified","free_only":True},
            {"provider":"gateway:declared-free","available":True,"local":False,"model":"declared","free_only":True},
            {"provider":"openai","available":True,"local":False,"model":"paid","free_only":False},
        ]
        # Keep this unit test independent of any real Ollama service/models present
        # on the machine running the suite. coding_plan() is intentionally allowed
        # to inspect live local role status in production, so the test must stub it.
        router.local_model_status=lambda task="general":{
            "task":task,
            "available":False,
            "selected_model":None,
        }
        with patch.dict(os.environ,{"KRISHNA_ALLOW_PAID_CLOUD":"0"},clear=False):
            plan=router.coding_plan("approved_cloud")
        providers={x["provider"] for x in plan}
        self.assertIn("ollama",providers)
        self.assertIn("openrouter-free",providers)
        self.assertIn("direct-free:cloudflare-workers-ai",providers)
        self.assertNotIn("gateway:declared-free",providers)
        self.assertNotIn("openai",providers)

    def test_route_does_not_reach_paid_gateway_without_explicit_opt_in(self):
        class Gateway:
            def eligible(self,privacy="approved_cloud",free_only=False):
                if free_only:return []
                return [type("P",(),{"id":"paid1","free_only":False})()]
        router=ModelRouter(Gateway())
        called=[]
        def governed(provider,*args,**kwargs):
            called.append(provider)
            raise RuntimeError("unavailable")
        router._governed_ask=governed
        with patch.dict(os.environ,{"KRISHNA_ALLOW_PAID_CLOUD":"0"},clear=False):
            with self.assertRaisesRegex(RuntimeError,"auto-fallback is disabled"):
                router.route("hello",privacy="approved_cloud")
        self.assertEqual(called,["ollama","gpt4all"])



    def test_route_uses_verified_direct_free_after_openrouter_failure(self):
        class OpenRouter:
            def configured(self):return True
            def status(self,refresh=False):return {"configured":True}

        class DirectFree:
            def __init__(self):self.calls=[]
            def configured(self):return True
            def status(self,refresh=False):
                return {"configured":True,"provider_id":"direct-free:cloudflare-workers-ai"}
            def complete(self,prompt,privacy="approved_cloud"):
                self.calls.append((prompt,privacy))
                return {
                    "provider_id":"direct-free:cloudflare-workers-ai",
                    "text":"verified-direct",
                    "zero_cost_proof":{"billing_guard":"live"},
                }

        router=ModelRouter()
        router.bind_openrouter_free(OpenRouter())
        direct=DirectFree()
        router.bind_direct_free(direct)

        def governed(provider,*args,**kwargs):
            if provider in {"ollama","gpt4all"}:raise RuntimeError("local unavailable")
            if provider.startswith("openrouter-free"):raise RuntimeError("free catalog unavailable")
            raise AssertionError(provider)

        router._governed_ask=governed
        with patch.dict(os.environ,{"KRISHNA_ALLOW_PAID_CLOUD":"0"},clear=False):
            out=router.route("public task",privacy="approved_cloud")
        self.assertEqual(out["provider"],"direct-free:cloudflare-workers-ai")
        self.assertEqual(out["text"],"verified-direct")
        self.assertTrue(out["zero_cost_verified"])
        self.assertEqual(direct.calls,[("public task","approved_cloud")])


    def test_strict_zero_credit_blocks_generic_gateway_even_when_marked_free(self):
        class Gateway:
            def complete(self,*args,**kwargs):
                raise AssertionError("generic gateway should not execute")
        router=ModelRouter(Gateway())
        with patch.dict(os.environ,{"KRISHNA_STRICT_ZERO_CREDIT":"1"},clear=False):
            with self.assertRaisesRegex(PermissionError,"strict zero-credit policy"):
                router.ask("gateway:declared-free","hello")

    def test_strict_zero_credit_cannot_be_bypassed_by_paid_cloud_flag(self):
        with patch.dict(os.environ,{
            "KRISHNA_STRICT_ZERO_CREDIT":"1",
            "KRISHNA_ALLOW_PAID_CLOUD":"1",
        },clear=False):
            self.assertFalse(ModelRouter.paid_cloud_enabled())

    def test_paid_cloud_requires_explicit_environment_opt_in(self):
        router=ModelRouter()
        with patch.dict(os.environ,{"KRISHNA_ALLOW_PAID_CLOUD":"0"},clear=False):
            self.assertFalse(router.paid_cloud_enabled())
        with patch.dict(os.environ,{"KRISHNA_ALLOW_PAID_CLOUD":"1"},clear=False):
            self.assertTrue(router.paid_cloud_enabled())



class QwenPcRolePolicyTests(unittest.TestCase):
    def test_qwen_is_owner_approved_pc_general_default(self):
        with patch.dict(os.environ,{},clear=True):
            candidates=ModelRouter.local_model_candidates()
        self.assertTrue(candidates)
        self.assertEqual(candidates[0],"qwen3.5:4b")
        self.assertIn("gemma3:4b",candidates)

    def test_explicit_pc_qwen_environment_is_honored(self):
        with patch.dict(os.environ,{
            "KRISHNA_LOCAL_MODEL":"qwen3.5:4b",
            "KRISHNA_LOCAL_FALLBACK_MODELS":"qwen2.5:3b,qwen2.5vl:7b,gemma3:4b",
        },clear=True):
            candidates=ModelRouter.local_model_candidates()
        self.assertEqual(candidates[0],"qwen3.5:4b")
        self.assertIn("qwen2.5:3b",candidates)
        self.assertIn("qwen2.5vl:7b",candidates)

    def test_explicit_qwen_request_reaches_pc_ollama(self):
        router=ModelRouter()
        calls=[]
        router._ollama_generate=lambda model,prompt: calls.append((model,prompt)) or "ok"
        self.assertEqual(router.local("hello","qwen3.5:4b"),"ok")
        self.assertEqual(calls,[("qwen3.5:4b","hello")])

    def test_qwen_family_is_allowed_on_pc(self):
        self.assertTrue(ModelRouter.local_model_allowed("qwen3.5:4b"))
        self.assertTrue(ModelRouter.local_model_allowed("library/qwen2.5vl:7b"))
        self.assertTrue(ModelRouter.local_model_allowed("gemma3:4b"))

    def test_one_shot_local_model_passes_keep_alive_to_ollama(self):
        router=ModelRouter()
        calls=[]
        router._ollama_generate=lambda model,prompt,keep_alive=None: calls.append((model,prompt,keep_alive)) or "ok"
        self.assertEqual(router.local("repair","qwen2.5-coder:7b",task="coding",keep_alive=0),"ok")
        self.assertEqual(calls,[("qwen2.5-coder:7b","repair",0)])


if __name__=="__main__":
    unittest.main()
