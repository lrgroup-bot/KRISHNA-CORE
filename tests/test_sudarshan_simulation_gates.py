import unittest
from tools.sudarshan_simulation_gates import SIMULATION_GATES,evaluate_simulation_gates

class SimulationGateTests(unittest.TestCase):
 def test_ten_gates(self):
  self.assertEqual(len(SIMULATION_GATES),10)
  self.assertEqual(evaluate_simulation_gates({})["validated"],0)
 def test_simulation_is_not_validation(self):
  result=evaluate_simulation_gates({"stakeholder_simulation":{"source":"sim-1","verified":True}})
  self.assertEqual(result["gates"]["stakeholder_simulation"],"simulation_only")
 def test_real_world_evidence_required(self):
  result=evaluate_simulation_gates({"prediction_validation":{"source":"trial-1","verified":True,"real_world_test":True}})
  self.assertEqual(result["gates"]["prediction_validation"],"validated")
 def test_unknown_gate_rejected(self):
  with self.assertRaises(ValueError):evaluate_simulation_gates({"unrecognized":{}})
if __name__=="__main__":unittest.main()
