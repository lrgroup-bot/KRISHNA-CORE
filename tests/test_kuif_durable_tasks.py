"""Regression tests for project-scoped durable task reads."""
import unittest
from kuif.durable_tasks import DurableTaskReader
from kuif.identity import Principal


class Ledger:
    def get(self, task_id):
        return {"task_id": task_id, "project": "kuber"}

    def list_tasks(self, project, limit):
        return [{"task_id": "one", "project": "kuber"}]


class DurableTaskTests(unittest.TestCase):
    def test_project_isolation(self):
        reader = DurableTaskReader(Ledger())
        principal = Principal("tester", frozenset({"krishna"}), frozenset({"read"}))
        self.assertIsNone(reader.get(principal, "krishna", "one"))
        self.assertEqual(reader.list(principal, "krishna"), [])

    def test_denied_other_project(self):
        reader = DurableTaskReader(Ledger())
        principal = Principal("tester", frozenset({"krishna"}), frozenset({"read"}))
        with self.assertRaises(PermissionError):
            reader.list(principal, "kuber")


if __name__ == "__main__":
    unittest.main()
