"""SURYADEV must run collector-first on a variety of CPU/laptop hosts."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from suryadev_dashboard_worker import DashboardWorkerControl
from suryadev_parallel import plan_capacity

SOURCE = Path(__file__).resolve().parents[1]


def portable_module():
    spec = importlib.util.spec_from_file_location("suryadev_portable_start",
        SOURCE / "start-node.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PortableNodeTests(unittest.TestCase):
    def test_fast_books_survives_reopen_and_can_be_explicitly_disabled(self):
        runner = portable_module()
        with TemporaryDirectory() as tmp:
            data = Path(tmp) / "study"
            runner.prepare(data, model="collector", fast_books=True)
            evidence = data / "evidence.txt"
            evidence.write_bytes(b"immutable source receipt")
            runner.prepare(data, model="collector")
            marker = data / "fresh-workspace.json"
            self.assertIs(json.loads(marker.read_text())["fast_books"], True)
            runner.prepare(data, model="collector", fast_books=False)
            self.assertIs(json.loads(marker.read_text())["fast_books"], False)
            self.assertEqual(evidence.read_bytes(), b"immutable source receipt")

    def test_four_gigabyte_collector_can_work_without_local_model(self):
        reading = {"available":True,"cpu_percent":18,"ram_percent":50,
                   "ram_total_gb":4,"ram_used_gb":2,
                   "disk_percent":20,"disk_free_gb":20,"gpu":{"available":False}}
        self.assertEqual(plan_capacity(reading,logical_cpus=4)["max_total"],0)
        good = plan_capacity(reading,logical_cpus=4,collector_only=True)
        self.assertTrue(good["safe"])
        self.assertGreaterEqual(good["max_total"],1)
        self.assertEqual(good["local_model_concurrency"],0)
        self.assertEqual(good["processing_mode"],"collector_only")
        reading["ram_percent"] = 85
        self.assertEqual(plan_capacity(reading,logical_cpus=4,collector_only=True)["max_total"],0)

    def test_fresh_portable_workspace_preserves_all_previous_evidence(self):
        runner = portable_module()
        with TemporaryDirectory() as tmp:
            old = Path(tmp)/"old"
            old.mkdir()
            (old/"learning-history.txt").write_text("never erase",encoding="utf-8")
            fresh = Path(tmp)/"fresh"
            prepared=runner.prepare(fresh,model="collector",previous=old)
            marker=json.loads((prepared/"fresh-workspace.json").read_text(encoding="utf-8"))
            self.assertEqual(marker["trial_model"],"collector")
            self.assertEqual(marker["active_task_limit"],3)
            (fresh/"evidence.txt").write_text("keep this",encoding="utf-8")
            runner.prepare(fresh,model="qwen3.5:2b",previous=old)
            self.assertEqual((fresh/"evidence.txt").read_text(),"keep this")
            self.assertEqual((old/"learning-history.txt").read_text(),"never erase")
            self.assertEqual(json.loads((fresh/"fresh-workspace.json").read_text())
                             ["trial_model"],"qwen3.5:2b")
            with self.assertRaisesRegex(ValueError,"within the old"):
                runner.prepare(old/"new",model="collector",previous=old)

    def test_unmarked_existing_directory_never_becomes_fresh_by_accident(self):
        runner = portable_module()
        with TemporaryDirectory() as tmp:
            data=Path(tmp)/"occupied"
            data.mkdir()
            (data/"ledger.sqlite3").write_text("history")
            with self.assertRaisesRegex(ValueError,"Nonempty unmarked"):
                runner.prepare(data,model="collector")
            self.assertTrue((data/"ledger.sqlite3").exists())

    def test_dashboard_collector_flag_and_saved_role_have_no_ollama_dependency(self):
        class FakeProc:
            pid=77721
            def poll(self): return None
            def send_signal(self, signal): pass
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"fresh-workspace.json").write_text(json.dumps({
                "schema":"suryadev.fresh-workspace.v1",
                "trial_model":"qwen3.5:2b", "active_task_limit":3,
                "auto_start":True
            }),encoding="utf-8")
            control=DashboardWorkerControl(root,SOURCE)
            try:
                with patch("suryadev_dashboard_worker.subprocess.Popen",
                           return_value=FakeProc()) as launch:
                    outcome=control.start(model="collector")
                self.assertIn("--no-ollama",launch.call_args.args[0])
                self.assertEqual(outcome["ollama_required"],False)
                self.assertEqual(outcome["max_parallel_research"],3)
                self.assertEqual(outcome["learning_role"],"collector_only")
                self.assertEqual(control.snapshot()["preferred_model"],"collector")
                self.assertEqual(control.snapshot()["managed_model"],"collector")
            finally:
                control.close()

    def test_actual_portable_package_installs_and_prepares_isolated_collector(self):
        # Executed on BOTH Windows and Linux CI; no Ollama or live network.
        spec = importlib.util.spec_from_file_location("suryadev_portable_installer",
            SOURCE / "install-node.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with TemporaryDirectory() as tmp:
            target=Path(tmp)/"installed"
            data=Path(tmp)/"node-ledger"
            installed=installer.install(SOURCE,target,tests=False)
            self.assertEqual(installed,target.resolve())
            self.assertTrue((target/"suryadev_r39_worker.py").is_file())
            self.assertTrue((target/"suryadev_r39_adapter.py").is_file())
            self.assertTrue((target/"start-node.py").is_file())
            runner=portable_module()
            result=runner.prepare(data,model="collector")
            self.assertEqual(result,data.resolve())
            self.assertFalse((data/"suryadev.sqlite3").exists(),
                             "Only the live worker may create its actual SQLite ledger")
            with self.assertRaisesRegex(ValueError,"already has files"):
                installer.install(SOURCE,target,tests=False)

    def test_portable_release_has_no_required_model_or_hardcoded_laptop_path(self):
        runner=(SOURCE/"start-node.py").read_text(encoding="utf-8")
        installer=(SOURCE/"install-node.py").read_text(encoding="utf-8")
        win=(SOURCE/"install-windows.ps1").read_text(encoding="utf-8")
        front=(SOURCE/"dashboard.html").read_text(encoding="utf-8")
        self.assertIn('default="collector"',runner)
        self.assertIn('option value="collector"',front)
        self.assertIn("start-node.py",win)
        self.assertIn("verify_runtime_package.py",installer)
        self.assertNotIn("D:\\Work",runner)
        self.assertNotIn("Remove-Item",runner)
        self.assertNotIn("ollama pull",installer)


if __name__ == "__main__":
    unittest.main()
