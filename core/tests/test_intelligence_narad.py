import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.automation_bus import AutomationBus
from krishna_core.narad import NaradRuntime
from krishna_core.specialist_registry import SpecialistRegistry
from krishna_core.context_governor import ContextGovernor
from krishna_core.integrations import CodebaseMemoryAdapter, GraftMemoryAdapter

class IntelligenceNaradTests(unittest.TestCase):
    def test_optional_adapters_fail_closed(self):
        self.assertFalse(CodebaseMemoryAdapter(executable="").status()["available"])
        self.assertFalse(GraftMemoryAdapter(executable="").status()["available"])
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

if __name__=="__main__": unittest.main()
