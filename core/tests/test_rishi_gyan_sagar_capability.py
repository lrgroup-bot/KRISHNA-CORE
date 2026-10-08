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


if __name__ == "__main__":
    unittest.main()
