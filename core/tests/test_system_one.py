import unittest

from krishna_core.system_one import SystemOneDecisionEngine


class SystemOneDecisionEngineTests(unittest.TestCase):
    def test_local_bounded_ranking_needs_no_model_process(self):
        engine=SystemOneDecisionEngine(endpoint="")
        out=engine.decide(
            "choose mobile route",
            ["mobile-free-cloud","krishna-pc"],
            signals={"preferred":"mobile-free-cloud"},
        )
        self.assertEqual(out["choice"],"mobile-free-cloud")
        self.assertEqual(out["engine"],"deterministic-heuristic")
        self.assertFalse(out["escalated"])
        self.assertEqual(engine.status()["pc_ram_reserved_mb"],0)

    def test_high_stakes_never_gets_probabilistic_authority(self):
        out=SystemOneDecisionEngine().decide(
            "approve payment",["allow","block"],decision_class="payment"
        )
        self.assertTrue(out["escalated"])
        self.assertEqual(out["choice"],"")
        self.assertEqual(out["engine"],"policy-escalation")

    def test_requires_bounded_options(self):
        with self.assertRaises(ValueError):
            SystemOneDecisionEngine().decide("x",["only"])


if __name__=="__main__":
    unittest.main()
