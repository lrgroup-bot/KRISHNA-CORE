import unittest
from tools.sudarshan_research_ranker import rank_feature,rank_backlog

R={"user_value":5,"technical_gain":4,"reuse":4,"testability":5,"cost_maintainability":3}
C={"authorization":True,"license":True,"security":True,"privacy":True}
class ResearchRankerTests(unittest.TestCase):
 def test_no_evidence_blocks(self):
  x=rank_feature("chart",R,C)
  self.assertIn("missing_research_evidence",x["blockers"])
 def test_unreviewed_legal_blocks(self):
  x=rank_feature("chart",R,{**C,"license":False},("rea-1",))
  self.assertFalse(x["eligible_for_implementation_review"])
 def test_simulation_cannot_authorize_release(self):
  x=rank_feature("chart",R,C,("rea-1",),{"stakeholder_simulation":{"source":"mirofish-1"}})
  self.assertTrue(x["eligible_for_implementation_review"])
  self.assertFalse(x["release_ready"])
  self.assertEqual(x["simulation_gate_results"]["gates"]["stakeholder_simulation"],"simulation_only")
 def test_backlog_orders_reviewable_first(self):
  a={"feature_id":"a","ratings":R,"compliance":C,"observations":("e1",)}
  b={"feature_id":"b","ratings":R,"compliance":C}
  self.assertEqual(rank_backlog([b,a])[0]["feature_id"],"a")
if __name__=="__main__":unittest.main()
