import unittest
from tools.sudarshan_mirofish import Scenario,prepare_scenario,assess_simulation

class MiroFishAdapterTests(unittest.TestCase):
 def test_evidence_required(self):
  with self.assertRaises(ValueError):
   prepare_scenario(Scenario("kuber","chart","test usability",(),("trader",)))
 def test_sandbox_never_auto_approves(self):
  plan=prepare_scenario(Scenario("kuber","chart","compare dashboard usability",("observation-1",),("novice trader","risk manager")))
  result=assess_simulation(plan,{"summary":"hypothetical preferences"})
  self.assertFalse(plan["execution_enabled"])
  self.assertFalse(result["eligible_for_auto_implementation"])
  self.assertTrue(result["requires_real_world_tests"])
 def test_invalid_report(self):
  plan=prepare_scenario(Scenario("kuber","chart","compare",("e1",),("tester",)))
  with self.assertRaises(ValueError):
   assess_simulation(plan,{})
if __name__=="__main__":unittest.main()
