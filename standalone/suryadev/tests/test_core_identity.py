import unittest
from suryadev_core_identity import verify_candidate

class IdentityTests(unittest.TestCase):
    def test_matching_identity(self):
        candidate = {"host": "192.168.1.10", "health": {"instance_id": "server-a"}}
        self.assertTrue(verify_candidate(candidate, expected_host="192.168.1.10", expected_identity="server-a"))
        self.assertFalse(verify_candidate(candidate, expected_host="192.168.1.11", expected_identity="server-a"))
        self.assertFalse(verify_candidate(candidate, expected_host="192.168.1.10", expected_identity="server-b"))

    def test_missing_identity_fails_closed(self):
        self.assertFalse(verify_candidate({"host": "192.168.1.10", "health": {"status": "ok"}},
                                          expected_host="192.168.1.10", expected_identity="server-a"))

if __name__ == "__main__":
    unittest.main()
