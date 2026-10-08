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

    def test_shared_capability_route_returns_knowledge_plan_from_context(self):
        out = CapabilityFabric().route(
            "knowledge.research",
            context={
                "topic": "Sanskrit grammar and classical texts",
                "rishi_id": "panini",
                "max_sources": 10,
            },
        )
        self.assertEqual(out["selected"], "rishi-gyan-sagar")
        self.assertEqual(out["knowledge_plan"]["lead_rishi"], "panini")
        ids = {x["id"] for x in out["knowledge_plan"]["sources"]}
        self.assertIn("sarit", ids)
        self.assertIn("dcs", ids)
        self.assertIn("Shared Action Bus", out["execution"])

    def test_shared_route_can_return_bounded_source_request_contract(self):
        out = CapabilityFabric().route(
            "knowledge.research",
            context={
                "topic": "research datasets",
                "rishi_id": "bharadvaja",
                "source_id": "datacite",
                "query": "battery recycling dataset",
                "max_sources": 10,
            },
        )
        self.assertEqual(out["request_plan"]["source_id"],"datacite")
        self.assertIn("query=battery+recycling+dataset",out["request_plan"]["url"])
        self.assertIn("Shared Action Bus",out["execution"])

    def test_shared_capability_route_returns_rights_decision(self):
        out = CapabilityFabric().route(
            "knowledge.rights",
            sensitive=True,
            context={
                "requested_mode": "archive",
                "license_id": "CC-BY-4.0",
                "source_default_max_mode": "index",
            },
        )
        self.assertEqual(out["selected"], "rishi-rights-gate")
        self.assertTrue(out["rights_decision"]["allowed"])
        self.assertTrue(out["rights_decision"]["attribution_required"])

    def test_shared_rights_route_requires_extra_review_for_cc_by_training(self):
        out = CapabilityFabric().route(
            "knowledge.rights",
            sensitive=True,
            context={
                "requested_mode": "train",
                "license_id": "CC-BY-4.0",
                "source_default_max_mode": "index",
            },
        )
        decision=out["rights_decision"]
        self.assertFalse(decision["allowed"])
        self.assertFalse(decision["training_allowed"])
        self.assertTrue(decision["review_required"])
        self.assertIn("separate model-training rights review",decision["training_policy"])

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
        self.assertGreater(out["total_source_count"],out["sagar"]["source_count"])


if __name__ == "__main__":
    unittest.main()
