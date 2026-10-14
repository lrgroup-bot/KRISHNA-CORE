"""Read-only bridge to KRISHNA's authoritative durable task ledger.

A trusted caller must supply an authenticated principal. This module never
constructs a principal from HTTP input and cannot submit or mutate jobs.
"""
from .identity import can_access


class DurableTaskReader:
    def __init__(self, ledger):
        if not callable(getattr(ledger, "get", None)) or not callable(getattr(ledger, "list_tasks", None)):
            raise TypeError("A KRISHNA TaskLedger-compatible instance is required")
        self._ledger = ledger

    def get(self, principal, project, task_id):
        if not can_access(principal, project, "read"):
            raise PermissionError("Project task access denied")
        row = self._ledger.get(task_id)
        if row is None or row.get("project") != project:
            return None
        return row

    def list(self, principal, project, limit=100):
        if not can_access(principal, project, "read"):
            raise PermissionError("Project task access denied")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("Invalid task limit")
        return [row for row in self._ledger.list_tasks(project, limit) if row.get("project") == project]
