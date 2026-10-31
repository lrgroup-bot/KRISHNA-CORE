"""Connection-first checks for the isolated R106 Core integration."""
import tempfile
import unittest

from krishna_core.remote_access import PrivateRemotePolicy
from krishna_core.suryadev import SuryadevAgent
from krishna_core.suryadev_plan_delivery import approved_plan


class ActiveConnectionTests(unittest.TestCase):
    def test_heartbeat_authentication_is_server_asserted_and_plan_waits(self):
        with tempfile.TemporaryDirectory() as root:
            agent = SuryadevAgent(root)
            payload = {"device_id": "suryadev-1", "worker_running": False,
                       "learning_state": "awaiting_approved_plan", "authenticated": True}
            agent.device_heartbeat(payload)
            with self.assertRaises(PermissionError):
                approved_plan(agent, "suryadev-1")
            agent.device_heartbeat(payload, authenticated=True)
            self.assertEqual(approved_plan(agent, "suryadev-1"), {
                "status": "awaiting_owner_approved_plan", "device_id": "suryadev-1"})

    def test_remote_policy_allows_only_the_protected_plan_route(self):
        policy = PrivateRemotePolicy()
        self.assertTrue(policy.mobile_route_allowed("/api/suryadev/device/heartbeat"))
        self.assertTrue(policy.mobile_route_allowed("/api/suryadev/device/status"))
        self.assertTrue(policy.mobile_route_allowed("/api/suryadev/learning-plan/request"))
        self.assertFalse(policy.mobile_route_allowed("/api/mobile/pair/approve"))


if __name__ == "__main__":
    unittest.main()
