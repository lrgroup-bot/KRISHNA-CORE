import unittest

from krishna_core.engineering_hooks import EngineeringHooks


class EngineeringHooksTests(unittest.TestCase):
    def test_hook_failures_are_evidence_not_permission_escalation(self):
        h = EngineeringHooks()
        h.register("before_test", lambda payload: {"seen": payload["project"]})
        h.register("before_test", lambda payload: (_ for _ in ()).throw(RuntimeError("boom")))
        out = h.emit("before_test", {"project": "demo"})
        self.assertEqual(out["handlers"], 2)
        self.assertTrue(out["results"][0]["ok"])
        self.assertFalse(out["results"][1]["ok"])
        self.assertEqual(h.status()["permissions_granted"], False)


if __name__ == "__main__":
    unittest.main()
