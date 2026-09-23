import unittest

from krishna_core.mcp_transport import MCPJsonRpcAdapter, MCPPrincipal


class FakeGateway:
    def mcp_catalog(self,permissions=(),relevant_actions=None):
        return {"tools":[
            {"name":"project.read","description":"Read project","permissions":["projects.read"],"mutating":False,"requires_approval":False},
            {"name":"project.fix","description":"Fix project","permissions":["projects.write"],"mutating":True,"requires_approval":True},
        ]}
    def mcp_call(self,name,args=None,**kwargs):
        if name=="missing":raise KeyError(name)
        if name=="project.fix" and not kwargs.get("approved"):
            raise PermissionError("approval required")
        return {"status":"completed","action":name,"result":args or {},"actor":kwargs.get("principal")}


class MCPTransportTests(unittest.TestCase):
    def test_initialize_does_not_require_authentication(self):
        out=MCPJsonRpcAdapter(FakeGateway()).handle(
            {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}},auth=None
        )
        self.assertEqual(out["result"]["serverInfo"]["name"],"KRISHNA MCP Action Gateway")

    def test_tools_require_authenticated_principal(self):
        adapter=MCPJsonRpcAdapter(FakeGateway())
        denied=adapter.handle({"jsonrpc":"2.0","id":2,"method":"tools/list"},auth=None)
        self.assertEqual(denied["error"]["code"],-32001)
        allowed=adapter.handle(
            {"jsonrpc":"2.0","id":3,"method":"tools/list"},
            auth=MCPPrincipal("local-owner",permissions=("projects.read",))
        )
        self.assertEqual(len(allowed["result"]["tools"]),2)

    def test_mutating_call_keeps_approval_gate(self):
        adapter=MCPJsonRpcAdapter(FakeGateway())
        out=adapter.handle(
            {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"project.fix","arguments":{"x":1}}},
            auth=MCPPrincipal("agent",permissions=("projects.write",),approved=False)
        )
        self.assertEqual(out["error"]["code"],-32003)


if __name__=="__main__":
    unittest.main()
