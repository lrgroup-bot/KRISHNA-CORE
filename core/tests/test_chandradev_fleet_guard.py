"""CHANDRADEV health is read-only; unknown hardware is never assumed healthy."""
import unittest
from krishna_core.chandradev_fleet_guard import inspect_fleet

NOW=1000.0

def node(**kw):
    base={"device_id":"suryadev-01","last_seen":NOW,
          "telemetry_sample_at":NOW,"authenticated":True,
          "worker_running":True,"network_online":True,"last_error":"",
          "cpu_percent":45,"ram_percent":50,"disk_percent":22,
          "thermal_state":"unknown","gpu":{"available":False}}
    base.update(kw)
    return base

class FleetGuardianTests(unittest.TestCase):
    def test_unknown_temperature_is_reported_without_fabricating_it(self):
        result=inspect_fleet({"nodes":[node()]},now=NOW)
        self.assertEqual(result["node_count"],1)
        self.assertIn("temperature",result["nodes"][0]["unmeasured"])
        self.assertIn("gpu_utilization",result["nodes"][0]["unmeasured"])
        self.assertTrue(result["nodes"][0]["new_job_admission_recommended"])
    def test_stale_overloaded_and_unauthenticated_rejected(self):
        rows=[node(device_id="suryadev-1",last_seen=NOW-160),
              node(device_id="suryadev-2",ram_percent=85),
              node(device_id="suryadev-3",authenticated=False),
              node(device_id="suryadev-4",telemetry_sample_at=NOW-46)]
        r=inspect_fleet({"nodes":rows},now=NOW)
        self.assertEqual(r["alerts"],4)
        self.assertFalse(any(x["new_job_admission_recommended"] for x in r["nodes"]))
        self.assertEqual(r["nodes"][1]["state"],"critical")
    def test_no_report_is_fail_closed(self):
        with self.assertRaises(ValueError):
            inspect_fleet({},now=NOW)

if __name__=="__main__":
    unittest.main()
