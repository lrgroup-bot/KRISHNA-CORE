"""Loopback HTTP integration for operator popups, asset serving and CSRF."""
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from suryadev import Library
import suryadev_extras


class LocalOperatorHttpTests(unittest.TestCase):
    def test_popup_assets_and_csrf_protected_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            lib = Library(directory)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
            sock.close()
            holder = {}
            created = threading.Event()
            def real_factory(address, handler):
                server = ThreadingHTTPServer(address, handler)
                holder["server"] = server
                created.set()
                return server
            def run_server():
                suryadev_extras.serve(lib, port)
            with patch.object(suryadev_extras, "ThreadingHTTPServer",
                              side_effect=real_factory):
                thread = threading.Thread(target=run_server, daemon=True)
                thread.start()
                self.assertTrue(created.wait(timeout=5))
            def request(method, path, body=None, headers=None):
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                try:
                    content = json.dumps(body).encode("utf-8") if body is not None else None
                    outgoing = dict(headers or {})
                    if content is not None:
                        outgoing["Content-Type"] = "application/json"
                    connection.request(method, path, body=content, headers=outgoing)
                    reply = connection.getresponse()
                    data = reply.read()
                    return reply.status, data
                finally:
                    connection.close()
            try:
                status, html = request("GET", "/advanced")
                self.assertEqual(status, 200)
                self.assertIn(b'id="server-settings-dialog"', html)
                self.assertIn(b'id="storage-settings-dialog"', html)
                status, _ = request("GET", "/dashboard-settings.css")
                self.assertEqual(status, 200)
                status, js = request("GET", "/dashboard-settings.js")
                self.assertEqual(status, 200)
                self.assertIn(b"/api/operator/server/save", js)
                status, data = request("GET", "/api/ui-version")
                self.assertEqual(status, 200)
                self.assertTrue(json.loads(data)["has_storage_settings"])
                self.assertTrue(json.loads(data)["has_youtube_learning_audit"])
                status, data = request("GET", "/api/youtube/audit")
                self.assertEqual(status, 200)
                audit=json.loads(data)
                self.assertTrue(audit["read_only"])
                self.assertEqual(audit["schema"],"suryadev.youtube-learning-audit.v1")
                self.assertEqual(audit["counts"]["rishi_exams_verified"],0)
                status, data = request("GET", "/api/operator/settings")
                self.assertEqual(status, 200)
                secret = json.loads(data)["csrf_token"]
                self.assertGreater(len(secret), 30)
                endpoint = "/api/operator/server/save"
                payload = {"ip":"192.168.0.100","port":8766}
                status, _ = request("POST", endpoint, payload)
                self.assertEqual(status, 403)
                status, _ = request("POST", endpoint, payload, headers={
                    "Origin":f"http://127.0.0.1:{port}",
                    "X-SURYADEV-CSRF":"invalid"
                })
                self.assertEqual(status, 403)
                headers = {
                    "Origin":f"http://127.0.0.1:{port}",
                    "X-SURYADEV-CSRF":secret
                }
                status, saved = request("POST", endpoint, payload, headers=headers)
                self.assertEqual(status, 200)
                self.assertFalse(json.loads(saved)["paired"])
                # Retired source enrollment endpoints cannot be revived by
                # old frontend bundles or same-origin scripts with a CSRF token.
                for retired, body in (
                    ("/api/operator/learning/activate-sources", {}),
                    ("/api/operator/video/approve-source",
                        {"url":"https://www.youtube.com/watch?v=mgBpcQRDtl0"}),
                    ("/api/operator/video/auto",{"enabled":True}),
                    ("/api/operator/video/import",{"job":{}}),
                    ("/api/operator/video/run",{"job_id":"missing","approved":True})
                ):
                    with self.subTest(retired=retired):
                        denied, reason=request("POST",retired,body,headers=headers)
                        self.assertEqual(denied,410)
                        self.assertIn("Manual source controls retired",
                                      json.loads(reason)["error"])
                self.assertFalse((Path(directory)/"learning-plan.json").exists())
                status, data = request("GET", "/api/operator/settings")
                self.assertEqual(json.loads(data)["server"]["ip"], "192.168.0.100")
                status, data = request("POST", "/api/operator/storage/check",
                                       {"path":str(Path(directory).parent / "new-location")},
                                       headers=headers)
                self.assertEqual(status, 200)
                self.assertIn("free_bytes", json.loads(data))
                status, data = request("POST", "/api/operator/cleanup/run",
                                       {"dry_run":True}, headers=headers)
                self.assertEqual(status, 200)
                self.assertTrue(json.loads(data)["retained_evidence"])
            finally:
                holder["server"].shutdown()
                holder["server"].server_close()
                thread.join(timeout=5)
                lib.db.close()


if __name__ == "__main__":
    unittest.main()
