import unittest
from tools.sudarshan_behavior import Transition,inspect_transitions,compare_observed

class BehaviorTests(unittest.TestCase):
 def test_valid_graph(self):
  t=Transition("search","home","submit query","results","matching results")
  self.assertTrue(inspect_transitions({"search"},[t])["valid"])
 def test_duplicate_action(self):
  t=Transition("search","home","submit query","results","matching results")
  self.assertIn("duplicate_action:search",inspect_transitions({"search"},[t,t])["issues"])
 def test_comparison(self):
  result=compare_observed({"screen":"results","count":3},{"screen":"results","count":4})
  self.assertEqual(result["differing"],["count"])
  self.assertFalse(result["matched"])
if __name__=="__main__":unittest.main()
