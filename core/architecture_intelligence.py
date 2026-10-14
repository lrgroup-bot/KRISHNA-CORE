from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArchifyPolicy:
    """Fail-closed policy for KRISHNA's Archify adapter."""

    update_check_disabled: bool = True
    source_read_only: bool = True
    allow_repo_write: bool = False
    allow_merge: bool = False
    allow_deploy: bool = False

    def environment(self) -> dict[str, str]:
        return {"ARCHIFY_UPDATE_CHECK_DISABLED": "1"}

    def assert_safe_paths(self, repo_root: Path, output_dir: Path) -> None:
        repo = repo_root.resolve()
        out = output_dir.resolve()
        if out == repo:
            raise ValueError("Archify output directory cannot be repository root")
        protected = {repo / ".git", repo / "core", repo / "app"}
        if any(out == p or p in out.parents for p in protected):
            raise ValueError("Archify output directory is inside a protected source path")

    def assert_no_privileged_action(self, action: str) -> None:
        blocked = {"repo-write", "merge", "deploy", "spend", "approve"}
        if action.strip().lower() in blocked:
            raise PermissionError(f"Archify adapter cannot perform privileged action: {action}")


DEFAULT_ARCHIFY_POLICY = ArchifyPolicy()


def archify_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env.update(DEFAULT_ARCHIFY_POLICY.environment())
    return env
