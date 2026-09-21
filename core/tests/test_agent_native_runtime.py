import tempfile
import unittest
from pathlib import Path

from krishna_core.automation_bus import AutomationBus
from krishna_core.agent_runtime import AgentRuntime
from krishna_core.dispatch_runtime import DispatchRuntime
from krishna_core.job_runtime import JobRuntime
from krishna_core.permission_runtime import PermissionRuntime
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.protocol_gateway import AgentProtocolGateway
from krishna_core.shared_action_bus import SharedActionBus
from krishna_core.task_ledger import TaskLedger


class AgentNativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.permissions=PermissionRuntime()
        self.bus=SharedActionBus(
            AutomationBus(),PolicyKernel(root/"runtime"),
            permission_resolver=self.permissions.authorize,
        )
        self.bus.register(
            "chat.create",lambda payload,ctx:{"chat_id":"c1","title":payload.get("title","New chat")},
            permissions=("chat.write",),
        )
        self.bus.register(
            "garuda.scout",lambda payload,ctx:{"goal":payload.get("goal"),"source":ctx["source"]},
            permissions=("web.read","evidence.write"),
        )
        self.ledger=TaskLedger(root/"jobs.db")
        self.agents=AgentRuntime(self.bus)
        self.agents.register(
            "garuda","research",("web.read","evidence.write"),("garuda.scout",),
        )
        self.jobs=JobRuntime(self.ledger,self.bus)
        self.protocols=AgentProtocolGateway(self.bus,self.agents)
        self.dispatch=DispatchRuntime(self.bus,self.agents,self.jobs)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_permission_runtime_requires_capabilities_for_delegated_callers(self):
        allowed,reason=self.permissions.authorize(
            type("Spec",(),{"permissions":("chat.write",)})(),
            {"source":"mcp","permissions":["chat.write"]},
        )
        self.assertTrue(allowed,reason)
        denied,reason=self.permissions.authorize(
            type("Spec",(),{"permissions":("chat.write",)})(),
            {"source":"mcp","permissions":[]},
        )
        self.assertFalse(denied)
        self.assertIn("missing capability",reason)

    def test_agent_runtime_is_action_allowlisted_and_capability_bounded(self):
        out=self.agents.dispatch("garuda","garuda.scout",{"goal":"browser fabric"})
        self.assertEqual(out["status"],"completed")
        self.assertEqual(out["source"],"agent")
        self.assertEqual(out["actor"],"garuda")
        with self.assertRaises(PermissionError):
            self.agents.dispatch("garuda","chat.create",{"title":"no"})

    def test_job_runtime_creates_durable_task_receipt(self):
        out=self.jobs.submit(
            "chat.create",{"title":"Job chat"},project="general",
            permissions=("chat.write",),
        )
        self.assertEqual(out["status"],"completed")
        job=self.ledger.get(out["job_id"])
        self.assertEqual(job["status"],"completed")
        self.assertEqual(job["phase"],"complete")
        self.assertEqual(job["detail"]["action_id"],out["action"]["action_id"])

    def test_mcp_and_a2a_are_adapters_not_separate_execution_authorities(self):
        catalog=self.protocols.mcp_catalog()
        self.assertEqual(catalog["authority"],"KRISHNA Shared Action Bus")
        names={x["name"] for x in catalog["tools"]}
        self.assertIn("chat.create",names)
        out=self.protocols.mcp_call(
            "chat.create",{"title":"MCP chat"},project="general",
            permissions=("chat.write",),request_id="mcp-1",
        )
        self.assertEqual(out["source"],"mcp")
        a2a=self.protocols.a2a_dispatch({
            "action":"chat.create","payload":{"title":"A2A chat"},"project":"general",
            "permissions":["chat.write"],"request_id":"a2a-1",
        })
        self.assertEqual(a2a["source"],"a2a")

    def test_dispatch_runtime_targets_action_agent_and_job(self):
        direct=self.dispatch.dispatch(
            "action","chat.create",{"title":"Direct"},project="general",
            permissions=("chat.write",),
        )
        self.assertEqual(direct["status"],"completed")
        agent=self.dispatch.dispatch(
            "agent","garuda.scout",{"goal":"x"},agent_id="garuda",
        )
        self.assertEqual(agent["source"],"agent")
        job=self.dispatch.dispatch(
            "job","chat.create",{"title":"Queued"},project="general",
            permissions=("chat.write",),
        )
        self.assertEqual(job["status"],"completed")
        with self.assertRaises(ValueError):
            self.dispatch.dispatch("unknown","chat.create",{})


if __name__=="__main__":
    unittest.main()
