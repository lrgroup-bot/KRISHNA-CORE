"""Opt-in pinned Core mission client, failure isolation and replay tests."""
from pathlib import Path
import json
import ssl
import tempfile
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_mission_renewal import renewal_tick
from suryadev_krishna_mission import MissionRelay, load_config, STATE_FILE
from suryadev_liveops import operations_snapshot


class CoreMissionRelayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plan = self.root / "learning-plan.json"
        self.allowed_url = "https://docs.python.org/3/library/asyncio-task.html"
        self.plan.write_text(json.dumps({
            "approved_urls": [self.allowed_url], "approved_feeds": [],
            "allowed_source_hosts": ["docs.python.org"], "max_new_per_cycle": 10,
            "max_queued": 30}), encoding="utf-8")
        self.secret = self.root / "paired-device-secret.txt"
        self.secret.write_text("x"*64, encoding="ascii")
        self.cfg = self.root / "paired-core-mission.json"
        self.cfg.write_text(json.dumps({
            "schema": "suryadev.krishna-mission-connection.v1",
            "endpoint": "https://192.168.0.100:8766",
            "cert_sha256": "a"*64,
            "device_id": "suryadev-laptop",
            "token_file": str(self.secret),
        }), encoding="utf-8")
        self.lib = Library(self.root)
        self.clock = [1000.0]
        self.req = renewal_tick(self.lib, now=1000)

    def tearDown(self):
        self.lib.db.close()
        self.temp.cleanup()

    def offer(self, url=None, status="offered"):
        return {
            "status": status, "request_id": self.req["request"]["request_id"],
            "mission": {"id": "python-async", "duration_hours": 6,
                        "approved_urls": [url or self.allowed_url]},
        }

    def relay(self, transport):
        return MissionRelay(self.root, self.plan, self.cfg, transport=transport,
                            clock=lambda: self.clock[0])

    def test_valid_paired_six_hour_mission_queues_and_is_acknowledged(self):
        requests = []
        def fake_transport(config, path, payload):
            requests.append(path)
            return self.offer() if path.endswith("/request") else {
                "request_id": self.req["request"]["request_id"],
                "acknowledged": True}
        relay = self.relay(fake_transport)
        with patch("suryadev.validate_url", return_value=None):
            result = relay.tick(self.lib, self.req)
        self.assertTrue(result["acknowledged"])
        self.assertEqual(result["queued_urls"], 1)
        self.assertEqual(requests, ["/api/suryadev/mission/request",
                                     "/api/suryadev/mission/ack"])
        self.assertEqual(self.lib.stats()["queued"], 1)
        self.assertIsNone(relay.tick(self.lib, self.req))
        new_view = renewal_tick(self.lib, now=1001)
        self.assertTrue(new_view["delivered_to_krishna"])
        self.assertTrue(new_view["krishna_assignment_acknowledged"])
        self.assertFalse(new_view["brahmagyan_acknowledged"])
        self.assertTrue(operations_snapshot(self.lib.db, self.root)
                        ["mission_renewal"]["krishna_assignment_acknowledged"])

    def test_remote_unapproved_url_is_rejected_without_queue_mutation(self):
        def transport(config, path, payload):
            return self.offer(url="https://evil.example/hidden")
        result = self.relay(transport).tick(self.lib, self.req)
        self.assertEqual(result["state"], "retry_later")
        self.assertIn("not explicitly approved", result["last_error"])
        self.assertEqual(self.lib.stats().get("queued", 0), 0)
        self.assertFalse(renewal_tick(self.lib, now=1001)
                         ["krishna_assignment_acknowledged"])

    def test_ack_failure_keeps_durable_receipt_then_replays_only_ack(self):
        calls = []
        def transport(config, path, payload):
            calls.append(path)
            if path.endswith("/request"):
                return self.offer()
            if len(calls) == 2:
                raise OSError("transient Core disconnect")
            return {"request_id": self.req["request"]["request_id"],
                    "acknowledged": True}
        relay = self.relay(transport)
        with patch("suryadev.validate_url", return_value=None):
            first = relay.tick(self.lib, self.req)
            self.assertEqual(self.lib.stats()["queued"], 1)
            self.assertFalse(first["acknowledged"])
            self.assertEqual(first["receipt"]["queued_urls"], 1)
            self.clock[0] += 301
            again = relay.tick(self.lib, self.req)
        self.assertTrue(again["acknowledged"])
        self.assertEqual(self.lib.stats()["queued"], 1)
        self.assertEqual(calls, ["/api/suryadev/mission/request",
                                 "/api/suryadev/mission/ack",
                                 "/api/suryadev/mission/ack"])

    def test_empty_catalogue_reports_exhausted_no_fake_ack(self):
        def transport(config, path, payload):
            return {"status": "no_approved_work",
                    "request_id": self.req["request"]["request_id"]}
        result = self.relay(transport).tick(self.lib, self.req)
        self.assertEqual(result["state"], "core_curriculum_exhausted")
        self.assertEqual(result["queued_urls"], 0)
        self.assertFalse(result["acknowledged"])
        self.assertEqual(self.lib.stats().get("queued", 0), 0)

    def test_config_requires_private_ip_pin_and_secret(self):
        accepted = load_config(self.cfg)
        self.assertEqual(accepted["host"], "192.168.0.100")
        for invalid in ("http://192.168.0.100:8766", "https://8.8.8.8:8766",
                        "https://192.168.0.100:8766/unsafe"):
            row = json.loads(self.cfg.read_text(encoding="utf-8"))
            row["endpoint"] = invalid
            self.cfg.write_text(json.dumps(row),encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(self.cfg)

    def test_windows_release_relay_is_opt_in_and_installed(self):
        source = Path(__file__).resolve().parents[1]
        worker = (source / "suryadev_extras.py").read_text(encoding="utf-8")
        launcher = (source / "start-continuous-learning.ps1").read_text(encoding="utf-8")
        installer = (source / "install-windows.ps1").read_text(encoding="utf-8")
        self.assertIn('worker.add_argument("--core-mission-config"', worker)
        self.assertIn('relay.tick(lib, renewal)', worker)
        self.assertIn('$CoreMissionConfig', launcher)
        self.assertIn("'suryadev_krishna_mission.py'", installer)


if __name__ == "__main__":
    unittest.main()
