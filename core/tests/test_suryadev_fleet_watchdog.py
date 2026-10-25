"""Read-only 5-minute SURYADEV watchdog: detected errors do not kill apps."""
import time
import unittest

from krishna_core.suryadev_fleet_watchdog import (
    SuryadevFleetWatchdog, fleet_health_report, INTERVAL_SECONDS,
)


class SuryadevFleetWatchdogTests(unittest.TestCase):
    def sample(self, **changes):
        row = {
            "device_id":"suryadev-1","authenticated":True,
            "last_seen":1000,"telemetry_sample_at":1000,
            "cpu_percent":30,"ram_percent":40,"disk_percent":20,
            "network_online":True,"worker_running":True,
            "thermal_state":"normal","last_error":"",
        }
        row.update(changes)
        return row

    def test_no_commands_are_sent_and_stale_nodes_reported(self):
        report = fleet_health_report({"nodes":[self.sample(),
            self.sample(device_id="suryadev-2",last_seen=600)]},now=1000)
        self.assertEqual(report["interval_seconds"],300)
        self.assertEqual(report["unhealthy"],1)
        self.assertEqual(report["nodes"][0]["health"],"healthy_telemetry_only")
        self.assertEqual(report["nodes"][1]["health"],"heartbeat_stale")
        self.assertFalse(report["automatic_process_killing"])
        self.assertFalse(report["mastery_verified"])

    def test_hot_resources_fails_closed_and_unauthenticated_excluded(self):
        report = fleet_health_report({"nodes":[
            self.sample(ram_percent=90),
            self.sample(device_id="suryadev-2",authenticated=False),
            self.sample(device_id="suryadev-3",last_error="network problem"),
        ]},now=1000)
        self.assertEqual([row["health"] for row in report["nodes"]],
                         ["resource_guard_ram","unpaired_or_unauthenticated","reported_error"])

    def test_scheduler_can_check_without_starting_background_thread(self):
        records={"nodes":[self.sample(last_seen=time.time(),
                                       telemetry_sample_at=time.time())]}
        watcher=SuryadevFleetWatchdog(lambda:records, interval_seconds=15)
        self.assertEqual(watcher.interval_seconds,INTERVAL_SECONDS)
        self.assertEqual(watcher.status()["checks"],0)
        report=watcher.check()
        self.assertEqual(report["unhealthy"],0)
        self.assertEqual(watcher.status()["checks"],1)
        self.assertFalse(watcher.status()["running"])
        watcher.stop()


if __name__ == "__main__":
    unittest.main()
