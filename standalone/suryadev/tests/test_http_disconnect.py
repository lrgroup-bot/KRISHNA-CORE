"""Regression: browser/client request cancellation must not crash local dashboard."""
from __future__ import annotations

import unittest

from suryadev_extras import _send_http_response


class _Writer:
    def __init__(self, error=None):
        self.error = error
        self.sent = []

    def write(self, data):
        if self.error is not None:
            raise self.error
        self.sent.append(data)


class _Handler:
    def __init__(self, error=None):
        self.wfile = _Writer(error)
        self.code = None
        self.headers = {}
        self.ended = False

    def send_response(self, status):
        self.code = status

    def send_header(self, name, value):
        self.headers[name] = value

    def end_headers(self):
        self.ended = True


class HttpClientDisconnectTests(unittest.TestCase):
    def test_successful_response_preserves_headers_and_body(self):
        h = _Handler()
        self.assertTrue(_send_http_response(h, 200, "application/json", b'{"ok":true}'))
        self.assertEqual(h.code, 200)
        self.assertEqual(h.headers["Content-Length"], str(len(b'{"ok":true}')))
        self.assertEqual(h.headers["Cache-Control"], "no-store")
        self.assertEqual(h.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'none'", h.headers["Content-Security-Policy"])
        self.assertTrue(h.ended)
        self.assertEqual(h.wfile.sent, [b'{"ok":true}'])

    def test_aborted_windows_or_posix_request_is_not_server_failure(self):
        for exc in (
            ConnectionAbortedError(10053, "Client aborted request"),
            ConnectionResetError(10054, "Client reset request"),
            BrokenPipeError(32, "Broken pipe"),
        ):
            with self.subTest(exception=type(exc).__name__):
                h = _Handler(exc)
                self.assertFalse(_send_http_response(h, 200, "application/json", b'{"ok":true}'))
                self.assertTrue(h.ended)

    def test_unrelated_server_write_failure_is_not_hidden(self):
        with self.assertRaises(PermissionError):
            _send_http_response(_Handler(PermissionError("Unexpected server failure")),
                                200, "text/plain", b"x")


if __name__ == "__main__":
    unittest.main()
