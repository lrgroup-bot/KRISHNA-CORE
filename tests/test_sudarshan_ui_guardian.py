import unittest
from tools.sudarshan_ui_guardian import validate_plan, run_browser

BASE = {'url': 'http://127.0.0.1:8766/health',
        'steps': [{'action': 'expect_visible', 'selector': 'body'}]}

class UIGuardianTests(unittest.TestCase):
    def test_owner_approval_required(self):
        with self.assertRaises(PermissionError):
            run_browser(BASE)

    def test_local_browser_plan_accepted(self):
        self.assertIn('127.0.0.1', validate_plan(BASE))

    def test_unapproved_host_blocked(self):
        with self.assertRaises(PermissionError):
            validate_plan({'url': 'https://example.com', 'steps': BASE['steps']})

    def test_external_host_must_be_explicit(self):
        item = dict(BASE, url='https://example.com', allow_hosts=['example.com'])
        self.assertIn('example.com', validate_plan(item))

    def test_unsupported_script_actions_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan({'url': BASE['url'], 'steps': [{'action': 'eval', 'selector': 'body'}]})

    def test_fill_value_required(self):
        with self.assertRaises(ValueError):
            validate_plan({'url': BASE['url'], 'steps': [{'action': 'fill', 'selector': 'input'}]})

    def test_mobile_emulation_validated(self):
        item = dict(BASE, device='mobile_emulation')
        self.assertTrue(validate_plan(item))

if __name__ == '__main__':
    unittest.main()
