from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import json
import re


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    if not out:
        raise ValueError("project is required")
    return out[:96]


class EngineeringSwarmManager:
    """Create durable child missions + isolated worktrees from an HR schedule.

    This manager staffs work; it does not bypass AgentRuntime, Shared Actions,
    verification, promotion, or Sudarshan.
    """

    SCHEMA = "krishna.engineering-swarm.v1"

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, project: str) -> Path:
        return self.root / (_slug(project) + ".json")

    def _save(self, project: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._path(project)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        return payload

    @staticmethod
    def _allocation(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
        out = {}
        for wave in plan.get("dependency_waves") or []:
            for batch_index, batch in enumerate(wave.get("batches") or [], 1):
                for row in batch:
                    out[str(row.get("id"))] = {
                        "wave": int(wave.get("wave") or 0),
                        "batch": batch_index,
                        "execution_host": row.get("execution_host"),
                        "reasoning_route": row.get("reasoning_route") or {},
                        "worktree_required": bool(row.get("worktree_required")),
                    }
        return out

    def staff(
        self, project: str, plan: dict[str, Any], *, parent_mission_id: str,
        mission_engine, worktree_manager, base_ref: str = "HEAD",
    ) -> dict[str, Any]:
        project = str(project or "").strip()
        parent_mission_id = str(parent_mission_id or "").strip()
        if not project or not parent_mission_id:
            raise ValueError("project and parent_mission_id are required")
        existing = self.status(project)
        if existing and existing.get("parent_mission_id") == parent_mission_id and existing.get("status") == "STAFFED":
            return existing
        allocations = self._allocation(plan)
        created_worktrees = []
        child_missions = []
        workers = []
        try:
            for task in plan.get("tasks") or []:
                task_id = str(task.get("id") or "").strip()
                role = str(task.get("role") or "engineering").strip() or "engineering"
                if not task_id:
                    raise ValueError("planned task missing id")
                allocation = allocations.get(task_id) or {}
                worktree = None
                if bool(task.get("mutable", True)):
                    worktree = worktree_manager.create(
                        project, task_id, base_ref=base_ref,
                        mission_id=(parent_mission_id[:8] + "-" + task_id)[:32],
                    )
                    created_worktrees.append(worktree)
                metadata = {
                    "engineering_swarm": True,
                    "task_id": task_id,
                    "role": role,
                    "depends_on": list(task.get("depends_on") or []),
                    "wave": allocation.get("wave"),
                    "batch": allocation.get("batch"),
                    "reasoning_route": allocation.get("reasoning_route") or {},
                    "worktree": worktree,
                }
                child = mission_engine.create(
                    str(task.get("description") or f"{role}: {task_id}"),
                    project_id=project,
                    parent_mission_id=parent_mission_id,
                    assigned_agents=[role, "mrityunjay"],
                    required_tools=["git-worktree", "development.verify", "project-perfection"],
                    permission_profile="engineering_worker",
                    resource_budget={"max_subagents": 1},
                    metadata=metadata,
                )
                child_missions.append(child)
                workers.append({
                    "worker_id": f"{role}:{task_id}",
                    "task_id": task_id,
                    "role": role,
                    "mission_id": child["mission_id"],
                    "depends_on": list(task.get("depends_on") or []),
                    "wave": allocation.get("wave"),
                    "batch": allocation.get("batch"),
                    "execution_host": allocation.get("execution_host"),
                    "reasoning_route": allocation.get("reasoning_route") or {},
                    "worktree": worktree,
                    "status": "QUEUED",
                })
        except Exception:
            for child in reversed(child_missions):
                try:
                    mission_engine.transition(child["mission_id"], "CANCELLED", error="swarm staffing rolled back")
                except Exception:
                    pass
            for worktree in reversed(created_worktrees):
                try:
                    worktree_manager.remove(worktree["path"], force=True, delete_branch=True)
                except Exception:
                    pass
            raise
        payload = {
            "schema": self.SCHEMA,
            "project": project,
            "parent_mission_id": parent_mission_id,
            "status": "STAFFED",
            "created_at": _now(),
            "workers": workers,
            "recommended_workers": plan.get("recommended_workers"),
            "local_execution_slots": plan.get("local_execution_slots"),
            "deadline_risk": bool(plan.get("deadline_risk")),
            "policy": {
                "hr_defines_staffing": True,
                "one_mutating_task_one_worktree": True,
                "live_source_worker_write": False,
                "promotion_authority": "Sudarshan/Project Perfection",
            },
        }
        return self._save(project, payload)

    def status(self, project: str) -> dict[str, Any] | None:
        path = self._path(project)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"engineering swarm state is unreadable: {type(exc).__name__}") from exc
        if not isinstance(value, dict):
            raise RuntimeError("engineering swarm state must be an object")
        return value
