"""Deterministic conservative SURYADEV local-model selection tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from suryadev_model_router import decide_model, resolve_model, SMALL_MODEL
from suryadev_dashboard_worker import DashboardWorkerControl

SOURCE=Path(__file__).resolve().parents[1]


def healthy():
    return {"available":True,"cpu_percent":22,"ram_percent":40,
            "ram_total_gb":16,"ram_used_gb":6.4,"disk_free_gb":50,
            "temperature_max_c":50,"battery_plugged":True,
            "gpu":{"available":False}}


class ModelRouterTests(unittest.TestCase):
    def test_small_installed_model_only_under_measured_headroom(self):
        self.assertEqual(decide_model(healthy(),installed=True)["model"],SMALL_MODEL)
        self.assertEqual(decide_model(healthy(),installed=False)["model"],"collector")
        for changes in ({"ram_percent":78},{"cpu_percent":82},
                        {"ram_total_gb":4,"ram_used_gb":2},
                        {"ram_used_gb":14},{"disk_free_gb":1},
                        {"temperature_max_c":82},
                        {"battery_plugged":False,"battery_percent":25},
                        {"gpu":{"available":True,"usage_percent":86}}):
            with self.subTest(changes=changes):
                state=dict(healthy(),**changes)
                self.assertEqual(decide_model(state,installed=True)["model"],"collector")

    def test_auto_does_not_probe_model_when_node_overloaded(self):
        overloaded=dict(healthy(), ram_percent=89)
        def forbidden():
            raise AssertionError("must not touch even local Ollama on overloaded machine")
        self.assertEqual(resolve_model("auto","unused",measurement=overloaded,probe=forbidden)
                         ["model"],"collector")
        self.assertEqual(resolve_model("auto","unused",measurement=healthy(),
                       probe=lambda:True)["model"],SMALL_MODEL)
        self.assertEqual(resolve_model("auto","unused",measurement=healthy(),
                       probe=lambda:False)["model"],"collector")

    def test_explicit_collector_does_not_require_telemetry(self):
        self.assertEqual(resolve_model("collector","unused")["model"],"collector")

    def test_managed_worker_auto_resolves_into_collector_without_model(self):
        class FakeProcess:
            pid=654321
            def poll(self): return None
            def send_signal(self, sig): pass
        with TemporaryDirectory() as d:
            root=Path(d)
            control=DashboardWorkerControl(root,SOURCE)
            try:
                with patch("suryadev_model_router.resolve_model",
                           return_value={"model":"collector","reason":"no_model","auto":True}), \
                     patch("suryadev_dashboard_worker.subprocess.Popen",
                           return_value=FakeProcess()) as fake:
                    out=control.start(model="auto")
                args=fake.call_args.args[0]
                self.assertIn("--no-ollama",args)
                self.assertEqual(out["model"],"collector")
                self.assertEqual(out["requested_model"],"auto")
                self.assertFalse(out["ollama_required"])
                self.assertEqual(fake.call_args.kwargs["env"]["SURYADEV_COLLECTOR_ONLY"],"1")
            finally:
                control.close()


if __name__=="__main__":
    unittest.main()
