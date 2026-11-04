"""KUIF: conservative, dependency-free policy gate for cross-project operations."""
from dataclasses import dataclass
from typing import FrozenSet

@dataclass(frozen=True)
class Project:
    name: str
    allowed_actions: FrozenSet[str]

PROJECTS = {
    "krishna": Project("krishna", frozenset({"read", "analyze"})),
    "lr_group": Project("lr_group", frozenset({"read", "analyze"})),
    "lr_resources": Project("lr_resources", frozenset({"read", "analyze"})),
    "lr_commerce": Project("lr_commerce", frozenset({"read", "analyze"})),
    "lr_production": Project("lr_production", frozenset({"read", "analyze"})),
    "kidzoo": Project("kidzoo", frozenset({"read", "analyze"})),
    "kuber": Project("kuber", frozenset({"read", "analyze"})),
}

def authorize(project: str, action: str, *, approved: bool = False) -> bool:
    """Default deny. Explicit approval never bypasses the action allowlist."""
    entry = PROJECTS.get(project)
    return bool(entry and action in entry.allowed_actions)

def require_authorized(project: str, action: str) -> None:
    if not authorize(project, action):
        raise PermissionError(f"Action {action!r} denied for project {project!r}")
