from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[2]


def text(rel):
    return (ROOT/rel).read_text(encoding="utf-8")


def block(source,start,end=None):
    i=source.index(start)
    if end is None:
        return source[i:]
    j=source.find(end,i+len(start))
    return source[i:] if j < 0 else source[i:j]


class AuthorityTransportContractTests(unittest.TestCase):
    def test_agent_runtime_forwards_lease(self):
        src=text("core/krishna_core/agent_runtime.py")
        self.assertIn("authority_lease=None",src)
        self.assertGreaterEqual(src.count("authority_lease=authority_lease"),2)

    def test_dispatch_runtime_forwards_lease_to_all_targets(self):
        src=text("core/krishna_core/dispatch_runtime.py")
        self.assertIn("authority_lease=None",src)
        self.assertGreaterEqual(src.count("authority_lease=authority_lease"),4)

    def test_protocol_gateway_forwards_mcp_and_a2a_lease(self):
        src=text("core/krishna_core/protocol_gateway.py")
        self.assertIn("authority_lease=None",src)
        self.assertGreaterEqual(src.count("authority_lease=authority_lease"),2)
        a2a=block(src,"    def a2a_dispatch", "    def status")
        self.assertGreaterEqual(a2a.count('msg.get("authority_lease")'),3)

    def test_orchestrator_owner_wrappers_accept_lease(self):
        src=text("core/krishna_core/orchestrator.py")
        self.assertIn("def rollback_dispatched_action(self,action_id,source=\"pc\",actor=\"owner\",approved=False,authority_lease=None)",src)
        self.assertIn("def promote_candidate(self, token, approved=False, authority_lease=None)",src)
        self.assertIn("def run_managed_goal(self, project, goal, action_name=None, components=None, approved=False, amcc_signals=None, authority_lease=None)",src)

    def test_mrityunjay_autonomous_path_is_shadow_only_by_default(self):
        src=text("core/krishna_core/orchestrator.py")
        event=block(src,"    def _mrityunjay_heal_event", "    def dispatch_action")
        self.assertIn('"auto_apply":False',event)
        self.assertIn("approved=False",event)
        heal=block(src,"        def mrityunjay_heal_action", "        self.action_bus.register(")
        self.assertIn('payload.get("auto_apply",False)',heal)
        self.assertIn("scoped owner authority lease",heal)

    def test_server_decision_needs_explicit_partha_confirmation(self):
        src=text("core/krishna_core/server.py")
        decide=block(src,'        if post_path == "/api/authority/lease/decide":','        if post_path == "/api/authority/kill-switch/engage":')
        self.assertIn("PARTHA_APPROVE_LEASE",decide)

    def test_sensitive_http_routes_forward_authority_lease(self):
        src=text("core/krishna_core/server.py")
        routes=[
            "/api/mobile/testing/run",
            "/api/desktop/rpa/run",
            "/api/garudanetra/session/start",
            "/api/garudanetra/replay",
            "/api/narad/dead-letters/retry",
            "/api/narad/checkpoints/resume",
            "/api/narad/workflows/promote",
            "/api/narad/workflows/execute",
            "/api/plugins/enable",
            "/api/plugins/remove",
            "/api/plugins/execute",
            "/api/action-bus/rollback",
            "/api/protocols/mcp/call",
            "/api/gyan-bhandar/acl/grant",
            "/api/gyan-bhandar/acl/revoke",
            "/api/gyan-bhandar/replica/snapshot",
            "/api/gyan-bhandar/encrypted/store",
            "/api/work/promotion/apply",
        ]
        for route in routes:
            marker=f'        if post_path == "{route}":'
            self.assertIn(marker,src,route)
            section=block(src,marker,"\n        if post_path == ")
            self.assertIn('authority_lease',section,route)

    def test_visual_live_apply_requires_authority_lease(self):
        src=text("core/krishna_core/server.py")
        self.assertNotIn("orch.promote_candidate(token,approved=True)",src)
        self.assertIn('orch.promote_candidate(token,approved=bool(data.get("approved",False)),authority_lease=data.get("authority_lease"))',src)


if __name__ == "__main__":
    unittest.main()
