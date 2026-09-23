from __future__ import annotations

"""Authenticated JSON-RPC adapter for KRISHNA's internal MCP boundary.

This module intentionally does not open a socket. A trusted local transport may
feed decoded JSON-RPC messages here after authentication. Every tool call still
enters AgentProtocolGateway -> Sudarshan/Shared Action Bus.
"""

from dataclasses import dataclass
import json


@dataclass(frozen=True)
class MCPPrincipal:
    principal: str
    project: str = "KRISHNA"
    permissions: tuple[str, ...] = ()
    approved: bool = False


class MCPJsonRpcAdapter:
    VERSION = "2025-06-18"

    def __init__(self, gateway):
        self.gateway = gateway

    @staticmethod
    def _error(message_id, code, message):
        return {"jsonrpc":"2.0","id":message_id,"error":{"code":int(code),"message":str(message)[:500]}}

    @staticmethod
    def _result(message_id, result):
        return {"jsonrpc":"2.0","id":message_id,"result":result}

    def handle(self, message, *, auth: MCPPrincipal | None):
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except Exception:
                return self._error(None, -32700, "parse error")
        if not isinstance(message, dict):
            return self._error(None, -32600, "invalid request")
        mid = message.get("id")
        method = str(message.get("method") or "")
        params = message.get("params") or {}
        if message.get("jsonrpc") != "2.0" or not method:
            return self._error(mid, -32600, "invalid request")

        if method == "initialize":
            return self._result(mid, {
                "protocolVersion": self.VERSION,
                "serverInfo": {"name":"KRISHNA MCP Action Gateway","version":"1"},
                "capabilities": {"tools":{"listChanged":False}},
                "authority": "KRISHNA/Sudarshan",
            })

        if auth is None:
            return self._error(mid, -32001, "authenticated local principal required")

        if method == "tools/list":
            catalog = self.gateway.mcp_catalog(
                permissions=auth.permissions,
                relevant_actions=params.get("relevant_actions"),
            )
            tools = []
            for row in catalog.get("tools") or []:
                tools.append({
                    "name": row["name"],
                    "description": row.get("description") or row["name"],
                    "inputSchema": {"type":"object","additionalProperties":True},
                    "_krishna": {
                        "permissions": row.get("permissions") or [],
                        "mutating": bool(row.get("mutating")),
                        "requires_approval": bool(row.get("requires_approval")),
                    },
                })
            return self._result(mid, {"tools":tools})

        if method == "tools/call":
            name = str(params.get("name") or "").strip()
            if not name:
                return self._error(mid, -32602, "tool name is required")
            try:
                receipt = self.gateway.mcp_call(
                    name,
                    params.get("arguments") or {},
                    principal=auth.principal,
                    project=auth.project,
                    permissions=auth.permissions,
                    approved=auth.approved,
                    request_id=str(params.get("request_id") or "").strip() or None,
                )
            except KeyError:
                return self._error(mid, -32601, "tool not found")
            except PermissionError as exc:
                return self._error(mid, -32003, str(exc))
            except Exception as exc:
                return self._error(mid, -32000, f"{type(exc).__name__}: {exc}")
            return self._result(mid, {
                "content":[{"type":"text","text":json.dumps(receipt,ensure_ascii=False,default=str)}],
                "isError":False,
                "_krishna_receipt":receipt,
            })

        return self._error(mid, -32601, "method not found")

    def status(self):
        return {
            "component":"KRISHNA MCP JSON-RPC Adapter",
            "protocol_version":self.VERSION,
            "network_listener":False,
            "authentication_required":True,
            "execution_path":"JSON-RPC -> AgentProtocolGateway -> Sudarshan/Shared Action Bus",
            "ready":True,
        }
