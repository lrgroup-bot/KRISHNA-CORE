import unittest
from krishna_core.vishvakarma_team import *
class T(unittest.TestCase):
 def test_liaison_is_required(self):
  with self.assertRaises(RuntimeError):VishvakarmaTeam().brief("ui",[])
 def test_handoff(self):
  t=VishvakarmaTeam();b=t.brief("ui",[{"lesson":"visible focus"}]);h=t.handoff(b,{"screen":"home"})
  self.assertTrue(h["ready"]);self.assertEqual(h["verifier"],"Sudarshan Verifier")
if __name__=="__main__":unittest.main()
