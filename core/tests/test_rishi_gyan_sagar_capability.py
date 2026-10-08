import unittest

from krishna_core.capability_fabric import CapabilityFabric


class RishiGyanSagarCapabilityTests(unittest.TestCase):
    def test_research_and_rights_capabilities_are_registered_without_resident_load(self):
        fabric = CapabilityFabric()
        research = fabric.route("knowledge.research")
        rights = fabric.route("knowledge.rights", sensitive=True)

        self.assertEqual(research["selected"], "rishi-gyan-sagar")
        self.assertEqual(rights["selected"], "rishi-rights-gate")
        self.assertFalse(research["provider"]["resident"])
        self.assertFalse(rights["provider"]["resident"])
        self.assertTrue(research["provider"]["free_only"])
        self.assertTrue(rights["provider"]["free_only"])

    def test_capability_registration_keeps_idle_load_zero(self):
        status = CapabilityFabric().status()
        self.assertEqual(status["resident_provider_count"], 0)
        self.assertIn("never starts provider runtimes", status["idle_load_policy"])

    def test_orchestrator_fabric_can_plan_rishi_sources_without_network_execution(self):
        fabric = CapabilityFabric()
        out = fabric.knowledge_plan("clinical medicine and diagnosis", rishi_id="sushruta", max_sources=8)
        self.assertEqual(out["route"]["selected"], "rishi-gyan-sagar")
        self.assertEqual(out["plan"]["lead_rishi"], "sushruta")
        ids = {x["id"] for x in out["plan"]["sources"]}
        self.assertIn("europe-pmc", ids)
        self.assertIn("pmc", ids)
        self.assertIn("Shared Action Bus", out["execution"])

    def test_capability_fabric_can_build_bounded_request_contract(self):
        out = CapabilityFabric().knowledge_request("openalex", "solid state battery")
        self.assertEqual(out["route"]["selected"], "rishi-gyan-sagar")
        self.assertIn("search=solid+state+battery", out["request"]["url"])
        self.assertIn("permission-gated", out["execution"])

    def test_capability_fabric_exposes_fail_closed_rights_gate(self):
        out = CapabilityFabric().knowledge_rights(
            "archive", license_id="", source_default_max_mode="index"
        )
        self.assertEqual(out["route"]["selected"], "rishi-rights-gate")
        self.assertFalse(out["decision"]["allowed"])
        self.assertTrue(out["decision"]["review_required"])

    def test_knowledge_status_is_lazy_but_complete(self):
        out = CapabilityFabric().knowledge_status()
        self.assertEqual(out["route"]["selected"], "rishi-gyan-sagar")
        self.assertGreaterEqual(out["sagar"]["source_count"], 25)


if __name__ == "__main__":
    unittest.main()
