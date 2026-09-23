import unittest
from krishna_core.sudarshan_project_orchestrator import *
from krishna_core.project_bootstrap import REQUIRED_CONTEXT
class T(unittest.TestCase):
 def test_start_blocks_missing(self):self.assertEqual(SudarshanProjectOrchestrator().start("p",{})["state"],"BLOCKED_CONTEXT")
 def test_start_loaded(self):
  c={x:True for x in REQUIRED_CONTEXT};self.assertEqual(SudarshanProjectOrchestrator().start("p",c)["state"],"DISCOVERY")
 def test_complete_requires_runtime(self):
  o=SudarshanProjectOrchestrator();self.assertEqual(o.completion({"tests":True},True,False)["state"],"POST_DEPLOY_VERIFY")
  self.assertTrue(o.completion({"tests":True},True,True)["complete"])
if __name__=="__main__":unittest.main()
