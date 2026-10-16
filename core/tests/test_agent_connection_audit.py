import unittest
from krishna_core.agent_runtime import AgentRuntime


class StubBus:
    def list(self):
        return [
            {"name": "lab.plan", "permissions": ["lab.plan"], "sources": ["agent"]},
            {"name": "lab.execute", "permissions": ["lab.execute"], "sources": ["pc"]},
            {"name": "lab.secret", "permissions": ["secrets.write"], "sources": ["agent"]},
        ]


class AgentConnectionAuditTests(unittest.TestCase):
    def test_audit_is_read_only_and_distinguishes_permissions_and_sources(self):
        runtime = AgentRuntime(StubBus())
        runtime.register("lab-bot", "laboratory", permissions=("lab.plan",),
                         actions=("lab.*", "missing.*"))
        report = runtime.audit_connections()
        self.assertEqual(report["registered_agents"], 1)
        row = report["agents"][0]
        self.assertEqual(row["matched_actions"], 3)
        self.assertEqual(row["permission_compatible_actions"], 1)
        self.assertEqual(row["missing_permissions"]["lab.secret"], ["secrets.write"])
        self.assertEqual(row["unmatched_patterns"], ["missing.*"])
        self.assertFalse(row["runtime_verified"])


if __name__ == "__main__":
    unittest.main()
