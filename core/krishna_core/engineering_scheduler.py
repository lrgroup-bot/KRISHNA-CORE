from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable
import math

from .project_perfection import DeadlineHR, WorkItem


@dataclass(frozen=True)
class EngineeringTask:
    id: str
    role: str
    estimate_minutes: float
    depends_on: tuple[str, ...] = ()
    privacy: str = "local_only"
    mutable: bool = True
    parallelizable: bool = True
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EngineeringScheduler:
    """Dependency-aware engineering schedule over KRISHNA's existing HR/runtime.

    Code execution remains on an authorized execution host. Free cloud providers
    may supply reasoning/review only unless a future trusted compute-node adapter
    explicitly provides a repository/build environment.
    """

    def __init__(self, max_workers: int = 8):
        self.max_workers = max(1, min(int(max_workers), 32))
        self.hr = DeadlineHR()

    @staticmethod
    def _tasks(rows: Iterable[dict[str, Any]]) -> list[EngineeringTask]:
        out = []
        seen = set()
        for row in rows:
            task_id = str(row.get("id") or "").strip()
            if not task_id:
                raise ValueError("engineering task id is required")
            if task_id in seen:
                raise ValueError("duplicate engineering task id: " + task_id)
            seen.add(task_id)
            estimate = float(row.get("estimate_minutes") or 1)
            if estimate <= 0:
                raise ValueError("estimate_minutes must be positive")
            out.append(EngineeringTask(
                task_id,
                str(row.get("role") or "engineering").strip() or "engineering",
                estimate,
                tuple(str(x).strip() for x in row.get("depends_on") or [] if str(x).strip()),
                str(row.get("privacy") or "local_only").strip().lower(),
                bool(row.get("mutable", True)),
                bool(row.get("parallelizable", True)),
                str(row.get("description") or "").strip(),
            ))
        if not out:
            raise ValueError("at least one engineering task is required")
        known = {x.id for x in out}
        for task in out:
            missing = [x for x in task.depends_on if x not in known]
            if missing:
                raise ValueError(f"task {task.id} depends on unknown tasks: {','.join(missing)}")
            if task.id in task.depends_on:
                raise ValueError("task cannot depend on itself: " + task.id)
        return out

    @staticmethod
    def _waves(tasks: list[EngineeringTask]) -> list[list[EngineeringTask]]:
        by_id = {x.id: x for x in tasks}
        remaining = set(by_id)
        completed = set()
        waves = []
        while remaining:
            ready = sorted(
                (by_id[x] for x in remaining if set(by_id[x].depends_on).issubset(completed)),
                key=lambda t: (t.role, t.id),
            )
            if not ready:
                cycle = ",".join(sorted(remaining))
                raise ValueError("engineering dependency graph contains a cycle: " + cycle)
            waves.append(ready)
            completed.update(x.id for x in ready)
            remaining.difference_update(x.id for x in ready)
        return waves

    @classmethod
    def _critical_path(cls, tasks: list[EngineeringTask]) -> float:
        waves = cls._waves(tasks)
        by_id = {x.id: x for x in tasks}
        finish: dict[str, float] = {}
        for wave in waves:
            for task in wave:
                start = max((finish[x] for x in task.depends_on), default=0.0)
                finish[task.id] = start + task.estimate_minutes
        return max(finish.values(), default=0.0)

    @staticmethod
    def _reasoning_route(task: EngineeringTask, free_cloud_available: bool) -> dict[str, Any]:
        local_only = task.privacy in {"local_only", "restricted", "secret", "private"}
        if local_only or not free_cloud_available:
            return {
                "reasoning": "local_ollama",
                "cloud_allowed": False,
                "cloud_scope": "none",
            }
        return {
            "reasoning": "local_first_then_verified_free_cloud",
            "cloud_allowed": True,
            "cloud_scope": "reasoning/review only; filesystem, Git, build and tests remain on the authorized execution host",
        }

    def plan(
        self, rows: Iterable[dict[str, Any]], *, deadline_minutes: float,
        local_slots: int = 1, free_cloud_available: bool = False,
        execution_host: str = "local_pc",
    ) -> dict[str, Any]:
        tasks = self._tasks(rows)
        local_slots = max(1, min(int(local_slots), self.max_workers))
        work = [
            WorkItem(x.id, x.role, x.estimate_minutes, parallelizable=x.parallelizable)
            for x in tasks
        ]
        team = self.hr.plan(work, float(deadline_minutes), self.max_workers)
        waves = self._waves(tasks)
        rendered = []
        for wave_index, wave in enumerate(waves, 1):
            batches = []
            for offset in range(0, len(wave), local_slots):
                batch = []
                for task in wave[offset:offset + local_slots]:
                    route = self._reasoning_route(task, free_cloud_available)
                    batch.append({
                        **task.as_dict(),
                        "execution_host": execution_host,
                        "reasoning_route": route,
                        "worktree_required": bool(task.mutable),
                    })
                batches.append(batch)
            rendered.append({"wave": wave_index, "parallel_ready": len(wave), "batches": batches})
        total = sum(x.estimate_minutes for x in tasks)
        critical = self._critical_path(tasks)
        available_parallelism = max((len(x) for x in waves), default=1)
        return {
            "tasks": [x.as_dict() for x in tasks],
            "deadline_minutes": float(deadline_minutes),
            "hr": asdict(team),
            "critical_path_minutes": critical,
            "total_work_minutes": total,
            "dependency_waves": rendered,
            "max_graph_parallelism": available_parallelism,
            "local_execution_slots": local_slots,
            "recommended_workers": team.recommended_workers,
            "deadline_risk": bool(team.resource_limited or critical > float(deadline_minutes)),
            "execution_truth": {
                "code_execution_host": execution_host,
                "free_cloud_is_compute_node": False,
                "free_cloud_role": "model reasoning/review only unless a separately trusted compute-node adapter is configured",
                "filesystem_build_tests": "execution_host",
            },
        }

    def status(self) -> dict[str, Any]:
        return {
            "component": "KRISHNA Engineering Scheduler",
            "dependency_aware": True,
            "deadline_hr": True,
            "max_workers": self.max_workers,
            "worktree_per_mutating_worker": True,
            "free_cloud_truth_boundary": "reasoning/review, not a repository machine",
        }
