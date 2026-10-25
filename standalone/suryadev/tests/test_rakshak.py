"""RAKSHAK runs as its own process, without a KRISHNA scheduler thread."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from suryadev_rakshak import (
    _valid_core_url, inspect, check_once, STATUS_FILE, ALERT_LOG,
)


class RakshakTests(unittest.TestCase):
    def row(self, **extra):
        base = {"device_id": "suryadev-1", "authenticated": True,
                "last_seen": 1000.0, "telemetry_sample_at": 1000.0,
                "worker_running": True, "network_online": True,
                "cpu_percent": 20, "ram_percent": 30, "disk_percent": 15,
                "thermal_state": "normal", "last_error": ""}
        base.update(extra)
        return base

    def test_strict_loopback_url_only(self):
        self.assertEqual(_valid_core_url(
            "http://127.0.0.1:8766/api/suryadev/fleet/nodes"),
            "http://127.0.0.1:8766/api/suryadev/fleet/nodes")
        for url in ("http://localhost:8766/api/suryadev/fleet/nodes",
                    "http://192.168.0.1:8766/api/suryadev/fleet/nodes",
                    "https://127.0.0.1:8766/api/suryadev/fleet/nodes",
                    "http://127.0.0.1:8766/api/suryadev/fleet/nodes?token=no",
                    "http://127.0.0.1:8766/health"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _valid_core_url(url)

    def test_resource_abuse_and_stale_devices_are_reported_not_killed(self):
        nodes = {"nodes": [self.row(),
                           self.row(device_id="suryadev-2",ram_percent=87),
                           self.row(device_id="suryadev-3",last_seen=800),
                           self.row(device_id="suryadev-4",authenticated=False)]}
        result=inspect(nodes,now=1000)
        self.assertEqual([r["health"] for r in result["nodes"]],
                         ["healthy_telemetry_only","hardware_guard",
                          "heartbeat_stale","unpaired"])
        self.assertEqual(result["unhealthy"],3)
        self.assertTrue(all(not r["automatic_process_killing"] for r in result["nodes"]))
        self.assertFalse(result["rishi_mastery_verified"])

    def test_single_remote_failure_is_not_repeated_in_incident_log(self):
        with TemporaryDirectory() as d:
            def offline(_url):
                raise OSError("Core not connected")
            first=check_once(d,fetch=offline,now=1000)
            second=check_once(d,fetch=offline,now=1300)
            self.assertEqual(first["core_state"],"unreachable")
            self.assertEqual(len(first["state_changes"]),1)
            self.assertEqual(len(second["state_changes"]),0)
            lines=(Path(d)/ALERT_LOG).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines),1)
            self.assertFalse(first["repair_executed"])

    def test_health_changes_and_recovery_are_durable_without_worker_touch(self):
        with TemporaryDirectory() as d:
            good={"nodes":[self.row()]}
            first=check_once(d,fetch=lambda _:good,now=1000)
            self.assertEqual(first["core_state"],"reachable")
            second=check_once(d,fetch=lambda _:good,now=1001)
            self.assertEqual(second["state_changes"],[])
            bad={"nodes":[self.row(ram_percent=90)]}
            third=check_once(d,fetch=lambda _:bad,now=1002)
            self.assertEqual(third["nodes"][0]["health"],"hardware_guard")
            self.assertEqual(len(third["state_changes"]),1)
            stored=json.loads((Path(d)/STATUS_FILE).read_text(encoding="utf-8"))
            self.assertEqual(stored["core_state"],"reachable")
            self.assertFalse(stored["rishi_mastery_verified"])

if __name__=="__main__":
    unittest.main()
