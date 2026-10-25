"""Universal SURYADEV fleet foundation: portable profile and no forced idle gaps.

No live network, process termination, external media or real model is needed.
Legacy laptop safety contracts remain unchanged.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from suryadev_parallel import AdaptiveResearchWorkers, plan_capacity
from suryadev_mission_cycle import MissionCycle, WORK_SECONDS
from suryadev_dashboard_worker import DashboardWorkerControl

SOURCE = Path(__file__).resolve().parents[1]


def launcher():
    spec = importlib.util.spec_from_file_location("universal_suryadev", SOURCE / "start-node.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def large_node():
    return {"available": True, "cpu_percent": 12, "ram_percent": 8,
            "ram_total_gb": 256, "ram_used_gb": 20.48,
            "disk_percent": 9, "disk_free_gb": 400,
            "gpu": {"available": False}}


class UniversalFleetTests(unittest.TestCase):
    def test_identical_launcher_supports_legacy_and_adaptive_profiles(self):
        with TemporaryDirectory() as root:
            base = Path(root)
            normal = launcher().prepare(base / "one", model="collector")
            fleet = launcher().prepare(base / "two", model="collector",
                                       adaptive_fleet=True, continuous=True)
            old = json.loads((normal / "fresh-workspace.json").read_text())
            new = json.loads((fleet / "fresh-workspace.json").read_text())
            self.assertEqual(old["active_task_limit"], 3)
            self.assertEqual(new["active_task_limit"], 125)
            self.assertEqual(new["node_profile"], "fleet_adaptive")
            self.assertEqual(new["mission_rest_policy"], "continuous")
            # Switching the model must NOT erase evidence or revert the profile.
            (fleet / "learning-proof.txt").write_text("retain", encoding="utf-8")
            launcher().prepare(fleet, model="qwen3.5:2b")
            saved = json.loads((fleet / "fresh-workspace.json").read_text())
            self.assertEqual(saved["node_profile"], "fleet_adaptive")
            self.assertEqual(saved["trial_model"], "qwen3.5:2b")
            self.assertEqual((fleet / "learning-proof.txt").read_text(), "retain")

    def test_headroom_measured_not_hardcoded_to_laptop_three(self):
        with TemporaryDirectory() as root:
            fleet = launcher().prepare(Path(root) / "fleet",
                                       model="collector", adaptive_fleet=True)
            normal = launcher().prepare(Path(root) / "legacy", model="collector")
            reading = large_node()
            with patch.dict(os.environ, {"SURYADEV_MAX_PARALLEL": "125"}), \\
                 patch("suryadev_parallel.os.cpu_count", return_value=256):
                with AdaptiveResearchWorkers(fleet, use_ollama=False) as agent:
                    a = agent.pump(telemetry=reading)["capacity"]
                with AdaptiveResearchWorkers(normal, use_ollama=False) as agent:
                    z = agent.pump(telemetry=reading)["capacity"]
            self.assertGreater(a["max_total"], 10)
            self.assertLessEqual(a["max_total"], 125)
            self.assertEqual(z["max_total"], 3)
            self.assertEqual(a["node_profile"], "fleet_adaptive")
            self.assertEqual(a["active_total"], 0)  # Capacity != tasks actually running

    def test_continuous_six_hour_rollover_does_not_preempt_running_jobs(self):
        with TemporaryDirectory() as tmp:
            node = launcher().prepare(Path(tmp) / "fleet", model="collector",
                                      adaptive_fleet=True, continuous=True)
            clock = [1_800_000_000.0]
            cycle = MissionCycle(node, clock=lambda:clock[0])
            self.assertEqual(cycle.tick(active_jobs=2)["mission_number"], 1)
            clock[0] += WORK_SECONDS
            new = cycle.tick(active_jobs=2)
            self.assertEqual(new["phase"], "work")
            self.assertTrue(new["admission_allowed"])
            self.assertEqual(new["mission_number"], 2)
            self.assertEqual(new["completed_missions"], 1)
            self.assertEqual(new["mission_rest_policy"], "continuous")
            clock[0] += WORK_SECONDS
            self.assertEqual(MissionCycle(node, clock=lambda:clock[0])
                             .tick(active_jobs=1)["mission_number"], 3)

    def test_dashboard_uses_configured_cap_not_actual_resource_claim(self):
        class FakeProcess:
            pid = 99001
            def poll(self): return None
            def send_signal(self, sig): pass

        with TemporaryDirectory() as tmp:
            node = launcher().prepare(Path(tmp) / "fleet", model="collector",
                                      adaptive_fleet=True)
            ctl = DashboardWorkerControl(node, SOURCE)
            try:
                self.assertEqual(ctl.snapshot()["workspace_active_task_limit"], 125)
                with patch("suryadev_dashboard_worker.subprocess.Popen",
                           return_value=FakeProcess()) as spawn, \\
                     patch.dict(os.environ, {"SURYADEV_MAX_PARALLEL": "999"}):
                    result = ctl.start(model="collector")
                self.assertEqual(result["max_parallel_research"], 125)
                self.assertEqual(spawn.call_args.kwargs["env"]["SURYADEV_MAX_PARALLEL"], "125")
                self.assertEqual(result["ollama_required"], False)
            finally:
                ctl.close()


if __name__ == "__main__":
    unittest.main()
