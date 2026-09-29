import unittest

from krishna_core.capability_fabric import CapabilityFabric
from krishna_core.load_relief_integrations import LoadReliefIntegrationCatalog, StemkitOnDemand, StrixSandboxContract
from krishna_core.system_one import SystemOneDecisionEngine


class LoadReliefCapabilityTests(unittest.TestCase):
    def test_system_one_is_advisory_and_probabilities_sum_to_one(self):
        engine=SystemOneDecisionEngine()
        out=engine.choose(
            {"task":"quick routine mobile question"},
            ["mobile_free_cloud","pc_heavy"],
            allow_remote=False,
        )
        self.assertEqual(out["authority"],"advisory-only")
        self.assertAlmostEqual(sum(out["probabilities"].values()),1.0,places=5)
        self.assertEqual(out["choice"],"mobile_free_cloud")

    def test_system_one_private_context_prefers_pc(self):
        engine=SystemOneDecisionEngine()
        out=engine.choose(
            {"privacy":"private credential protected local only"},
            ["mobile_cloud","pc_private"],
            allow_remote=False,
        )
        self.assertEqual(out["choice"],"pc_private")

    def test_capability_fabric_mobile_prefers_mobile_or_cloud_without_resident_load(self):
        fabric=CapabilityFabric(SystemOneDecisionEngine())
        fabric.register("mobile-free","general","cloud",free_only=True,resident=False)
        fabric.register("pc-heavy","general","pc",free_only=True,resident=False,heavy=True,sensitive_allowed=True)
        out=fabric.route("general",mobile=True,sensitive=False)
        self.assertEqual(out["selected"],"mobile-free")
        self.assertEqual(fabric.status()["resident_provider_count"],0)

    def test_sensitive_route_filters_mobile_cloud(self):
        fabric=CapabilityFabric(SystemOneDecisionEngine())
        fabric.register("mobile-vision","vision","cloud",free_only=True,sensitive_allowed=False)
        fabric.register("pc-vision","vision","pc",free_only=True,sensitive_allowed=True,heavy=True)
        out=fabric.route("vision",mobile=True,sensitive=True,heavy=True)
        self.assertEqual(out["selected"],"pc-vision")

    def test_integrations_are_zero_spend_and_nonresident(self):
        status=LoadReliefIntegrationCatalog().status()
        self.assertFalse(status["automatic_paid_fallback"])
        self.assertEqual(status["heavy_resident_services"],0)
        ids={x["integration_id"] for x in status["integrations"]}
        for expected in (
            "openjev","deepseek-harness-patterns","dots3-note","dots-tts",
            "dots-mocr","stemkit","strix","daily-stock-analysis",
            "eromify-patterns","google-maps-scraper-patterns",
        ):
            self.assertIn(expected,ids)
        self.assertTrue(all(not x["paid_fallback"] for x in status["integrations"]))
        self.assertTrue(all(not x["resident"] for x in status["integrations"]))

    def test_strix_external_requires_owner_approval(self):
        contract=StrixSandboxContract()
        with self.assertRaises(PermissionError):
            contract.plan("https://example.test",external=True,approved=False)
        local=contract.plan("candidate-app",candidate_root="/tmp/candidate",external=False)
        self.assertEqual(local["network"],"deny-by-default")
        self.assertFalse(local["promotion"])

    def test_stemkit_is_cold_when_unconfigured(self):
        status=StemkitOnDemand(module_root=None).status()
        self.assertFalse(status["configured"])
        self.assertFalse(status["resident"])
        self.assertFalse(status["paid"])


if __name__=="__main__":
    unittest.main()
