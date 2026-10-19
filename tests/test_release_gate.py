import unittest
from release_gate import REQUIRED, assess


class GateTests(unittest.TestCase):
    def test_empty_fails(self):
        self.assertFalse(assess({})['ready'])

    def test_missing_evidence_fails(self):
        self.assertFalse(assess({'checks': {k: {'status': 'pass'} for k in REQUIRED}})['ready'])

    def test_all_verified_passes(self):
        self.assertTrue(assess({'checks': {k: {'status': 'pass', 'evidence': 'artifact:sha256'} for k in REQUIRED}})['ready'])

    def test_extra_failure_blocks(self):
        checks = {k: {'status': 'pass', 'evidence': 'artifact:sha256'} for k in REQUIRED}
        checks['garuda'] = {'status': 'fail'}
        self.assertFalse(assess({'checks': checks})['ready'])

    def test_not_tested_blocks(self):
        checks = {k: {'status': 'pass', 'evidence': 'artifact:sha256'} for k in REQUIRED}
        checks['android_apk'] = {'status': 'not_tested'}
        self.assertFalse(assess({'checks': checks})['ready'])


if __name__ == '__main__':
    unittest.main()
