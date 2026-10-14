import tempfile, unittest
from krishna_core.vishwakarma_research import VishwakarmaResearchShishya
class ResearchShishyaTests(unittest.TestCase):
    def test_proposal_is_research_only_and_zero_spend(self):
        with tempfile.TemporaryDirectory() as d:
            s=VishwakarmaResearchShishya(d)
            p=s.record(source_name="X",source_url="https://example.invalid/x",source_version="1",
              license="MIT",what_it_does="test",krishna_benefit="test",expected_efficiency_gain="unknown until benchmark",
              security_privacy_risk="review required",local_resource_cost="benchmark required",money_cost="₹0",
              alternatives_checked=[],affected_components=[],test_plan=["benchmark"],frontend_impact="none",rollback_plan="remove candidate")
            self.assertEqual(p["status"],"PROPOSED"); self.assertFalse(p["implementation_authorized"])
    def test_paid_proposal_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            s=VishwakarmaResearchShishya(d)
            with self.assertRaises(ValueError):
                s.record(source_name="X",source_url="x",source_version="1",license="x",what_it_does="x",krishna_benefit="x",
                 expected_efficiency_gain="x",security_privacy_risk="x",local_resource_cost="x",money_cost="₹1",
                 alternatives_checked=[],affected_components=[],test_plan=[],frontend_impact="x",rollback_plan="x")
if __name__=="__main__": unittest.main()
