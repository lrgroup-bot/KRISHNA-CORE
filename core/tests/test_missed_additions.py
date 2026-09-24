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
from krishna_core.narad.providers import NaradProviderHub
from krishna_core.model_memory_governor import ModelMemoryGovernor
from krishna_core.garudanetra_session import GarudanetraSessionManager, BrowserSession
import json
import queue
import threading


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

    def test_remote_paired_route_allowlist_is_conversation_only(self):
        p=PrivateRemotePolicy("100.64.0.0/10")
        for path in ("/api/core/chat","/api/chats/create","/api/attachments","/api/mobile/resume"):
            with self.subTest(path=path):
                self.assertTrue(p.mobile_route_allowed(path))
        for path in ("/api/mobile/control","/api/projects/unregister","/api/plugins/add","/api/development/git/push",
                     "/api/narad/connections/register-secret","/api/resilience/models/unload"):
            with self.subTest(path=path):
                self.assertFalse(p.mobile_route_allowed(path))

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
            else:
                row=v.put("x","test","secret-value")
                self.assertEqual(v.resolve(row["id"]),"secret-value")
                raw=(Path(td)/"s.json").read_text("utf-8")
                self.assertNotIn("secret-value",raw)

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
            with self.assertRaises(ValueError):w.verify(d["id"])
            d=w.verify(d["id"],evidence="manual Bluetooth audio loopback passed")
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
        with self.assertRaises(PermissionError):n.execute(w["id"],approved=True)
        n.promote(w["id"],"verified",verified=True,approved=True);n.promote(w["id"],"stable",verified=True,approved=True)
        with self.assertRaises(PermissionError):n.execute(w["id"],approved=False)
        out=n.execute(w["id"],approved=True)
        self.assertEqual(out["results"][0]["provider"],"slack")

    def test_narad_provider_hub_has_all_planned_connectors(self):
        providers=set(NaradProviderHub().providers())
        self.assertTrue({"telegram","discord","slack","whatsapp","gmail","google_drive","google_sheets","google_calendar"}<=providers)

    def test_model_memory_governor_no_action_below_threshold(self):
        g=ModelMemoryGovernor("http://127.0.0.1:1")
        self.assertFalse(g.relieve(70,90)["acted"])

    def test_garudanetra_modes_and_rich_actions(self):
        with tempfile.TemporaryDirectory() as td:
            m=GarudanetraSessionManager(td)
            self.assertEqual(m.validate_mode("task_memory"),"task_memory")
            with self.assertRaises(ValueError):m.validate_mode("personal_chrome")
            with self.assertRaises(PermissionError):m.create("KRISHNA","https://example.com","persistent_workspace",False)
            s=BrowserSession("s","KRISHNA","https://example.com",mode="task_memory",remember_evidence=True)
            m._sessions["s"]=s;m._commands["s"]=queue.Queue()
            for action in ("back","forward","reload","new_tab","switch_tab","type_text","drag_xy","upload"):
                m.command("s",action,{})
            with self.assertRaises(ValueError):m.command("s","shell",{})

    def test_garudanetra_redacts_url_secrets_in_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            m=GarudanetraSessionManager(td)
            s=BrowserSession("s","KRISHNA","https://user:pass@example.com/x?token=abc&safe=1#access_token=xyz",
                             mode="task_memory",remember_evidence=True,
                             current_url="https://example.com/current?api_key=secret&ok=yes")
            s.network=[{"method":"GET","url":"https://example.com/n?session=secret","status":200,"at":0}]
            s.tabs=[{"index":0,"url":"https://example.com/t?auth=secret","title":"T"}]
            snap=m._snapshot(s)
            blob=json.dumps(snap)
            self.assertNotIn("user:pass",blob)
            self.assertNotIn("abc",blob)
            self.assertNotIn("secret",blob)
            self.assertIn("REDACTED",blob)

    def test_garudanetra_close_all_waits_for_threads(self):
        with tempfile.TemporaryDirectory() as td:
            m=GarudanetraSessionManager(td)
            s=BrowserSession("s","KRISHNA","https://example.com")
            m._sessions["s"]=s
            m._commands["s"]=queue.Queue()
            done=threading.Event()
            def worker():
                cmd=m._commands["s"].get(timeout=1)
                if cmd["action"]=="stop":
                    s.stopped=True
                    done.set()
            t=threading.Thread(target=worker)
            m._threads["s"]=t
            t.start()
            status=m.close_all(timeout=1)
            self.assertTrue(done.is_set())
            self.assertEqual(status["running"],0)

    def test_worker_supervisor_status_contract(self):
        with tempfile.TemporaryDirectory() as td:
            f=WorkerFabric(td)
            f.register("x",["missing-command-for-contract-test"],autostart=False)
            s=WorkerResilienceSupervisor(f,interval=1)
            self.assertIn("workers",s.status())
            self.assertFalse(s.status()["workers"]["x"]["quarantined"])


if __name__=="__main__":unittest.main()
