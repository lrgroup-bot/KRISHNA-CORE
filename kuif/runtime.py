"""Opt-in KUIF runtime: authorized local inference, memory and audit.

The caller supplies an authenticated Principal; this module does not authenticate it.
No production entrypoint imports this module automatically.
"""
from dataclasses import dataclass
from .identity import Principal, can_access
from .audit import append_event
from .knowledge import KnowledgeStore
from .ollama import generate

@dataclass(frozen=True)
class RuntimeConfig:
    memory_path: str
    audit_path: str
    model: str = "qwen3.5:4b"

class Runtime:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.memory = KnowledgeStore(config.memory_path)

    def _check(self, principal: Principal, project: str, action: str) -> None:
        allowed = can_access(principal, project, action)
        append_event(self.config.audit_path, project=project,
                     actor=principal.subject or "anonymous", action=action, allowed=allowed)
        if not allowed:
            raise PermissionError("Project action denied")

    def search(self, principal: Principal, project: str, term: str):
        self._check(principal, project, "read")
        return self.memory.search(project, term)

    def analyze(self, principal: Principal, project: str, prompt: str) -> str:
        self._check(principal, project, "analyze")
        return generate(self.config.model, prompt)
