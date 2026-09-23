import unittest
from krishna_core.project_bootstrap import *
from krishna_core.idea_intake import *
class T(unittest.TestCase):
 def test_loader_blocks_incomplete_context(self):
  self.assertFalse(ProjectBootstrap().load("p",{"source":1})["loaded"])
 def test_idea_does_not_implement_immediately(self):
  x=IdeaIntake().capture(Idea("add export"),{"phase":"2"})
  self.assertFalse(x["implementation_started"])
  y=IdeaIntake().schedule(IdeaIntake().impact(x,["architecture","tests"]))
  self.assertEqual(y["insertion"],"next-safe-boundary");self.assertTrue(y["retest_affected_work"])
if __name__=="__main__":unittest.main()
