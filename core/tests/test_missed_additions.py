import tempfile
import unittest
from pathlib import Path

from krishna_core.project_registry import ProjectRegistry, ProjectPolicy
from krishna_core.remote_access import PrivateRemotePolicy
from krishna_core.secure_vault import SecureSecretVault, SecretVaultUnavailable
from krishna_core.model_gateway import ModelGatewayRegistry
from krishna_core.vision_adapter import VisionAdapter
from krishna_core.native_voice import KrishnaVoiceStack
from krishna_core.wearable_bridge import WearableBridge
from krishna_core.worker_fabric import WorkerFabric, WorkerResilienceSupervisor
from krishna_core.narad.runtime import NaradRuntime


class FakePolicy:
    class D:
        def __init__(self,allowed=True,reason="ok"):self.allowed=allowed;self.reason=reason
    def action(self,name,mutating=False,approved=False):
        return self.D(bool(approved) if name=="send_external" else True,"approval required" if not approved else "ok")


class FakeBus:
    def publish(self,*a,**k):return {"published":True}


class FakeHub:
    def providers(self):return ["slack"]
    def send(self,provider,operation,payload,headers=None):
        return {"provider":provider,"operation":operation,"payload":payload,"headers":headers or {}}


class FakeCreds:
    def list(self):return {"count":1}
    def headers(self,ref):return {"Authorization":"Bearer hidden"}


class MissedAdditionsTests(unittest.TestCase):
    def test_project_roles_block_mutation(self):
        r=ProjectRegistry()
        r.register(ProjectPolicy("backup",".",allowed_actions=["edit"],role="protected"))
        self.assertFalse(r.can("backup","edit",mutating=True))
        self.assertTrue(r.can("backup","edit",mutating=False))
        with self.assertRaises(PermissionError):r.assert_mutable("backup","edit")

    def test_remote_policy_rejects_public_internet(self):
        p=PrivateRemotePolicy("100.64.0.0/10")
        self.assertTrue(p.allowed("127.0.0.1"))
        self.assertTrue(p.allowed("192.168.1.5"))
        self.assertTrue(p.allowed("100.100.10.20"))
        self.assertFalse(p.allowed("8.8.8.8"))

    def test_secure_vault_fails_closed_off_windows(self):
        with tempfile.TemporaryDirectory() as td:
            v=SecureSecretVault(Path(td)/"s.json")
            self.assertIn("windows-dpapi",v.list()["backend"])
            if not v.available:
                with self.assertRaises(SecretVaultUnavailable):v.put("x","test","secret")

    def test_model_gateway_enforces_https_for_remote(self):
        with tempfile.TemporaryDirectory() as td:
            g=ModelGatewayRegistry(Path(td)/"g.json",SecureSecretVault(Path(td)/"s.json"))
            with self.assertRaises(ValueError):g._validate_url("http://example.com/v1")
            self.assertEqual(g._validate_url("http://127.0.0.1:1234/v1"),"http://127.0.0.1:1234/v1")
            self.assertEqual(g._validate_url("https://example.com/v1"),"https://example.com/v1")

    def test_local_vision_accepts_only_images(self):
        v=VisionAdapter()
        with self.assertRaises(ValueError):v.analyze_bytes(b"x","text/plain","inspect")
        self.assertTrue(v.status()["local"])

    def test_native_voice_stack_is_local_and_honest(self):
        s=KrishnaVoiceStack().status()
        self.assertEqual(s["language"],"or-IN")
        self.assertTrue(s["stt"]["local"])
        self.assertTrue(s["tts"]["local"])
        self.assertEqual(s["wake"]["wake_word"],"Krishna")
        self.assertIn("activation signal",s["wake"]["security_note"])

    def test_wearable_capabilities_are_verification_gated(self):
        with tempfile.TemporaryDirectory() as td:
            w=WearableBridge(Path(td)/"wearables.json")
            d=w.register("test headset","headset",["bluetooth_audio","microphone"])
            self.assertFalse(d["verified"])
            d=w.verify(d["id"])
            self.assertTrue(d["verified"])
            self.assertIn("bluetooth_audio",w.status()["verified_capabilities"])
            with self.assertRaises(ValueError):w.register("fake","glasses",["unverified_magic_display"])

    def test_narad_provider_send_requires_approval(self):
        n=NaradRuntime(FakePolicy(),FakeBus(),state_path=None,credentials=FakeCreds(),provider_hub=FakeHub())
        w=n.create_workflow("slack",{"type":"manual"},[
            {"action":"provider_send","provider":"slack","operation":"send_message","credential_ref":"c1","payload":{"channel":"C","text":"hi"}}
        ])
        n.promote(w["id"],"sandbox")
        with self.assertRaises(PermissionError):n.execute(w["id"],approved=False)
        out=n.execute(w["id"],approved=True)
        self.assertEqual(out["results"][0]["provider"],"slack")

    def test_worker_supervisor_status_contract(self):
        with tempfile.TemporaryDirectory() as td:
            f=WorkerFabric(td)
            f.register("x",["missing-command-for-contract-test"],autostart=False)
            s=WorkerResilienceSupervisor(f,interval=1)
            self.assertIn("workers",s.status())
            self.assertFalse(s.status()["workers"]["x"]["quarantined"])


if __name__=="__main__":unittest.main()
