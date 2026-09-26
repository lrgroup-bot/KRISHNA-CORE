import unittest

from krishna_core.action_registry import ActionRegistry
from krishna_core.shared_action_bus import SharedActionBus


class DuplicateRegistrationGuardTests(unittest.TestCase):
    def test_shared_action_bus_rejects_duplicate_by_default(self):
        bus=SharedActionBus(object(),object())
        bus.register("demo.action",lambda payload,context: {"v":1})
        with self.assertRaisesRegex(ValueError,"already registered"):
            bus.register("demo.action",lambda payload,context: {"v":2})

    def test_shared_action_bus_replace_must_be_explicit(self):
        bus=SharedActionBus(object(),object())
        bus.register("demo.action",lambda payload,context: {"v":1})
        row=bus.register("demo.action",lambda payload,context: {"v":2},replace=True)
        self.assertEqual(row["name"],"demo.action")
        self.assertEqual(len(bus.list()),1)

    def test_project_action_registry_rejects_duplicate_by_default(self):
        registry=ActionRegistry()
        registry.register("KRISHNA","demo",lambda payload: {"v":1})
        with self.assertRaisesRegex(ValueError,"already registered"):
            registry.register("KRISHNA","demo",lambda payload: {"v":2})

    def test_project_action_registry_explicit_replace_is_allowed(self):
        registry=ActionRegistry()
        registry.register("KRISHNA","demo",lambda payload: {"v":1})
        registry.register("KRISHNA","demo",lambda payload: {"v":2},replace=True)
        out=registry.execute("KRISHNA","demo")
        self.assertEqual(out["result"]["v"],2)
        self.assertEqual(len(registry.list("KRISHNA")),1)

    def test_same_action_name_is_allowed_for_different_projects(self):
        registry=ActionRegistry()
        registry.register("KRISHNA","status",lambda payload: {"project":"KRISHNA"})
        registry.register("KUBER","status",lambda payload: {"project":"KUBER"})
        self.assertEqual(len(registry.list()),2)


if __name__=="__main__":
    unittest.main()
