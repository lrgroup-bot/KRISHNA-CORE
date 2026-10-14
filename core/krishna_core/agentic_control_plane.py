from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import re
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str, limit: int = 96) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    if not text:
        raise ValueError("identifier is required")
    return text[:limit]


def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(f"{k} {_flatten(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten(v) for v in value)
    return str(value)


@dataclass(frozen=True)
class ProviderContract:
    name: str
    optional: bool = True
    authority: str = "worker"
    may_be_required_for_runtime: bool = False
    billable_dependency_allowed: bool = False
    merge_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgenticPreToolPolicy:
    """Provider-neutral guard for coding-agent tool calls.

    This is intentionally narrower than KRISHNA's runtime Policy Kernel. It guards
    coding-agent sessions and does not create a second runtime authority.
    """

    DEFAULT_PROTECTED_BRANCHES = (
        "fix/krishna-ui-runtime-verification",
        "main",
        "master",
    )
    _DESTRUCTIVE = (
        r"\bgit\s+push\b[^\n]*(?:--force|-f\b)",
        r"\bgit\s+reset\s+--hard\b",
        r"\bgit\s+clean\b[^\n]*-[^\n]*f",
        r"\brm\s+-rf\b",
        r"\bremove-item\b[^\n]*-recurse[^\n]*-force",
        r"\bformat\s+[a-z]:",
        r"\bdel\s+/[sq]\b",
    )
    _SECRET_TARGETS = (
        ".env",
        "credentials",
        "credential",
        "private_key",
        "id_rsa",
        "secrets.",
        "secret.",
    )

    def __init__(self, protected_branches: Iterable[str] | None = None):
        self.protected_branches = tuple(
            str(x).strip() for x in (protected_branches or self.DEFAULT_PROTECTED_BRANCHES)
            if str(x).strip()
        )

    @staticmethod
    def _decision(allowed: bool, reason: str) -> dict[str, Any]:
        return {
            "permissionDecision": "allow" if allowed else "deny",
            "permissionDecisionReason": str(reason),
        }

    def evaluate(self, *, tool_name: str, tool_args: Any, cwd: str = "") -> dict[str, Any]:
        tool = str(tool_name or "").strip().lower()
        text = _flatten(tool_args).lower()

        if tool in {"bash", "powershell", "shell", "terminal"}:
            for pattern in self._DESTRUCTIVE:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    return self._decision(False, "KRISHNA agent policy blocks destructive or forceful repository/system commands")
            if "git push" in text:
                for branch in self.protected_branches:
                    if branch.lower() in text:
                        return self._decision(False, f"KRISHNA agent policy blocks direct push to protected branch {branch}")
            if re.search(r"\bgh\s+pr\s+merge\b", text):
                return self._decision(False, "KRISHNA agent policy keeps pull-request merge authority outside coding agents")

        if tool in {"create", "edit", "write", "apply_patch", "str_replace_editor"}:
            if any(token in text for token in self._SECRET_TARGETS):
                return self._decision(False, "KRISHNA agent policy blocks direct creation/editing of secret or credential material")

        if "purchase" in text and any(x in text for x in ("api credit", "subscription", "billing", "payment")):
            return self._decision(False, "KRISHNA zero-spend policy blocks billable dependency activation")

        return self._decision(True, "allowed by KRISHNA additive coding-agent guard")


class MissionArtifactStore:
    """Durable, reviewable evidence packets for agentic engineering missions."""

    SAFE_NAMES = {
        "PLAN",
        "STAFFING",
        "CHANGES",
        "TEST_RESULTS",
        "SECURITY",
        "UI_PROOF",
        "REVIEW",
        "MRITYUNJAY",
        "FINAL_RECEIPT",
    }

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def mission_dir(self, project: str, mission_id: str) -> Path:
        path = (self.root / _slug(project) / _slug(mission_id)).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise RuntimeError("mission artifact path escaped configured root") from exc
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, project: str, mission_id: str, name: str, payload: Any) -> dict[str, Any]:
        key = str(name or "").strip().upper()
        if key not in self.SAFE_NAMES:
            raise ValueError(f"unsupported artifact name: {name}")
        directory = self.mission_dir(project, mission_id)
        path = directory / f"{key}.json"
        body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(path)
        return {
            "name": key,
            "path": str(path),
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "bytes": len(body.encode("utf-8")),
        }

    def manifest(self, project: str, mission_id: str) -> dict[str, Any]:
        directory = self.mission_dir(project, mission_id)
        rows = []
        for path in sorted(directory.glob("*.json")):
            data = path.read_bytes()
            rows.append({
                "name": path.stem,
                "path": str(path),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            })
        return {
            "project": project,
            "mission_id": mission_id,
            "artifact_root": str(directory),
            "artifacts": rows,
        }


