import os
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.automation_bus import AutomationBus
from krishna_core.narad import NaradRuntime
from krishna_core.narad.scheduler import NaradScheduler
from krishna_core.narad.credentials import NaradCredentialVault
from krishna_core.specialist_registry import SpecialistRegistry
from krishna_core.context_governor import ContextGovernor
from krishna_core.integrations import CodebaseMemoryAdapter, GraftMemoryAdapter
from krishna_core.media_adapter import OpenMontageAdapter

class IntelligenceNaradTests(unittest.TestCase):
    def test_scheduler_status_is_valid_before_start(self):
        class Runtime:
            def run_due(self): return {"due":0,"results":[]}
        scheduler=NaradScheduler(Runtime(),poll_seconds=5)
        status=scheduler.status()
        self.assertFalse(status["running"])
        self.assertEqual(status["run_count"],0)
        self.assertIsNone(status["last_error"])

    def test_optional_adapters_fail_closed(self):
        self.assertFalse(CodebaseMemoryAdapter(executable="").status()["available"])
        self.assertFalse(GraftMemoryAdapter(executable="").status()["available"])
    def test_cbm_discovers_configured_existing_binary(self):
        with TemporaryDirectory() as td:
            exe=Path(td)/"codebase-memory-mcp.exe"; exe.write_bytes(b"stub")
            with patch.dict(os.environ,{"KRISHNA_CBM_BIN":str(exe)}):
                status=CodebaseMemoryAdapter().status()
            self.assertTrue(status["available"])
            self.assertEqual(status["discovery"],"environment")
            self.assertEqual(Path(status["executable"]),exe.resolve())

    def test_openmontage_distinguishes_install_from_execution_bridge(self):
        class Workers:
            def __init__(self): self.workers={}
            def register(self,name,command,cwd=None,kind=None,autostart=False):
                self.workers[name]={"name":name,"command":command,"cwd":str(cwd),"kind":kind,"autostart":autostart,"process":None}
            def describe(self,name): return {"name":name,"kind":self.workers[name]["kind"],"running":False}
        with TemporaryDirectory() as td:
            home=Path(td)/"OpenMontage"; py=home/".venv/Scripts/python.exe"
            py.parent.mkdir(parents=True); py.write_bytes(b"stub")
            with patch.dict(os.environ,{"OPENMONTAGE_CMD":""}):
                m=OpenMontageAdapter(Workers(),home=home,python=py)
                status=m.status()
                self.assertTrue(status["installed"])
                self.assertFalse(status["available"])
                self.assertFalse(status["bridge_ready"])
                with self.assertRaises(RuntimeError): m.start()

    def test_openmontage_registers_only_explicit_bridge_command(self):
        class Workers:
            def __init__(self): self.workers={}
            def register(self,name,command,cwd=None,kind=None,autostart=False):
                self.workers[name]={"name":name,"command":command,"cwd":str(cwd),"kind":kind,"autostart":autostart,"process":None}
            def describe(self,name): return {"name":name,"kind":self.workers[name]["kind"],"running":False}
        with TemporaryDirectory() as td:
            home=Path(td)/"OpenMontage"; py=home/".venv/Scripts/python.exe"
            py.parent.mkdir(parents=True); py.write_bytes(b"stub")
            workers=Workers()
            m=OpenMontageAdapter(workers,home=home,python=py,command="python bridge.py")
            d=m.register_command_bridge()
            self.assertEqual(d["name"],"openmontage")
            self.assertEqual(workers.workers["openmontage"]["kind"],"media")

    def test_specialists_have_independent_verifier(self):
        names={x["name"] for x in SpecialistRegistry().list()}
        self.assertIn("verifier",names); self.assertIn("code-investigator",names)
    def test_context_governor_prefers_verified(self):
        g=ContextGovernor(max_items=1)
        out=g.select([{"text":"a","score":99,"verified":False},{"text":"b","score":1,"verified":True}])
        self.assertEqual(out[0]["text"],"b")
    def test_narad_lifecycle_and_policy(self):
        with TemporaryDirectory() as td:
            bus=AutomationBus(); n=NaradRuntime(PolicyKernel(Path(td)),bus)
            w=n.create_workflow("safe",{"type":"manual"},[{"action":"publish_event","topic":"x"}])
            with self.assertRaises(RuntimeError): n.execute(w["id"])
            n.promote(w["id"],"sandbox")
            r=n.execute(w["id"]); self.assertEqual(r["results"][0]["event"]["topic"],"x")
            with self.assertRaises(PermissionError): n.promote(w["id"],"stable")
            n.promote(w["id"],"verified",verified=True)
            n.promote(w["id"],"stable",verified=True)
    def test_narad_blocks_unapproved_mutation(self):
        with TemporaryDirectory() as td:
            n=NaradRuntime(PolicyKernel(Path(td)),AutomationBus())
            w=n.create_workflow("mut",{"type":"manual"},[{"action":"send_external","mutating":True}])
            n.promote(w["id"],"sandbox")
            with self.assertRaises(PermissionError): n.execute(w["id"],approved=False)

    def test_durable_state_roundtrip(self):
        with TemporaryDirectory() as td:
            state=Path(td)/"narad.json"
            n=NaradRuntime(PolicyKernel(Path(td)),AutomationBus(),state_path=state)
            w=n.create_workflow("persist",{"type":"manual"},[{"action":"publish_event","topic":"persist"}])
            restored=NaradRuntime(PolicyKernel(Path(td)),AutomationBus(),state_path=state)
            self.assertIn(w["id"],restored.workflows)

    def test_webhook_is_always_high_impact(self):
        with TemporaryDirectory() as td:
            n=NaradRuntime(PolicyKernel(Path(td)),AutomationBus(),{"n8n":object()})
            w=n.create_workflow("hook",{"type":"manual"},[{"action":"adapter_webhook","provider":"n8n","url":"https://example.invalid"}])
            n.promote(w["id"],"sandbox")
            with self.assertRaises(PermissionError): n.execute(w["id"],approved=False)

    def test_schedule_trigger_runs_stable_workflow(self):
        with TemporaryDirectory() as td:
            n=NaradRuntime(PolicyKernel(Path(td)),AutomationBus(),state_path=Path(td)/"narad.json")
            with self.assertRaises(ValueError):
                n.create_workflow("too-fast",{"type":"schedule","every_seconds":30},[{"action":"publish_event","topic":"x"}])
            w=n.create_workflow("hourly",{"type":"schedule","every_seconds":3600},[{"action":"publish_event","topic":"scheduled"}])
            n.promote(w["id"],"sandbox");n.promote(w["id"],"verified",verified=True);n.promote(w["id"],"stable",verified=True)
            out=n.run_due(now=10000)
            self.assertEqual(out["due"],1)
            self.assertEqual(out["results"][0]["result"]["trigger_source"],"schedule")
            self.assertEqual(n.run_due(now=10001)["due"],0)

    def test_webhook_token_is_hashed_and_invalid_token_fails(self):
        with TemporaryDirectory() as td:
            state=Path(td)/"narad.json"
            n=NaradRuntime(PolicyKernel(Path(td)),AutomationBus(),state_path=state)
            w=n.create_workflow("incoming",{"type":"webhook"},[{"action":"publish_event","topic":"incoming"}])
            n.promote(w["id"],"sandbox");n.promote(w["id"],"verified",verified=True);n.promote(w["id"],"stable",verified=True)
            hook=n.provision_webhook(w["id"])
            raw=state.read_text(encoding="utf-8")
            self.assertNotIn(hook["token"],raw)
            out=n.handle_webhook(hook["token"],{"hello":"world"})
            self.assertEqual(out["trigger_source"],"webhook")
            with self.assertRaises(PermissionError): n.handle_webhook("wrong",{})

    def test_credential_vault_persists_only_secret_reference(self):
        with TemporaryDirectory() as td:
            path=Path(td)/"credentials.json";vault=NaradCredentialVault(path)
            ref=vault.register("N8N","n8n","KRISHNA_TEST_N8N_TOKEN")
            self.assertFalse(ref["available"])
            with patch.dict(os.environ,{"KRISHNA_TEST_N8N_TOKEN":"super-secret-value"}):
                self.assertEqual(vault.headers(ref["id"])["Authorization"],"Bearer super-secret-value")
                self.assertTrue(vault.describe(ref["id"])["available"])
            raw=path.read_text(encoding="utf-8")
            self.assertNotIn("super-secret-value",raw)
            self.assertIn("KRISHNA_TEST_N8N_TOKEN",raw)

    def test_corrupt_narad_state_fails_closed_without_overwrite(self):
        with TemporaryDirectory() as td:
            state=Path(td)/"narad.json"
            state.write_text("{broken",encoding="utf-8")
            n=NaradRuntime(PolicyKernel(Path(td)),AutomationBus(),state_path=state)
            self.assertFalse(n.status()["available"])
            before=state.read_text(encoding="utf-8")
            with self.assertRaises(RuntimeError):
                n.create_workflow("must-not-overwrite",{"type":"manual"},[{"action":"publish_event","topic":"x"}])
            self.assertEqual(state.read_text(encoding="utf-8"),before)

    def test_corrupt_narad_credential_state_fails_closed_without_overwrite(self):
        with TemporaryDirectory() as td:
            path=Path(td)/"credentials.json"
            path.write_text("{broken",encoding="utf-8")
            vault=NaradCredentialVault(path)
            status=vault.list()
            self.assertFalse(status["available"])
            before=path.read_text(encoding="utf-8")
            with self.assertRaises(RuntimeError):
                vault.register("Broken","n8n","KRISHNA_TOKEN")
            with self.assertRaises(RuntimeError):
                vault.resolve("missing")
            self.assertEqual(path.read_text(encoding="utf-8"),before)

    def test_dead_letter_retry_can_succeed_only_with_explicit_approval(self):
        class Adapter:
            def post(self,url,payload,headers=None,timeout=15):
                return {"status":200,"body":"ok","headers_seen":bool(headers)}
        with TemporaryDirectory() as td:
            n=NaradRuntime(PolicyKernel(Path(td)),AutomationBus(),{"n8n":Adapter()},state_path=Path(td)/"narad.json")
            w=n.create_workflow("external",{"type":"manual"},[{"action":"adapter_webhook","provider":"n8n","url":"https://example.invalid"}])
            n.promote(w["id"],"sandbox")
            with self.assertRaises(PermissionError): n.execute(w["id"],approved=False)
            letter=n.dead_letter_status()["dead_letters"][0]
            with self.assertRaises(PermissionError): n.retry_dead_letter(letter["id"],approved=False)
            with self.assertRaises(PermissionError): n.retry_dead_letter(letter["id"],approved=True)
            n.promote(w["id"],"verified",verified=True);n.promote(w["id"],"stable",verified=True)
            result=n.retry_dead_letter(letter["id"],approved=True)
            self.assertEqual(result["dead_letter"]["status"],"retried")
            self.assertEqual(result["result"]["results"][0]["status"],200)

if __name__=="__main__": unittest.main()
