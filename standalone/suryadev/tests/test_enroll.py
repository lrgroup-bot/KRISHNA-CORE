import ssl
import unittest
from unittest.mock import patch, MagicMock
from suryadev_enroll import enroll

class EnrollmentTests(unittest.TestCase):
    def test_reject_http(self):
        with self.assertRaises(ValueError):
            enroll("http://192.168.0.10:8766/enroll", "code", "a"*64)

    def test_reject_unspecified_endpoint(self):
        with self.assertRaises(ValueError):
            enroll("https://core.example/", "code", "a"*64)

    def test_reject_bad_pin(self):
        with self.assertRaises(ValueError):
            enroll("https://core.example/enroll", "code", "invalid")

    def test_reject_mismatched_certificate_before_post(self):
        conn = MagicMock()
        conn.sock.getpeercert.return_value = b"certificate"
        with patch("suryadev_enroll.http.client.HTTPSConnection", return_value=conn):
            with self.assertRaises(ssl.SSLError):
                enroll("https://core.example/enroll", "code", "a"*64)
        conn.request.assert_not_called()
        conn.close.assert_called_once()

    def test_successful_response_is_minimal(self):
        import hashlib
        pin = hashlib.sha256(b"certificate").hexdigest()
        conn = MagicMock()
        conn.sock.getpeercert.return_value = b"certificate"
        response = MagicMock(status=200)
        response.read.return_value = b'{"paired":true,"secret":"must-not-return"}'
        conn.getresponse.return_value = response
        with patch("suryadev_enroll.http.client.HTTPSConnection", return_value=conn):
            result = enroll("https://core.example/enroll", "code", pin)
        self.assertTrue(result["paired"])
        self.assertNotIn("secret", str(result))

if __name__ == "__main__":
    unittest.main()
