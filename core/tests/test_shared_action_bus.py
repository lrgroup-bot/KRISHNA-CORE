import tempfile
import unittest
from pathlib import Path

from krishna_core.automation_bus import AutomationBus
from krishna_core.policy_kernel import PolicyKernel
from krishna_core.shared_action_bus import SharedActionBus


class SharedActionBusTests(unittest.TestCase):
    def make_bus(self,permission_resolver=None):
        self.audit=[]
        return SharedActionBus(
            AutomationBus(),PolicyKernel(Path(tempfile.gettempdir())/"krishna-action-bus-test"),
            audit=lambda action,status,details:self.audit.append((action,status,details)),
            permission_resolver=permission_resolver,
        )

    def test_dispatch_has_real_action_envelope_audit_and_event(self):
        bus=self.make_bus()
        bus.register("chat.rename",lambda payload,ctx:{"title":payload["title"]},
                     mutating=True,permissions=("chat.write",))
        out=bus.dispatch("chat.rename",{"title":"Alpha"},project="KRISHNA",source="pc",actor="ui")
        self.assertEqual(out["status"],"completed")
        self.assertTrue(out["action_id"])
        self.assertEqual(out["result"]["title"],"Alpha")
        self.assertEqual(bus.recent(1)[0]["action_id"],out["action_id"])
        self.assertTrue(self.audit)
        topics=[x["topic"] for x in bus.event_bus.recent()]
        self.assertIn("action.requested",topics)
        self.assertIn("action.completed",topics)

    def test_idempotency_does_not_execute_twice(self):
        bus=self.make_bus(); calls=[]
        bus.register("chat.create",lambda payload,ctx:calls.append(payload) or {"chat_id":"c1"})
        first=bus.dispatch("chat.create",{"title":"X"},idempotency_key="k1")
        second=bus.dispatch("chat.create",{"title":"X"},idempotency_key="k1")
        self.assertEqual(len(calls),1)
        self.assertEqual(first["action_id"],second["action_id"])
        self.assertTrue(second["idempotent_replay"])

    def test_source_and_permission_contracts_block_before_handler(self):
        calls=[]
        def resolver(spec,context):
            required=set(spec.permissions);granted=set(context.get("permissions") or [])
            return (required.issubset(granted),"missing permission")
        bus=self.make_bus(resolver)
        bus.register("project.write",lambda payload,ctx:calls.append(1),
                     permissions=("project.write",),sources=("pc","agent"))
        with self.assertRaises(PermissionError):
            bus.dispatch("project.write",{},source="mobile",permissions=("project.write",))
        with self.assertRaises(PermissionError):
            bus.dispatch("project.write",{},source="agent",permissions=())
        self.assertEqual(calls,[])

    def test_approval_and_rollback_are_explicit(self):
        bus=self.make_bus()
        bus.register("thing.undo",lambda payload,ctx:{"undone":payload["original_action"]["action_id"]},
                     mutating=True,requires_approval=True)
        bus.register("thing.change",lambda payload,ctx:{"changed":True},
                     mutating=True,rollback_action="thing.undo")
        changed=bus.dispatch("thing.change",{})
        with self.assertRaises(PermissionError):
            bus.rollback(changed["action_id"],approved=False)
        rolled=bus.rollback(changed["action_id"],approved=True)
        self.assertEqual(rolled["status"],"completed")
        self.assertEqual(rolled["result"]["undone"],changed["action_id"])

    def test_sensitive_payload_is_redacted_from_action_history(self):
        bus=self.make_bus()
        bus.register("safe.echo",lambda payload,ctx:{"ok":True})
        out=bus.dispatch("safe.echo",{"token":"abc","nested":{"password":"xyz"},"text":"hello"})
        self.assertEqual(out["payload"]["token"],"[REDACTED]")
        self.assertEqual(out["payload"]["nested"]["password"],"[REDACTED]")
        self.assertEqual(out["payload"]["text"],"hello")


if __name__=="__main__":
    unittest.main()