class AgenticEngineeringControlPlane:
    """Additive engineering coordination layer over existing KRISHNA primitives.

    Dependencies are injected so this module does not replace or modify existing
    scheduler, swarm, verifier, worktree, promotion, or runtime authorities.
    """

    VERSION = "krishna-agentic-control-plane-v1"

    def __init__(self, artifact_root: str | Path, *, scheduler=None, swarm=None, verifier=None):
        self.artifacts = MissionArtifactStore(artifact_root)
        self.scheduler = scheduler
        self.swarm = swarm
        self.verifier = verifier

    @staticmethod
    def provider_contract(name: str) -> dict[str, Any]:
        return ProviderContract(name=_slug(name, 48)).as_dict()

    def new_mission(self, project: str, goal: str, *, provider: str = "local", metadata: dict | None = None) -> dict[str, Any]:
        project = str(project or "").strip()
        goal = str(goal or "").strip()
        if not project or not goal:
            raise ValueError("project and goal are required")
        mission_id = "agentic-" + uuid.uuid4().hex[:16]
        mission = {
            "schema": "krishna.agentic-mission.v1",
            "mission_id": mission_id,
            "project": project,
            "goal": goal,
            "provider": self.provider_contract(provider),
            "status": "PLANNED",
            "created_at": _now(),
            "metadata": dict(metadata or {}),
            "authority": "KRISHNA",
            "rules": {
                "live_source_worker_write": False,
                "one_mutating_worker_one_worktree": True,
                "auto_merge": False,
                "external_provider_required": False,
                "billable_dependency_allowed": False,
            },
        }
        self.artifacts.write(project, mission_id, "PLAN", mission)
        return mission

    def plan_engineering(
        self,
        mission: dict[str, Any],
        tasks: Iterable[dict[str, Any]],
        *,
        deadline_minutes: float,
        local_slots: int = 1,
        free_cloud_available: bool = False,
        execution_host: str = "local_pc",
    ) -> dict[str, Any]:
        if self.scheduler is None:
            raise RuntimeError("engineering scheduler is not configured")
        plan = self.scheduler.plan(
            tasks,
            deadline_minutes=float(deadline_minutes),
            local_slots=int(local_slots),
            free_cloud_available=bool(free_cloud_available),
            execution_host=str(execution_host),
        )
        packet = {
            "mission_id": mission["mission_id"],
            "project": mission["project"],
            "created_at": _now(),
            "plan": plan,
            "authority": "existing KRISHNA EngineeringScheduler",
        }
        self.artifacts.write(mission["project"], mission["mission_id"], "PLAN", {**mission, "engineering": packet})
        return plan

    def staff(self, mission: dict[str, Any], plan: dict[str, Any], *, mission_engine, worktree_manager, base_ref: str = "HEAD") -> dict[str, Any]:
        if self.swarm is None:
            raise RuntimeError("engineering swarm is not configured")
        result = self.swarm.staff(
            mission["project"],
            plan,
            parent_mission_id=mission["mission_id"],
            mission_engine=mission_engine,
            worktree_manager=worktree_manager,
            base_ref=base_ref,
        )
        self.artifacts.write(mission["project"], mission["mission_id"], "STAFFING", result)
        return result

    def record(self, mission: dict[str, Any], name: str, payload: Any) -> dict[str, Any]:
        return self.artifacts.write(mission["project"], mission["mission_id"], name, payload)

    def independent_review(self, mission: dict[str, Any], *, checks: list[dict], evidence: list | None = None) -> dict[str, Any]:
        if self.verifier is None:
            raise RuntimeError("independent verifier is not configured")
        verdict = self.verifier.judge(checks, evidence=evidence or [])
        self.artifacts.write(mission["project"], mission["mission_id"], "REVIEW", verdict)
        return verdict

    def finalize(self, mission: dict[str, Any], *, required: Iterable[str] = ("TEST_RESULTS", "REVIEW")) -> dict[str, Any]:
        manifest = self.artifacts.manifest(mission["project"], mission["mission_id"])
        present = {str(x["name"]).upper() for x in manifest["artifacts"]}
        required_set = {str(x).upper() for x in required}
        missing = sorted(required_set - present)
        receipt = {
            "schema": "krishna.agentic-final-receipt.v1",
            "mission_id": mission["mission_id"],
            "project": mission["project"],
            "goal": mission["goal"],
            "completed_at": _now(),
            "ready_for_governed_promotion": not missing,
            "missing_required_artifacts": missing,
            "auto_merge": False,
            "promotion_authority": "KRISHNA/Sudarshan/owner policy",
            "manifest": manifest,
        }
        self.artifacts.write(mission["project"], mission["mission_id"], "FINAL_RECEIPT", receipt)
        return receipt

    def status(self) -> dict[str, Any]:
        return {
            "component": "KRISHNA Agentic Engineering Control Plane",
            "version": self.VERSION,
            "additive_only": True,
            "scheduler_bound": self.scheduler is not None,
            "swarm_bound": self.swarm is not None,
            "verifier_bound": self.verifier is not None,
            "artifact_root": str(self.artifacts.root),
            "external_agents": "optional workers only",
            "auto_merge": False,
            "live_source_worker_write": False,
        }


def build_default_agentic_control_plane(state_root: str | Path, *, max_workers: int = 8) -> AgenticEngineeringControlPlane:
    """Bind the new layer to existing KRISHNA scheduler/swarm/verifier classes."""

    from .critic_verifier import IndependentCriticVerifier
    from .engineering_scheduler import EngineeringScheduler
    from .engineering_swarm import EngineeringSwarmManager

    root = Path(state_root).resolve()
    return AgenticEngineeringControlPlane(
        root / "artifacts",
        scheduler=EngineeringScheduler(max_workers=max_workers),
        swarm=EngineeringSwarmManager(root / "swarm"),
        verifier=IndependentCriticVerifier(None, None),
    )
