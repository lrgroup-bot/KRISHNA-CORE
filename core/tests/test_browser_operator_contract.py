import inspect
import unittest
from krishna_core.browser_operator import BrowserOperator

class BrowserOperatorContractTests(unittest.TestCase):
    def test_inspect_supports_viewport_contract(self):
        sig=inspect.signature(BrowserOperator.inspect)
        self.assertIn("viewport",sig.parameters)
        self.assertIn("screenshot_path",sig.parameters)
        self.assertIn("actions",sig.parameters)

if __name__=="__main__": unittest.main()
