"""Fresh SURYADEV workspace contract: previous learning retained; cap new work at 3."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_dashboard_worker import DashboardWorkerControl
from suryadev_parallel import AdaptiveResearchWorkers

SOURCE = Path(__file__).resolve().parents[1]


def safe_telemetry():
    return {"available": True, "cpu_percent": 12, "ram_percent": 31,
            "ram_total_gb": 128, "ram_used_gb": 35,
            "disk_percent": 9, "disk_free_gb": 90, "gpu": {"available": False}}


class FreshWorkspaceTests(unittest.TestCase):
    def test_fresh_root_has_zero_previous_tasks_without_destroying_history(self):
        with tempfile.TemporaryDirectory() as temp:
            old_root=Path(temp)/"learning-previous"
            fresh_root=Path(temp)/"learning-fresh"
            old=Library(old_root)
            try:
                old.add("https://playwright.dev/python/docs/intro")
                old.add("https://www.python.org/")
                old_count=old.stats()["queued"]
                fresh=Library(fresh_root)
                try:
                    self.assertEqual(old_count,2)
                    self.assertEqual(fresh.stats()["queued"],0)
                    self.assertTrue((old_root/"suryadev.sqlite3").is_file())
                    self.assertTrue((fresh_root/"suryadev.sqlite3").is_file())
                finally:
                    fresh.db.close()
                self.assertEqual(old.stats()["queued"],2)
            finally:
                old.db.close()

    def test_fresh_marker_and_model_represented_in_dashboard(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"fresh-workspace.json").write_text(json.dumps({
                "schema":"suryadev.fresh-workspace.v1",
                "active_task_limit":3, "auto_start":True,
                "trial_model":"qwen3.5:9b"}),encoding="utf-8")
            ctl=DashboardWorkerControl(root,SOURCE)
            try:
                report=ctl.snapshot()
                self.assertEqual(report["workspace_mode"],"fresh")
                self.assertTrue(report["workspace_previous_retained"])
                self.assertEqual(report["workspace_active_task_limit"],3)
            finally:
                ctl.close()

    def test_dashboard_start_caps_active_jobs_and_accepts_local_nine_b_model(self):
        class FakeProcess:
            pid=90003
            def poll(self): return None
            def send_signal(self, _signal): pass
        with tempfile.TemporaryDirectory() as temp:
            ctl=DashboardWorkerControl(temp,SOURCE)
            try:
                with patch("suryadev_dashboard_worker.subprocess.Popen",return_value=FakeProcess()) as popen:
                    with patch.dict(os.environ,{"SURYADEV_MAX_PARALLEL":"20"}):
                        outcome=ctl.start(model="qwen3.5:9b")
                    self.assertEqual(popen.call_args.kwargs["env"]["SURYADEV_MAX_PARALLEL"],"3")
                    self.assertEqual(outcome["max_parallel_research"],3)
            finally:
                ctl.close()

    def test_global_three_task_cap_is_admission_not_queue_truncation(self):
        blocker=threading.Event()
        class OfflineBrowser:
            def __init__(self, root, max_tabs): self._tabs=[]
            def start(self): pass
            def stop(self): pass
        with tempfile.TemporaryDirectory() as temp:
            lib=Library(temp)
            try:
                for i in range(12):
                    lib.add("https://playwright.dev/python/docs/intro?chapter="+str(i))
                with AdaptiveResearchWorkers(temp,use_ollama=False,
                                             browser_factory=OfflineBrowser) as pool:
                    pool._work=lambda kind:(blocker.wait(timeout=2),{"status":"test"})[1]
                    with patch.dict(os.environ,{"SURYADEV_MAX_PARALLEL":"3"}):
                        with patch("suryadev_parallel.os.cpu_count",return_value=32):
                            report=pool.pump(telemetry=safe_telemetry())["capacity"]
                    self.assertEqual(report["max_total"],3)
                    self.assertEqual(report["active_total"],3)
                    self.assertEqual(report["queued"]["website"],9)
            finally:
                blocker.set()
                lib.db.close()

    def test_frontend_launcher_installed_and_no_manual_source_entry(self):
        html=(SOURCE/"dashboard.html").read_text(encoding="utf-8")
        launcher=(SOURCE/"start-fresh-workspace.ps1").read_text(encoding="utf-8")
        install=(SOURCE/"install-windows.ps1").read_text(encoding="utf-8")
        for snippet in ('id="learning-workspace-state"','Current session assignments',
                        "Fresh learning","qwen3.5:9b"):
            self.assertIn(snippet,html)
        self.assertNotIn('id="video-auto-url"',html)
        self.assertIn("start-fresh-workspace.ps1",install)
        self.assertIn('SURYADEV_MAX_PARALLEL = "3"',launcher)
        self.assertIn('SURYADEV_LEARNING_TRIAL = "1"',launcher)
        self.assertIn('WriteAllText($marker',launcher)
        self.assertNotIn('Remove-Item',launcher)
        self.assertNotIn('del /',launcher)


if __name__=="__main__":
    unittest.main()
