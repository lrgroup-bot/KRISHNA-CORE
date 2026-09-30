import unittest
from krishna_core.prahari import Prahari
from krishna_core.local_model_evolution import LocalModelEvolution
class Tests(unittest.TestCase):
 def test_prahari_routes_failure(self):
  p=Prahari();p.expect("X");self.assertEqual(p.observe("X",state="FAILED")["route"],"MRITYUNJAY")
 def test_model_never_auto_promotes(self):
  e=LocalModelEvolution(lambda:{"ram_gb":16,"vram_gb":8,"disk_free_gb":100})
  row={"model_id":"x","source":"official","license":"Apache-2.0","size_gb":2,"ram_gb":4,"vram_gb":2}
  self.assertTrue(e.evaluate(row)["eligible_for_download"]);self.assertFalse(e.evaluate(row)["auto_promote"])

if __name__=="__main__":unittest.main()
