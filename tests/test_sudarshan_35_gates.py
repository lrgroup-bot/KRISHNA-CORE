import unittest
from tools.sudarshan_gates_35 import GATES,evaluate

class GateTests(unittest.TestCase):
 def test_35_gates(self):
  self.assertEqual(len(GATES),35)
  self.assertEqual(len(set(GATES)),35)
 def test_missing_fails_closed(self):
  self.assertFalse(evaluate({})['release_ready'])
  self.assertEqual(evaluate({})['passed'],0)
 def test_unverified_fails_closed(self):
  self.assertFalse(evaluate({GATES[0]:{'passed':True}})['release_ready'])
 def test_complete_evidence(self):
  evidence={gate:{'passed':True,'evidence_id':'sha256:sample-'+gate,'reviewer':'test-reviewer'} for gate in GATES}
  self.assertTrue(evaluate(evidence)['evidence_claims_complete'])
  self.assertFalse(evaluate(evidence)['release_ready'])
 def test_failed_gate_blocks(self):
  evidence={gate:{'passed':True,'evidence_id':'sample-'+gate,'reviewer':'reviewer'} for gate in GATES}
  evidence['security']['passed']=False
  self.assertFalse(evaluate(evidence)['release_ready'])
 def test_unknown_gate(self):
  with self.assertRaises(ValueError):evaluate({'unknown':{}})

if __name__=='__main__':unittest.main()
