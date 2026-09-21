import hashlib, tempfile, unittest
from pathlib import Path
from krishna_core.device_pairing import DevicePairingStore
from krishna_core.mobile_gateway import MobileGateway
from krishna_core.mobile_rpc import MobileRPC

class GatewayTest(unittest.TestCase):
    def test_pair_auth_and_rpc_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            store=DevicePairingStore(d)
            req=store.request("phone-1","KRISHNA Mobile")
            auth=store.approve(req["request_id"])
            gw=MobileGateway(store,MobileRPC({"chat.send":lambda p:{"echo":p["text"]}}))
            self.assertEqual(gw.call("phone-1",auth["token"],"chat.send",{"text":"hi"})["echo"],"hi")
            with self.assertRaises(PermissionError): gw.call("phone-1",auth["token"],"system.run",{"cmd":"whoami"})
            with self.assertRaises(PermissionError): gw.call("phone-1","bad","chat.send",{"text":"x"})
    def test_pairing_queue_and_device_id_are_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            store=DevicePairingStore(d,max_pending=2)
            store.request("phone-a","A")
            store.request("phone-b","B")
            with self.assertRaises(RuntimeError):
                store.request("phone-c","C")
            with self.assertRaises(ValueError):
                store.request("x"*161,"Too long")
            with self.assertRaises(ValueError):
                store.request("bad\ndevice","Bad")

    def test_corrupt_pairing_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            store=DevicePairingStore(d)
            store.paired_file.write_text("{broken",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                store.verify("phone","credential")
            with self.assertRaises(RuntimeError):
                store.request("phone-new","Mobile")

    def test_zero_code_client_hash_pairing(self):
        with tempfile.TemporaryDirectory() as d:
            store=DevicePairingStore(d)
            token="client-generated-credential-that-never-crosses-as-plaintext"
            digest=hashlib.sha256(token.encode()).hexdigest()
            req=store.request("phone-zero","KRISHNA Mobile",digest)
            self.assertNotIn("credential_sha256",req)
            pending=store.pending()
            self.assertTrue(pending["pending"][0]["credential_proposed"])
            approved=store.approve(req["request_id"])
            self.assertTrue(approved["approved"])
            self.assertNotIn("token",approved)
            self.assertTrue(store.verify("phone-zero",token))

if __name__=="__main__": unittest.main()
