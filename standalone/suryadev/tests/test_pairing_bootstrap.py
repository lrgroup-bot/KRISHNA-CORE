"""No network required: SURYADEV zero-code device pairing lifecycle tests."""
import hashlib
import json
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from suryadev_pairing_bootstrap import (request_pairing, activate_pairing, pinned_request,
                                         CONFIG, PENDING, TOKEN)


class PairingBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.pin = "a"*64
        self.origin = "https://192.168.0.100:8443"
        self.device = "suryadev-unit-01"
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def sender(self, origin, pin, method, path, *, payload=None, device="", token=""):
        self.calls.append((method,path,payload,device,token))
        if method == "POST":
            return 200, {"request_id":"PENDING-1","device_id":self.device,
                         "expires_at":1899999999}
        if method == "GET":
            return 404, {"error":"Suryadev node has not sent a heartbeat yet"}
        raise AssertionError("Unexpected call")

    def test_request_then_explicit_approve_then_activate(self):
        out = request_pairing(self.data,self.origin,self.pin,self.device,sender=self.sender)
        self.assertEqual(out["state"],"owner_approval_required")
        self.assertFalse((self.data / CONFIG).exists())
        sent=self.calls[0][2]
        credential=(self.data / TOKEN).read_text().strip()
        self.assertEqual(sent["credential_sha256"],
                         hashlib.sha256(credential.encode()).hexdigest())
        self.assertNotIn(credential,str(self.calls[0]))
        self.assertTrue((self.data/PENDING).exists())
        activated=activate_pairing(self.data,sender=self.sender)
        self.assertEqual(activated["state"],"paired_configuration_active")
        self.assertFalse(activated["live_network_heartbeat_verified"])
        self.assertFalse(activated["rishi_exam_verified"])
        conf=json.loads((self.data/CONFIG).read_text())
        self.assertEqual(conf["device_id"],self.device)
        self.assertEqual(conf["endpoint"],self.origin)
        self.assertTrue((self.data/TOKEN).exists())
        self.assertFalse((self.data/PENDING).exists())
        with self.assertRaises(FileExistsError):
            request_pairing(self.data,self.origin,self.pin,self.device,sender=self.sender)

    def test_unapproved_device_is_not_enabled(self):
        request_pairing(self.data,self.origin,self.pin,self.device,sender=self.sender)
        def rejected(*args,**kwargs):
            return 401, {"error":"paired Suryadev device required"}
        with self.assertRaises(PermissionError):
            activate_pairing(self.data,sender=rejected)
        self.assertFalse((self.data/CONFIG).exists())
        self.assertTrue((self.data/PENDING).exists())
        self.assertTrue((self.data/TOKEN).exists())

    def test_host_and_identity_rules(self):
        for host in ("http://192.168.0.100:8766","https://public.example.com",
                     "https://8.8.8.8:8443","https://192.168.0.100:8443/api",
                     "https://user:pass@192.168.0.100:8443"):
            with self.subTest(host=host),self.assertRaises(ValueError):
                request_pairing(self.data,host,self.pin,self.device,sender=self.sender)
        with self.assertRaises(ValueError):
            request_pairing(self.data,self.origin,self.pin,"another-node",sender=self.sender)

    def test_certificate_mismatch_happens_before_request_headers(self):
        connection=MagicMock()
        connection.sock.getpeercert.return_value=b"unexpected certificate"
        with patch("suryadev_pairing_bootstrap.http.client.HTTPSConnection",
                   return_value=connection):
            with self.assertRaises(ssl.SSLError):
                pinned_request(self.origin,self.pin,"POST",
                               "/api/mobile/pair/request",
                               payload={"credential_sha256":"token-digest"})
        connection.request.assert_not_called()
        connection.close.assert_called_once()

    def test_approval_rejects_untrusted_404(self):
        request_pairing(self.data,self.origin,self.pin,self.device,sender=self.sender)
        def wrong_404(*args,**kwargs):
            return 404,{"error":"unrecognized route"}
        with self.assertRaises(PermissionError):
            activate_pairing(self.data,sender=wrong_404)
        self.assertFalse((self.data/CONFIG).exists())


if __name__=="__main__":
    unittest.main()
