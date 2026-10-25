"""Malformed live telemetry must never authorize additional SURYADEV workers.

Offline regression for the adaptive governor; independent of any physical PC.
"""
import math
import unittest

from suryadev_parallel import plan_capacity


def healthy():
    return {
        "available": True,
        "cpu_percent": 20.0,
        "ram_percent": 30.0,
        "disk_percent": 25.0,
        "ram_total_gb": 64.0,
        "ram_used_gb": 19.2,
        "disk_free_gb": 100.0,
        "gpu": {"available": False},
        "battery_plugged": True,
    }


class FailClosedTelemetryTests(unittest.TestCase):
    def test_legitimate_collector_is_admitted(self):
        accepted = plan_capacity(healthy(), logical_cpus=16, collector_only=True)
        self.assertTrue(accepted["safe"])
        self.assertGreater(accepted["max_total"], 0)

    def test_invalid_or_absent_critical_measurement_is_never_capacity(self):
        for field, bad in (
            ("cpu_percent", float("nan")),
            ("ram_percent", float("inf")),
            ("disk_percent", None),
            ("ram_total_gb", "64"),
            ("ram_used_gb", float("nan")),
            ("disk_free_gb", -1.0),
            ("cpu_percent", -5),
            ("ram_percent", 101),
            ("ram_total_gb", 0),
            ("ram_used_gb", 70),
        ):
            with self.subTest(field=field, value=str(bad)):
                sample = healthy()
                sample[field] = bad
                denied = plan_capacity(sample, logical_cpus=16, collector_only=True)
                self.assertFalse(denied["safe"])
                self.assertEqual(denied["max_total"], 0)
                self.assertTrue(all(v == 0 for v in denied["limits"].values()))

    def test_gpu_thermal_and_unplugged_battery_gaps_denied(self):
        for changes in (
            {"gpu": ["not", "a", "sensor"]},
            {"gpu": {"available": True, "usage_percent": None, "vram_percent": 3}},
            {"gpu": {"available": True, "usage_percent": 2, "vram_percent": float("nan")}},
            {"temperature_max_c": float("nan")},
            {"temperature_max_c": "unknown"},
            {"battery_plugged": False, "battery_percent": None},
            {"battery_plugged": False, "battery_percent": float("inf")},
        ):
            with self.subTest(changes=str(changes)):
                sample = {**healthy(), **changes}
                denied = plan_capacity(sample, logical_cpus=16, collector_only=True)
                self.assertFalse(denied["safe"])
                self.assertEqual(denied["max_total"], 0)

    def test_valid_measured_gpu_and_battery_are_supported(self):
        sample = healthy()
        sample["gpu"] = {"available": True, "usage_percent": 8,
                         "vram_percent": 12}
        sample["battery_plugged"] = False
        sample["battery_percent"] = 85
        accepted = plan_capacity(sample, logical_cpus=16, collector_only=True)
        self.assertTrue(accepted["safe"])
        sample["gpu"]["vram_percent"] = 90
        self.assertFalse(plan_capacity(sample, logical_cpus=16)["safe"])


if __name__ == "__main__":
    unittest.main()
