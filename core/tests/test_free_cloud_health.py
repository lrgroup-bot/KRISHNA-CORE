import os
import unittest
from unittest.mock import patch

from krishna_core.free_cloud_health import FreeCloudHealthGovernor


class FakeGateway:
    def __init__(self, profiles):
        self._profiles=profiles
        self.calls=[]
    def list(self):
        return {"profiles":self._profiles,"count":len(self._profiles)}
    def request_json(self, profile_id, path, payload=None, method=None, timeout=120):
        self.calls.append((profile_id,path,method))
        return {"data":[{"id":"gemini-3.8-flash"},{"id":"gpt-oss-120b"},{"id":"mistral-small-latest"}]}


class FakeOpenRouter:
    def status(self, refresh=False):
        return {
            "configured":True,
            "catalog":{"cached":True,"fetched_at":123.0,"model_count":5,"error":None},
        }
    def _find_catalog_row(self, model_id, refresh=True):
        if model_id=="moonshotai/kimi-k2.6:free":
            return {"id":model_id,"pricing":{"prompt":"0","completion":"0"}}
        return None
    def _expired(self,row): return False
    def _pricing_zero(self,pricing): return pricing.get("prompt")=="0" and pricing.get("completion")=="0"


class FakeCloudflare:
    def status(self, refresh=False):
        return {
            "configured":True,
            "automatic_zero_cost_eligible":bool(refresh),
            "verification":{"billing_guard":"ok"} if refresh else None,
        }


def profile(pid,name,base,model):
    return {
        "id":pid,"name":name,"base_url":base,"model":model,
        "free_only":True,"enabled":True,"credential_available":True,
    }


class FreeCloudHealthGovernorTests(unittest.TestCase):
    def setUp(self):
        self.profiles=[
            profile("or","OpenRouter-Free","https://openrouter.ai/api/v1","openrouter/free"),
            profile("kimi","Kimi-Free","https://openrouter.ai/api/v1","moonshotai/kimi-k2.6:free"),
            profile("cf","cloudflare-workers-ai-free","https://api.cloudflare.com/client/v4/accounts/a","@cf/meta/llama-3.1-8b-instruct"),
            profile("gem","Gemini-Free","https://generativelanguage.googleapis.com/v1beta/openai","gemini-3.8-flash"),
            profile("hf","HuggingFace-Free","https://router.huggingface.co/v1","openai/gpt-oss-120b:groq"),
        ]
        self.gateway=FakeGateway(self.profiles)
        self.governor=FreeCloudHealthGovernor(self.gateway,FakeOpenRouter(),FakeCloudflare())

    def test_verified_zero_cost_paths_are_unattended_and_nvidia_not_needed(self):
        out=self.governor.status(refresh=True)
        by={x["family"]:x for x in out["profiles"]}
        self.assertTrue(by["openrouter"]["unattended_allowed"])
        self.assertTrue(by["cloudflare"]["unattended_allowed"])
        self.assertFalse(out["nvidia"]["needed"])
        self.assertFalse(out["automatic_paid_fallback"])
        self.assertEqual(out["background_workers"],0)

    def test_duplicate_kimi_profile_is_delegated_not_generic_unattended(self):
        out=self.governor.status(refresh=True,max_age=0)
        row=next(x for x in out["profiles"] if x["family"]=="kimi-openrouter")
        self.assertFalse(row["unattended_allowed"])
        self.assertEqual(row["billing_safety"],"delegate-to-openrouter-zero-cost-fabric")
        self.assertIn("OpenRouter zero-cost fabric",row["reason"])

    def test_huggingface_credit_limited_is_manual(self):
        out=self.governor.status(refresh=True,max_age=0)
        row=next(x for x in out["profiles"] if x["family"]=="huggingface")
        self.assertFalse(row["unattended_allowed"])
        self.assertEqual(row["billing_safety"],"credit-consumption-capable")

    def test_generic_provider_health_does_not_become_billing_proof(self):
        out=self.governor.status(refresh=True,max_age=0)
        row=next(x for x in out["profiles"] if x["family"]=="gemini")
        self.assertTrue(row["connectivity"]["healthy"])
        self.assertFalse(row["unattended_allowed"])
        self.assertEqual(row["billing_safety"],"free-tier-health-only-not-zero-charge-proof")

    def test_owner_declared_free_cannot_bypass_strict_zero_credit_policy(self):
        with patch.dict(os.environ,{"KRISHNA_TRUST_DECLARED_FREE_PROVIDERS":"gemini"},clear=False):
            governor=FreeCloudHealthGovernor(self.gateway,FakeOpenRouter(),FakeCloudflare())
            out=governor.status(refresh=True)
        row=next(x for x in out["profiles"] if x["family"]=="gemini")
        self.assertFalse(row["unattended_allowed"])
        self.assertEqual(out["monetary_credit_consumption"],"forbidden")

    def test_refresh_uses_metadata_only_for_generic_provider(self):
        self.governor.status(refresh=True)
        calls=[x for x in self.gateway.calls if x[0]=="gem"]
        self.assertEqual(calls,[("gem","/models","GET")])


if __name__=="__main__":
    unittest.main()
