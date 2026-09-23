import unittest
from krishna_core.sudarshan_design_engine import SudarshanDesignEngine,AcceptanceGovernor
from krishna_core.sudarshan_ui_pipeline import UIPipeline,UIEvidence
class T(unittest.TestCase):
 def test_repair_loop(self):
  p=UIPipeline(SudarshanDesignEngine("."));e=UIEvidence();c={x:True for x in AcceptanceGovernor.REQUIRED};c["visual"]=False
  self.assertEqual(p.next_action(c,e)["action"],"repair-and-retest")
if __name__=="__main__":unittest.main()
