import tempfile, unittest
from krishna_core.karma_protocol import KarmaProtocol
from krishna_core.brahma_council import BrahmaCouncil
class KarmaBrahmaTests(unittest.TestCase):
 def test_consequences_reduce_permissions(self):
  with tempfile.TemporaryDirectory() as d:
   k=KarmaProtocol(d)
   for _ in range(3): k.event("worker","UNSAFE_ATTEMPT","bad")
   self.assertFalse(k.permissions("worker")["execution_allowed"])
 def test_brahma_reviews_active_inactive_and_blocks_paid(self):
  with tempfile.TemporaryDirectory() as d:
   k=KarmaProtocol(d+"/k"); b=BrahmaCouncil(d+"/b",k)
   r=b.meeting([{"name":"A","active":True},{"name":"B","active":False}],
     improvement_proposals=[{"name":"free","money_cost":"₹0"},{"name":"paid","money_cost":"₹10"}])
   self.assertEqual(r["summary"]["total_agents"],2)
   self.assertEqual(r["improvement_proposals"][0]["council_status"],"CANDIDATE")
   self.assertEqual(r["improvement_proposals"][1]["council_status"],"PAID_BLOCKED")
if __name__=="__main__":unittest.main()
