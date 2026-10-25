"""Cross-package pairing contract: current Core zero-code store and
portable SURYADEV client agree without transmitting a plaintext device token.

This is an offline protocol test, NOT a physical HTTPS enrollment claim.
"""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "standalone" / "suryadev"))

from krishna_core.device_pairing import DevicePairingStore
from suryadev_pairing_bootstrap import request_pairing, activate_pairing, TOKEN, CONFIG
from suryadev_krishna_mission import load_config


class OwnerPairedDeviceContractTests(unittest.TestCase):
    def test_pending_approval_must_be_granted_before_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "node"
            pairing = DevicePairingStore(root / "core")
            device = "suryadev-physical-canary-test"
            def relay(origin, digest, method, route, *, payload=None, device="", token=""):
                self.assertEqual(origin,"https://192.168.0.100:8443")
                self.assertEqual(digest,"b"*64)
                if method == "POST":
                    self.assertEqual(route,"/api/mobile/pair/request")
                    row = pairing.request(payload["device_id"],payload["name"],
                                          payload["credential_sha256"])
                    return 200,row
                self.assertEqual((method,route),("GET","/api/suryadev/device/status"))
                if not pairing.verify(device,token):
                    return 401, {"error":"paired Suryadev device required"}
                return 404, {"error":"Suryadev node has not sent a heartbeat yet"}
            pending=request_pairing(node,"https://192.168.0.100:8443","b"*64,
                                     device,sender=relay)
            self.assertEqual(pairing.pending()["count"],1)
            self.assertEqual(pairing.paired()["count"],0)
            with self.assertRaises(PermissionError):
                activate_pairing(node,sender=relay)
            self.assertFalse((node/CONFIG).exists())
            confirmed=pairing.approve(pending["request_id"])
            self.assertTrue(confirmed["approved"])
            self.assertEqual(confirmed["mode"],"client-hash-zero-code")
            self.assertNotIn("token",confirmed)
            approved=activate_pairing(node,sender=relay)
            self.assertEqual(approved["state"],"paired_configuration_active")
            config=load_config(node/CONFIG)
            self.assertEqual(config["device_id"],device)
            self.assertTrue(pairing.verify(device,config["credential"]))
            pairing.revoke(device)
            self.assertFalse(pairing.verify(device,config["credential"]))
            # Config bytes remain for owner-controlled reapproval or removal;
            # no automatic repair bypasses explicit revocation.
            self.assertTrue((node/TOKEN).is_file())


if __name__=="__main__":
    unittest.main()
