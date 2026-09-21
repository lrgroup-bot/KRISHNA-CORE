import json
import socket
import tempfile
import time
import unittest
from pathlib import Path

from krishna_core.lan_discovery import DISCOVERY_MAGIC, LanDiscoveryService, discovery_payload
from krishna_core.model_gateway import GatewayProfile, ModelGatewayRegistry
from krishna_core.secure_vault import SecureSecretVault, SecretVaultUnavailable


class LanDiscoveryAndSafetyTests(unittest.TestCase):
    def test_discovery_payload_contains_only_service_metadata(self):
        data=json.loads(discovery_payload(8766).decode("utf-8"))
        self.assertEqual(data["service"],"KRISHNA_CORE")
        self.assertEqual(data["port"],8766)
        self.assertNotIn("token",data)
        self.assertNotIn("secret",data)
        self.assertNotIn("device",data)

    def test_udp_discovery_round_trip(self):
        probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        probe.bind(("127.0.0.1",0));port=probe.getsockname()[1];probe.close()
        service=LanDiscoveryService(8766,discovery_port=port,bind_host="127.0.0.1")
        service.start()
        try:
            deadline=time.time()+2
            last=None
            while time.time()<deadline:
                try:
                    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                        s.settimeout(.25)
                        s.sendto(DISCOVERY_MAGIC,("127.0.0.1",port))
                        raw,_=s.recvfrom(1024)
                        data=json.loads(raw.decode("utf-8"))
                        self.assertEqual(data["service"],"KRISHNA_CORE")
                        self.assertEqual(data["port"],8766)
                        return
                except OSError as exc:
                    last=exc;time.sleep(.05)
            self.fail(f"LAN discovery did not answer: {last}")
        finally:
            service.stop()

    def test_corrupt_secret_vault_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"vault.json";path.write_text("{broken",encoding="utf-8")
            vault=SecureSecretVault(path)
            self.assertTrue(vault.load_error)
            self.assertFalse(vault.list()["available"])
            with self.assertRaises(SecretVaultUnavailable):
                vault.delete("anything")

    def test_gateway_delete_does_not_forget_profile_if_secret_delete_fails(self):
        class BrokenVault:
            available=True
            def delete(self,_):raise RuntimeError("vault delete failed")
            def list(self):return {"available":True}
        with tempfile.TemporaryDirectory() as td:
            registry=ModelGatewayRegistry(Path(td)/"gateways.json",BrokenVault())
            row=GatewayProfile("p1","x","https://example.com","m","s1",True,True,1)
            registry.profiles[row.id]=row
            with self.assertRaises(RuntimeError):
                registry.delete(row.id)
            self.assertIn(row.id,registry.profiles)


if __name__=="__main__":
    unittest.main()
