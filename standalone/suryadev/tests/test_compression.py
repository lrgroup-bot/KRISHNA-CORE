import gzip
import unittest
from email.message import Message
from unittest.mock import MagicMock, patch
from suryadev import fetch_text

class Response:
    def __init__(self, body, encoding="gzip"):
        self.body = body
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        self.headers["Content-Encoding"] = encoding
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, n): return self.body[:n]

class CompressionTests(unittest.TestCase):
    @patch("suryadev.validate_url")
    @patch("suryadev.build_opener")
    def test_gzip_html(self, opener, validate):
        opener.return_value.open.return_value = Response(gzip.compress(b"<title>Good</title><h1>Readable research</h1>"))
        title, text = fetch_text("https://example.com")
        self.assertEqual(title, "Good")
        self.assertIn("Readable research", text)

    @patch("suryadev.validate_url")
    @patch("suryadev.build_opener")
    def test_binary_rejected(self, opener, validate):
        opener.return_value.open.return_value = Response(b"\x00\x01\x02", "identity")
        with self.assertRaises(ValueError):
            fetch_text("https://example.com")

    @patch("suryadev.validate_url")
    @patch("suryadev.build_opener")
    def test_gzip_bomb_rejected(self, opener, validate):
        opener.return_value.open.return_value = Response(gzip.compress(b"A" * 2000001))
        with self.assertRaises(ValueError):
            fetch_text("https://example.com")

if __name__ == "__main__":
    unittest.main()
