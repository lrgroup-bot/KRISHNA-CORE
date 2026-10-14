"""Explicit principal-to-project authorization, deny by default."""
from dataclasses import dataclass
from typing import FrozenSet
from .policy import authorize

@dataclass(frozen=True)
class Principal:
    subject: str
    projects: FrozenSet[str]
    actions: FrozenSet[str]

def can_access(principal: Principal, project: str, action: str) -> bool:
    return bool(principal.subject and project in principal.projects
                and action in principal.actions and authorize(project, action))
