import tempfile,unittest
from krishna_core.vishvakarma_rishi import *
class T(unittest.TestCase):
 def test_provenance_and_retrieval(self):
  with tempfile.TemporaryDirectory() as d:
   r=VishvakarmaRishi(d);r.learn(DesignFinding("repo@commit","accessibility","Keyboard focus must remain visible","MIT",0.9,"test"))
   self.assertEqual(r.retrieve("keyboard")[0]["source"],"repo@commit")
 def test_rejects_unprovenanced(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):VishvakarmaRishi(d).learn(DesignFinding("","ui","x"))
if __name__=="__main__":unittest.main()
