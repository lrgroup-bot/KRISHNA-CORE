import unittest
from krishna_core.cognitive_fabric import *

class CognitiveFabricTests(unittest.TestCase):
    def test_related_memory_attaches(self): self.assertEqual(branch_decision(.9,salience=.8),"attach")
    def test_distant_salient_memory_branches(self): self.assertEqual(branch_decision(.1,salience=.9),"new_branch")
    def test_distant_unimportant_event_stays_episode(self): self.assertEqual(branch_decision(.1,salience=.1),"episodic_only")
    def test_prediction_error_detects_wrong_state(self): self.assertEqual(prediction_error(True,False),1)
    def test_replay_prioritizes_unresolved_surprise(self):
        low=replay_score(novelty=.1,usefulness=.2,surprise=.1,contradiction=0,uncertainty=.1,prediction_error_value=0)
        high=replay_score(novelty=.8,usefulness=.8,surprise=.9,contradiction=.8,uncertainty=.8,prediction_error_value=1)
        self.assertGreater(high,low)
    def test_idea_without_evidence_potential_scores_zero(self):
        self.assertEqual(idea_score(novelty=1,utility=1,plausibility=1,cross_domain_distance=1,evidence_potential=0),0)
    def test_cognitive_candidate_cannot_self_verify(self):
        x=cognitive_candidate("idea",{"x":1},.9);self.assertFalse(x["verified"]);self.assertEqual(x["status"],"candidate")

if __name__=="__main__":unittest.main()
