from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
import shutil
import subprocess
import uuid


def _safe(value: str, limit: int = 48) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    if not text:
        raise ValueError("safe identifier is required")
    return text[:limit]


class GitWorktreeManager:
    """Real Git worktree isolation for parallel KRISHNA coding workers."""

    def __init__(self, repository_root: str | Path, worktree_root: str | Path):
        self.repository_root = Path(repository_root).resolve()
        self.worktree_root = Path(worktree_root).resolve()
        if self._within(self.worktree_root, self.repository_root):
            raise ValueError("worktree root must not be inside the source repository")
        self.worktree_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def _run(self, args: list[str], timeout: int = 120) -> str:
        if not shutil.which("git"):
            raise RuntimeError("git executable is unavailable")
        proc = subprocess.run(
            ["git", "-C", str(self.repository_root), *args],
            capture_output=True, text=True, timeout=timeout, shell=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or f"exit={proc.returncode}").strip()
            raise RuntimeError("git worktree operation failed: " + detail[:4000])
        return (proc.stdout or "").strip()

    def preflight(self) -> dict[str, Any]:
        if not self.repository_root.is_dir():
            return {"ready": False, "reason": "repository_missing"}
        if not (self.repository_root / ".git").exists():
            try:
                top = self._run(["rev-parse", "--show-toplevel"], 30)
            except RuntimeError as exc:
                return {"ready": False, "reason": str(exc)}
        else:
            top = self._run(["rev-parse", "--show-toplevel"], 30)
        return {
            "ready": Path(top).resolve() == self.repository_root,
            "repository_root": str(self.repository_root),
            "worktree_root": str(self.worktree_root),
            "git": shutil.which("git"),
        }

    def create(
        self, project: str, worker_id: str, *, base_ref: str = "HEAD",
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        check = self.preflight()
        if not check.get("ready"):
            raise RuntimeError("Git worktree preflight failed: " + str(check.get("reason") or "wrong repository root"))
        project_safe = _safe(project)
        worker_safe = _safe(worker_id)
        token = _safe(mission_id, 16) if mission_id else uuid.uuid4().hex[:10]
        branch = f"krishna/{project_safe}/{worker_safe}-{token}"
        path = (self.worktree_root / project_safe / f"{worker_safe}-{token}").resolve()
        if not self._within(path, self.worktree_root):
            raise RuntimeError("worktree path escaped configured worktree root")
        if path.exists():
            raise FileExistsError(str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        self._run(["worktree", "add", "-b", branch, str(path), str(base_ref)], 180)
        return {
            "project": project,
            "worker_id": worker_id,
            "mission_id": mission_id,
            "branch": branch,
            "path": str(path),
            "base_ref": str(base_ref),
            "isolated": True,
            "execution_authority": "KRISHNA/Sudarshan",
        }

    def list(self) -> list[dict[str, Any]]:
        raw = self._run(["worktree", "list", "--porcelain"], 30)
        rows = []
        current: dict[str, Any] = {}
        for line in raw.splitlines() + [""]:
            if not line.strip():
                if current:
                    rows.append(current)
                    current = {}
                continue
            key, _, value = line.partition(" ")
            if key == "worktree":
                current["path"] = value
            elif key == "HEAD":
                current["head"] = value
            elif key == "branch":
                current["branch"] = value.removeprefix("refs/heads/")
            else:
                current[key] = value or True
        return rows

    def remove(self, path: str | Path, *, force: bool = False, delete_branch: bool = False) -> dict[str, Any]:
        target = Path(path).resolve()
        if not self._within(target, self.worktree_root):
            raise PermissionError("only KRISHNA-managed worktrees may be removed")
        rows = self.list()
        row = next((x for x in rows if Path(str(x.get("path") or "")).resolve() == target), None)
        if row is None:
            raise KeyError(str(target))
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(target))
        self._run(args, 120)
        branch = str(row.get("branch") or "")
        deleted_branch = False
        if delete_branch and branch.startswith("krishna/"):
            self._run(["branch", "-D", branch], 60)
            deleted_branch = True
        self._run(["worktree", "prune"], 30)
        return {"removed": True, "path": str(target), "branch": branch or None, "branch_deleted": deleted_branch}

    def status(self) -> dict[str, Any]:
        preflight = self.preflight()
        return {
            "component": "KRISHNA Git Worktree Manager",
            "preflight": preflight,
            "managed_worktrees": self.list() if preflight.get("ready") else [],
            "policy": "one isolated Git worktree/branch per mutating coding worker; live source is not a worker workspace",
        }
