import unittest
from tools.sudarshan_execution_contract import AdapterResult,ENGINES,prepare_handoff,readiness

class ContractTests(unittest.TestCase):
 def test_authorization(self):
  with self.assertRaises(PermissionError):prepare_handoff('p','f',False,[])
 def test_missing_engines_block(self):
  h=prepare_handoff('p','f',True,[AdapterResult('REA','passed','sha256:a','observed')])
  self.assertFalse(readiness(h)['ready_for_human_review'])
  self.assertIn('MiroFish',readiness(h)['missing'])
 def test_invalid_pass_evidence(self):
  with self.assertRaises(ValueError):prepare_handoff('p','f',True,[AdapterResult('REA','passed','','missing')])
 def test_duplicate_engine(self):
  with self.assertRaises(ValueError):prepare_handoff('p','f',True,[AdapterResult('REA','blocked','',''),AdapterResult('REA','blocked','','')])
 def test_full_handoff(self):
  results=[AdapterResult(engine,'passed','sha256:'+engine,'verified test') for engine in sorted(ENGINES)]
  h=prepare_handoff('p','f',True,results)
  self.assertTrue(readiness(h)['ready_for_human_review'])
  self.assertFalse(h['deployment_allowed'])
  self.assertEqual(len(h['digest']),64)

if __name__=='__main__':unittest.main()
