import unittest
from krishna_core.design_adapters import StagehandAdapter,StorybookAdapter
class T(unittest.TestCase):
 def test_stagehand_opt_in(self):self.assertFalse(StagehandAdapter().available())
 def test_component_states(self):self.assertIn("error",StorybookAdapter().required_states())
if __name__=="__main__":unittest.main()
