import unittest
from krishna_core.sudarshan_design_policy import *
class T(unittest.TestCase):
 def test_ui_requires_vishvakarma(self):
  p=SudarshanDesignPolicy();v=p.require("frontend",{"functional":True})
  self.assertTrue(v["required"]);self.assertFalse(v["allowed"]);self.assertIn("vishvakarma_knowledge",v["missing"])
 def test_no_empty_design_dispatch(self):
  with self.assertRaises(RuntimeError):SudarshanDesignPolicy().dispatch_context("ui",[])
 def test_backend_not_forced(self):self.assertTrue(SudarshanDesignPolicy().require("backend",{})["allowed"])
if __name__=="__main__":unittest.main()
