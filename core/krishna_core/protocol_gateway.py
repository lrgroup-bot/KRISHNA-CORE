from __future__ import annotations


class AgentProtocolGateway:
    """MCP/A2A adapter boundary over KRISHNA's Shared Action Bus.

    This is the internal protocol contract, not a public unauthenticated network
    server. Transport adapters must authenticate first, then call these methods.
    """
    def __init__(self,action_bus,agent_runtime):
        self.action_bus=action_bus
        self.agent_runtime=agent_runtime
        self.control_plane=None

    def bind_sudarshan(self,control_plane):
        self.control_plane=control_plane
        return self.status()

    def mcp_catalog(self):
        return {
            "tools":[{
                "name":x["name"],
                "description":x.get("description") or x["name"],
                "permissions":x.get("permissions") or [],
                "mutating":bool(x.get("mutating")),
                "requires_approval":bool(x.get("requires_approval")),
            } for x in self.action_bus.list()],
            "authority":"KRISHNA Shared Action Bus",
        }

    def mcp_call(self,tool_name,args=None,*,principal="mcp-client",project="KRISHNA",
                 permissions=(),approved=False,request_id=None):
        if self.control_plane:
            return self.control_plane.action(
                tool_name,args or {},project=project,source="mcp",actor=principal,
                permissions=permissions,approved=approved,idempotency_key=request_id,
            )
        return self.action_bus.dispatch(
            tool_name,args or {},project=project,source="mcp",actor=principal,
            permissions=permissions,approved=approved,idempotency_key=request_id,
        )

    def a2a_dispatch(self,message):
        msg=dict(message or {})
        action=str(msg.get("action") or "").strip()
        if not action:raise ValueError("A2A action is required")
        agent_id=str(msg.get("agent_id") or "").strip()
        if agent_id:
            return self.agent_runtime.dispatch(
                agent_id,action,msg.get("payload") or {},
                project=str(msg.get("project") or "KRISHNA"),
                approved=bool(msg.get("approved",False)),
                idempotency_key=str(msg.get("request_id") or "").strip() or None,
            )
        if self.control_plane:
            return self.control_plane.action(
                action,msg.get("payload") or {},project=str(msg.get("project") or "KRISHNA"),
                source="a2a",actor=str(msg.get("principal") or "a2a-peer"),
                permissions=msg.get("permissions") or [],approved=bool(msg.get("approved",False)),
                idempotency_key=str(msg.get("request_id") or "").strip() or None,
            )
        return self.action_bus.dispatch(
            action,msg.get("payload") or {},project=str(msg.get("project") or "KRISHNA"),
            source="a2a",actor=str(msg.get("principal") or "a2a-peer"),
            permissions=msg.get("permissions") or [],approved=bool(msg.get("approved",False)),
            idempotency_key=str(msg.get("request_id") or "").strip() or None,
        )

    def status(self):
        return {
            "owner":"KRISHNA Agent Protocol Gateway",
            "mcp":"Sudarshan-gated action-tool adapter boundary",
            "a2a":"agent/action envelope adapter boundary",
            "network_exposure":"none by default",
        }
