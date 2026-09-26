import unittest

from krishna_core.direct_free import VerifiedDirectFreeFabric, VerifiedFreePolicyError


class FakeGateway:
    def __init__(self, *, model="@cf/nvidia/nemotron-3-120b-a12b", subscriptions=None,
                 subscription_error=None):
        self.calls = []
        self.model = model
        self.subscription_error = subscription_error
        self.subscriptions = [] if subscriptions is None else subscriptions

    def list(self):
        return {
            "profiles": [{
                "id": "cf1",
                "name": "Cloudflare Workers AI Free",
                "base_url": "https://api.cloudflare.com/client/v4/accounts/abcdef1234567890",
                "model": self.model,
                "free_only": True,
                "enabled": True,
                "credential_backend": "windows-dpapi",
                "credential_available": True,
                "created_at": 10,
            }]
        }

    def request_json(self, profile_id, path, payload=None, method=None, timeout=120, zero_credit_proof=None):
        self.calls.append({
            "profile_id": profile_id, "path": path, "payload": payload,
            "method": method, "timeout": timeout, "zero_credit_proof":zero_credit_proof,
        })
        if path == "/subscriptions":
            if self.subscription_error:
                raise RuntimeError(self.subscription_error)
            return {"success": True, "result": self.subscriptions}
        if path == "/ai/v1/chat/completions":
            return {"choices": [{"message": {"content": "free-worker-ok"}}]}
        raise AssertionError(path)


class VerifiedDirectFreeFabricTests(unittest.TestCase):
    def test_cloudflare_free_account_is_verified_before_inference(self):
        fabric = VerifiedDirectFreeFabric(FakeGateway())
        out = fabric.complete("public research question", privacy="approved_cloud")
        self.assertEqual(out["text"], "free-worker-ok")
        self.assertTrue(out["zero_cost_verified"])
        self.assertFalse(out["paid_fallback"])
        paths = [x["path"] for x in fabric.gateway.calls]
        self.assertEqual(paths, ["/subscriptions", "/ai/v1/chat/completions"])
        self.assertEqual(out["zero_cost_proof"]["free_allocation_neurons_per_day"], 10000)

    def test_workers_free_subscription_is_accepted(self):
        subs = [{
            "id": "workers-free",
            "state": "Provisioned",
            "price": 0,
            "rate_plan": {"id": "free", "public_name": "Workers Free", "sets": ["workers"]},
        }]
        fabric = VerifiedDirectFreeFabric(FakeGateway(subscriptions=subs))
        self.assertTrue(fabric.status(refresh=True)["automatic_zero_cost_eligible"])

    def test_workers_paid_subscription_blocks_automatic_route(self):
        subs = [{
            "id": "workers-paid",
            "state": "Paid",
            "price": 5,
            "rate_plan": {"id": "pro", "public_name": "Workers Paid", "sets": ["workers"]},
        }]
        fabric = VerifiedDirectFreeFabric(FakeGateway(subscriptions=subs))
        with self.assertRaises(VerifiedFreePolicyError):
            fabric.complete("must never bill", privacy="approved_cloud")
        self.assertFalse(any(x["path"] == "/ai/v1/chat/completions" for x in fabric.gateway.calls))

    def test_billing_read_failure_fails_closed(self):
        fabric = VerifiedDirectFreeFabric(FakeGateway(subscription_error="403 Billing Read required"))
        with self.assertRaises(VerifiedFreePolicyError):
            fabric.complete("do not guess the plan", privacy="approved_cloud")
        self.assertFalse(any(x["path"] == "/ai/v1/chat/completions" for x in fabric.gateway.calls))

    def test_paid_only_cloudflare_model_is_denied_before_inference(self):
        fabric = VerifiedDirectFreeFabric(FakeGateway(model="@cf/moonshotai/kimi-k2.7-code"))
        with self.assertRaises(VerifiedFreePolicyError):
            fabric.complete("coding", privacy="approved_cloud")
        self.assertEqual(fabric.gateway.calls, [])

    def test_non_cloudflare_gateway_model_is_not_eligible(self):
        fabric = VerifiedDirectFreeFabric(FakeGateway(model="openai/gpt-5.5"))
        self.assertFalse(fabric.configured())
        with self.assertRaises(RuntimeError):
            fabric.verify()

    def test_private_sensitive_and_secret_payloads_stay_local(self):
        fabric = VerifiedDirectFreeFabric(FakeGateway())
        with self.assertRaises(PermissionError):
            fabric.complete("hello", privacy="local_only")
        with self.assertRaises(PermissionError):
            fabric.complete("hello", privacy="approved_cloud", sensitive=True)
        with self.assertRaises(PermissionError):
            fabric.complete("api_key=super-secret-value", privacy="approved_cloud")
        self.assertEqual(fabric.gateway.calls, [])


if __name__ == "__main__":
    unittest.main()
