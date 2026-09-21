from __future__ import annotations
from dataclasses import asdict,dataclass


@dataclass(frozen=True)
class AgentManifest:
    agent_id:str
    role:str
    permissions:tuple[str,...]
    actions:tuple[str,...]
    enabled:bool=True
    def as_dict(self):
        row=asdict(self);row["permissions"]=list(self.permissions);row["actions"]=list(self.actions);return row


class AgentRuntime:
    """Capability-bounded KRISHNA agent dispatcher.

    Agents never call runtime internals directly; every side effect is a Shared
    Action Bus action using the manifest's explicit permission set.
    """
    def __init__(self,action_bus):
        self.action_bus=action_bus
        self._agents={}

    def register(self,agent_id,role,permissions=(),actions=(),enabled=True):
        item=AgentManifest(
            str(agent_id),str(role),tuple(str(x) for x in permissions),
            tuple(str(x) for x in actions),bool(enabled),
        )
        self._agents[item.agent_id]=item
        return item.as_dict()

    @staticmethod
    def _allowed(item,action):
        for pattern in item.actions:
            if pattern=="*" or pattern==action:return True
            if pattern.endswith(".*") and action.startswith(pattern[:-1]):return True
        return False

    def dispatch(self,agent_id,action,payload=None,*,project="KRISHNA",approved=False,idempotency_key=None):
        item=self._agents.get(str(agent_id))
        if not item:raise KeyError(f"agent not registered: {agent_id}")
        if not item.enabled:raise PermissionError(f"agent disabled: {agent_id}")
        if not self._allowed(item,str(action)):
            raise PermissionError(f"agent action not allowed: {agent_id}:{action}")
        return self.action_bus.dispatch(
            action,payload,project=project,source="agent",actor=item.agent_id,
            approved=approved,permissions=item.permissions,idempotency_key=idempotency_key,
        )

    def list(self):
        return [x.as_dict() for x in sorted(self._agents.values(),key=lambda x:x.agent_id)]

    def status(self):
        return {
            "owner":"KRISHNA Agent Runtime",
            "agents":self.list(),"count":len(self._agents),
            "authority":"Shared Action Bus",
        }
