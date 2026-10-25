"""Read-only connection LEDs require an authenticated current Core heartbeat and
an acknowledged BRAHMAGYAN collection candidate; Rishi mastery remains absent.
"""
import tempfile
import time
import unittest

from suryadev_liveops import atomic_json, connection_indicators


class CandidateConnectionTests(unittest.TestCase):
    def test_heartbeat_without_evidence_does_not_claim_brahmagyan(self):
        with tempfile.TemporaryDirectory() as root:
            atomic_json(root, "krishna-fleet-heartbeat-ack.json", {
                "schema": "suryadev.krishna-authenticated-heartbeat.v1",
                "authenticated_core_reply": True,
                "acknowledged_at": time.time(),
                "device_id": "suryadev-test"})
            connections = connection_indicators(root)
            self.assertTrue(connections["krishna"]["connected"])
            self.assertFalse(connections["brahmagyan"]["connected"])
            self.assertFalse(connections["rishi"]["connected"])

    def test_candidate_ack_distinct_from_verified_knowledge(self):
        with tempfile.TemporaryDirectory() as root:
            atomic_json(root, "krishna-fleet-heartbeat-ack.json", {
                "schema": "suryadev.krishna-authenticated-heartbeat.v1",
                "authenticated_core_reply": True,
                "acknowledged_at": time.time(),
                "device_id": "suryadev-test"})
            atomic_json(root, "suryadev-fleet-runtime.json", {
                "schema": "suryadev.fleet-node.v1",
                "receipts": {
                    "fleet-1": {
                        "device_id": "suryadev-test",
                        "outcome": "collected",
                        "core_acknowledged": True,
                        "brahmagyan_candidate_recorded": True,
                        "brahmagyan_accepted": False,
                        "rishi_exam_verified": False}}})
            result = connection_indicators(root)
            self.assertEqual(result["brahmagyan"]["state"],
                             "candidate_inbox_acknowledged")
            self.assertEqual(result["brahmagyan"]["candidate_receipts"], 1)
            self.assertFalse(result["brahmagyan"]["knowledge_accepted"])
            self.assertFalse(result["rishi"]["connected"])
            atomic_json(root, "krishna-fleet-heartbeat-ack.json", {
                "schema": "suryadev.krishna-authenticated-heartbeat.v1",
                "authenticated_core_reply": True,
                "acknowledged_at": time.time() - 600})
            self.assertFalse(connection_indicators(root)["brahmagyan"]["connected"])

    def test_forged_unacknowledged_candidate_is_not_connected(self):
        with tempfile.TemporaryDirectory() as root:
            atomic_json(root, "krishna-fleet-heartbeat-ack.json", {
                "schema": "suryadev.krishna-authenticated-heartbeat.v1",
                "authenticated_core_reply": True,
                "acknowledged_at": time.time()})
            atomic_json(root, "suryadev-fleet-runtime.json", {
                "schema": "suryadev.fleet-node.v1",
                "receipts": {"fleet-x": {
                    "outcome": "collected",
                    "core_acknowledged": False,
                    "brahmagyan_candidate_recorded": True}}})
            self.assertFalse(connection_indicators(root)["brahmagyan"]["connected"])


if __name__ == "__main__":
    unittest.main()
