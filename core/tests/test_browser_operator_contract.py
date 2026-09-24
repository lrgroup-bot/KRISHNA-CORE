import inspect
import unittest
from krishna_core.browser_operator import BrowserOperator

class BrowserOperatorContractTests(unittest.TestCase):
    def test_inspect_supports_viewport_contract(self):
        sig=inspect.signature(BrowserOperator.inspect)
        self.assertIn("viewport",sig.parameters)
        self.assertIn("screenshot_path",sig.parameters)
        self.assertIn("actions",sig.parameters)

    def test_network_failure_console_noise_is_not_double_counted(self):
        findings=BrowserOperator.summarize_findings(
            console_errors=["Failed to load resource: net::ERR_CONNECTION_REFUSED"],
            failed_requests=["GET http://127.0.0.1:9999/x :: net::ERR_CONNECTION_REFUSED"],
        )
        self.assertEqual(len(findings),1)
        self.assertEqual(findings[0]["kind"],"request_failed")
        self.assertIn("127.0.0.1:9999",findings[0]["detail"])

if __name__=="__main__": unittest.main()
