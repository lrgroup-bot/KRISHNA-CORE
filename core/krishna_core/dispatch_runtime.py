from __future__ import annotations


class DispatchRuntime:
    """One routing surface for action, agent and durable-job dispatch."""

    TARGETS={"action","agent","job"}

    def __init__(self,action_bus,agent_runtime,jobs):
        self.action_bus=action_bus;self.agents=agent_runtime;self.jobs=jobs;self.control_plane=None

    def bind_sudarshan(self,control_plane):
        self.control_plane=control_plane
        return self.status()

    def dispatch(self,target,action,payload=None,*,project="KRISHNA",actor="owner",
                 agent_id=None,permissions=(),approved=False,idempotency_key=None):
        target=str(target or "action").strip().lower()
        if target not in self.TARGETS:raise ValueError(f"unsupported dispatch target: {target}")
        if target=="action":
            if self.control_plane:
                return self.control_plane.action(
                    action,payload,project=project,source="pc",actor=actor,
                    permissions=permissions,approved=approved,idempotency_key=idempotency_key,
                )
            return self.action_bus.dispatch(
                action,payload,project=project,source="pc",actor=actor,
                permissions=permissions,approved=approved,idempotency_key=idempotency_key,
            )
        if target=="agent":
            if not agent_id:raise ValueError("agent_id is required for agent dispatch")
            return self.agents.dispatch(
                agent_id,action,payload,project=project,approved=approved,
                idempotency_key=idempotency_key,
            )
        if self.control_plane:
            return self.control_plane.job(
                action,payload,project=project,actor=actor,permissions=permissions,
                approved=approved,idempotency_key=idempotency_key,
            )
        return self.jobs.submit(
            action,payload,project=project,actor=actor,permissions=permissions,
            approved=approved,idempotency_key=idempotency_key,
        )

    def status(self):
        return {
            "owner":"KRISHNA Dispatch Runtime",
            "targets":sorted(self.TARGETS),
            "authority":"Sudarshan Control Plane" if self.control_plane else "Shared Action Bus",
        }
