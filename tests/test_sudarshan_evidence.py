import unittest
from tools.sudarshan_reconstruction import ReconstructionRequest,create_plan
from tools.sudarshan_evidence import record_observation,feature_coverage

class EvidenceTests(unittest.TestCase):
 def test_coverage_reports_unobserved_features(self):
  plan=create_plan(ReconstructionRequest("example","website",True,("search","checkout")))
  item=record_observation("search","interaction","local test","search submitted",b"redacted observation")
  result=feature_coverage(plan,[item])
  self.assertEqual(result["missing"],["checkout"])
  self.assertEqual(result["coverage"],0.5)
  self.assertFalse(result["release_ready"])
 def test_empty_evidence_is_rejected(self):
  with self.assertRaises(ValueError):
   record_observation("search","screenshot","local","screen",b"")
 def test_unknown_feature_is_rejected(self):
  plan=create_plan(ReconstructionRequest("example","website",True,("search",)))
  item=record_observation("checkout","manual","local","noted",b"proof")
  with self.assertRaises(ValueError):
   feature_coverage(plan,[item])
if __name__=="__main__":unittest.main()
