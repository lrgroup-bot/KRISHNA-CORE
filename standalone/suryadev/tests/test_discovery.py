import unittest
from unittest.mock import patch, MagicMock
from suryadev_discovery import candidates, discover, probe

class DiscoveryTests(unittest.TestCase):
    def test_local_subnet_only(self):
        result = candidates(["192.168.20.8"])
        self.assertEqual(len(result), 253)
        self.assertIn("192.168.20.1", result)
        self.assertNotIn("192.168.20.8", result)

    def test_public_interfaces_not_scanned(self):
        self.assertEqual(candidates(["8.8.8.8", "127.0.0.1"]), [])

    def test_untrusted_health_candidate(self):
        response = MagicMock()
        response.status = 200
        response.headers = {"Content-Length": "16"}
        response.read.return_value = b'{"status":"ok"}'
        response.__enter__.return_value = response
        with patch("suryadev_discovery.build_opener") as opener:
            opener.return_value.open.return_value = response
            item = probe("192.168.20.10")
        self.assertFalse(item["trusted"])
        self.assertEqual(item["health"]["status"], "ok")

    def test_reject_oversized_body_without_length_header(self):
        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.read.return_value = b"x" * 8193
        response.__enter__.return_value = response
        with patch("suryadev_discovery.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertIsNone(probe("192.168.20.10"))

    def test_never_probe_public_host(self):
        self.assertIsNone(probe("8.8.8.8"))

if __name__ == "__main__":
    unittest.main()
