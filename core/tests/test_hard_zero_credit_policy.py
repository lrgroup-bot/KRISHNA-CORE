import tempfile
import unittest
from pathlib import Path

from krishna_core.model_gateway import GatewayProfile, ModelGatewayRegistry
from krishna_core.zero_spend_policy import ZeroSpendPolicy


class DummyVault:
    available=True
    def describe(self, secret_id):
        return {"id":secret_id,"available":True,"backend":"windows-dpapi"}
    def resolve(self, secret_id):
        return "secret"


class HardZeroCreditPolicyTests(unittest.TestCase):
    def test_zero_spend_blocks_all_cloud_credit_types(self):
        policy=ZeroSpendPolicy()
        for op in ("api_credit","credit_purchase","promotional_api_credit","trial_credit","free_trial_credit","provider_credit","cloud_credit"):
            row=policy.decide(op)
            self.assertFalse(row["allowed"],op)
            self.assertTrue(row["hard_block"],op)
        status=policy.status()
        self.assertFalse(status["cloud_credit_use_allowed"])
        self.assertFalse(status["promotional_credit_use_allowed"])
        self.assertFalse(status["free_trial_credit_use_allowed"])
        self.assertTrue(status["zero_price_or_nonbillable_quota_only"])

    def test_gateway_post_requires_specialized_zero_credit_proof(self):
        with tempfile.TemporaryDirectory() as td:
            gateway=ModelGatewayRegistry(Path(td)/"gateways.json",DummyVault())
            row=GatewayProfile(
                "p1","Generic","https://example.com/v1","model","s1",True,True,1.0
            )
            gateway.profiles[row.id]=row
            with self.assertRaisesRegex(PermissionError,"zero-credit"):
                gateway.request_json("p1","/chat/completions",payload={"x":1},method="POST")

    def test_gateway_generic_complete_is_always_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            gateway=ModelGatewayRegistry(Path(td)/"gateways.json",DummyVault())
            row=GatewayProfile(
                "p1","Generic","https://example.com/v1","model","s1",True,True,1.0
            )
            gateway.profiles[row.id]=row
            with self.assertRaisesRegex(PermissionError,"hard zero-credit policy"):
                gateway.complete("p1","hello")


if __name__=="__main__":
    unittest.main()
