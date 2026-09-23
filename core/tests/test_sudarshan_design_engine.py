import unittest
from krishna_core.sudarshan_design_engine import *
class T(unittest.TestCase):
 def test_selective_router(self):
  s=SkillRouter().select(DesignJob("frontend",reference_image=True))
  self.assertIn("image-to-code",s);self.assertIn("playwright-cli",s);self.assertNotIn("stagehand",s)
 def test_drift(self):
  self.assertFalse(DesignDrift().compare({"radius":8},{"radius":12})["pass"])
 def test_acceptance_is_hard_gate(self):
  checks={x:True for x in AcceptanceGovernor.REQUIRED};checks["accessibility"]=False
  self.assertFalse(AcceptanceGovernor().evaluate(checks)["verified"])
if __name__=="__main__":unittest.main()
