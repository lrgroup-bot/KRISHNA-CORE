"""Regression coverage for generic fleet capacity, parallel video and references.

Does not contact the internet or start an actual model; real audiovisual
coverage and authenticated KRISHNA receipt require separate integration tests.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from suryadev_resources import network_interfaces, recently_verified_source
from suryadev_parallel import AdaptiveResearchWorkers
from suryadev_fleet_client import hardware_report


def sample(cpu=20, ram=28):
    return {"available": True, "sample_time": 100.0,
            "cpu_percent": cpu, "ram_percent": ram,
            "disk_percent": 22.0, "ram_total_gb": 64.0,
            "ram_used_gb": 17.9, "disk_free_gb": 80,
            "network_interface_up": True,
            "network_interface_speed_mbps": 1000,
            "internet_reachable": None, "gpu": {"available": False}}


class HardwareLearningTests(unittest.TestCase):
    def test_network_link_is_not_fabricated_internet_speed(self):
        class FakePsutil:
            @staticmethod
            def net_if_stats():
                return {"Loopback": SimpleNamespace(isup=True,speed=10000),
                        "Ethernet": SimpleNamespace(isup=True,speed=1000),
                        "Wi-Fi": SimpleNamespace(isup=False,speed=433)}
        report=network_interfaces(FakePsutil)
        self.assertEqual(report["link_speed_mbps"],1000)
        self.assertTrue(report["interface_up"])
        self.assertIsNone(report["internet_reachable"])
        self.assertIn("unverified",report["reachability"])
        class NoLink:
            @staticmethod
            def net_if_stats():
                return {"lo":SimpleNamespace(isup=True,speed=10000),
                        "Ethernet":SimpleNamespace(isup=False,speed=1000)}
        self.assertFalse(network_interfaces(NoLink)["interface_up"])

    def test_recent_source_access_proves_only_host_reachability(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            receipt={
                "schema":"suryadev.source-connectivity.v1",
                "source_host":"www.python.org",
                "verified_at":120.0,
                "evidence_sha256":"a"*64,
                "proof":"approved_source_extracted_and_evidence_committed",
                "internet_speed_mbps":None}
            (root/"last-approved-source-connectivity.json").write_text(
                json.dumps(receipt),encoding="utf-8")
            reported=recently_verified_source(root,now=121.0)
            self.assertEqual(reported["verified_host"],"www.python.org")
            self.assertTrue(reported["internet_reachable"])
            self.assertEqual(reported["reachability"],
                             "recent_approved_https_source_success")
            self.assertIsNone(recently_verified_source(root,now=400.0))
            receipt["evidence_sha256"]="incorrect"
            (root/"last-approved-source-connectivity.json").write_text(
                json.dumps(receipt),encoding="utf-8")
            self.assertIsNone(recently_verified_source(root,now=121.0))

    def test_paired_krishna_gets_collector_admission_from_fresh_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"fresh-workspace.json").write_text(json.dumps({
                "schema":"suryadev.fresh-workspace.v1",
                "trial_model":"collector","active_task_limit":3}),encoding="utf-8")
            with patch("suryadev_fleet_client.installed_capabilities",
                       return_value={"capabilities":["website","youtube","pdf"],
                                     "status":"installed_prerequisites_only",
                                     "sources":{}}):
                result=hardware_report(root,sample=sample(),now=100)
            self.assertEqual(result["processing_mode"],"collector_only")
            self.assertLessEqual(result["max_total"],3)
            self.assertGreaterEqual(result["max_total"],1)
            self.assertEqual(result["network_link_speed_mbps"],1000)
            self.assertIsNone(result["internet_reachable"])
            self.assertIsNone(result["internet_speed_mbps"])
            self.assertIn("youtube",result["capabilities"])

    def test_fleet_report_rejects_untimestamped_and_stale_sensor_data(self):
        with tempfile.TemporaryDirectory() as temp:
            for bad_timestamp in (None, float("nan"), 88.0, 112.0, "100"):
                with self.subTest(timestamp=str(bad_timestamp)):
                    reading = sample()
                    if bad_timestamp is None:
                        del reading["sample_time"]
                    else:
                        reading["sample_time"] = bad_timestamp
                    self.assertIsNone(hardware_report(temp, sample=reading, now=100.0))

    def test_three_videos_get_spare_capacity_but_not_if_sources_wait(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"fresh-workspace.json").write_text(json.dumps({
                "schema":"suryadev.fresh-workspace.v1","active_task_limit":3}),encoding="utf-8")
            with AdaptiveResearchWorkers(root,use_ollama=False) as workers:
                workers.video_enabled=True
                with patch("suryadev_parallel.os.cpu_count", return_value=16):
                    idle=workers.pump(telemetry=sample())["capacity"]
                self.assertEqual(idle["max_total"],3)
                self.assertEqual(idle["reserved_video_slots"],3)
                self.assertEqual(idle["source_execution_slots"],0)

    def test_throttle_offline_gpu_overload_to_zero_even_when_videos_wait(self):
        with tempfile.TemporaryDirectory() as temp:
            with AdaptiveResearchWorkers(temp,use_ollama=False) as workers:
                workers.video_enabled=True
                reading=sample(ram=86)
                reading["ram_used_gb"]=55
                report=workers.pump(telemetry=reading)["capacity"]
                self.assertFalse(report["safe"])
                self.assertEqual(report["reserved_video_slots"],0)
                self.assertEqual(report["max_total"],0)

    def test_video_speed_and_original_source_evidence_integrity_contracts(self):
        adapter=Path(__file__).resolve().parents[3]/"scripts"/"SURYDEV_VIDEO_LEARNING_ADAPTER.py"
        source=adapter.read_text(encoding="utf-8")
        self.assertIn("3.0 if self.chatter_streak >= 2", source)
        self.assertIn("actual in (1.0, 1.5, 2.0, 3.0)",source)
        web=(Path(__file__).resolve().parents[1]/"suryadev_garudanetra.py").read_text(encoding="utf-8")
        pdf=(Path(__file__).resolve().parents[1]/"suryadev_ingest.py").read_text(encoding="utf-8")
        self.assertIn('"same_host_links_discovered_not_followed"',web)
        self.assertIn('"page_line_counts"',pdf)
        self.assertIn('"source_reference_url"',pdf)


if __name__ == "__main__":
    unittest.main()
