"""Laptop CPU safety: bounded Ollama requests and conservative worker capacity."""
from __future__ import annotations
import json
import os
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
import unittest

from suryadev import _ollama_thread_budget, summarize
from suryadev_parallel import AdaptiveResearchWorkers


class OllamaThreadBudgetTests(unittest.TestCase):
    def test_default_is_no_more_than_half_logical_cpus(self):
        for logical, expected in ((1,1),(2,1),(4,2),(8,4),(16,4)):
            with self.subTest(logical=logical):
                with patch("suryadev.os.cpu_count", return_value=logical):
                    with patch.dict(os.environ, {"SURYADEV_OLLAMA_THREADS":""}):
                        self.assertEqual(_ollama_thread_budget(), expected)

    def test_managed_worker_budget_is_validated_and_bounded(self):
        with patch("suryadev.os.cpu_count", return_value=8):
            for env, expected in (("2",2),("1",1),("0",1),
                                  ("100",4),("-3",1),("garbled",4)):
                with self.subTest(env=env), patch.dict(os.environ, {"SURYADEV_OLLAMA_THREADS":env}):
                    self.assertEqual(_ollama_thread_budget(), expected)

    def test_ollama_request_enforces_thread_budget_without_truncating_summary(self):
        reqs=[]
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, size):
                return b'{"response":"A faithful source summary"}'
        class Opener:
            def open(self, request, timeout):
                reqs.append((request,timeout))
                return Response()
        with patch("suryadev.os.cpu_count",return_value=8):
            with patch.dict(os.environ, {"SURYADEV_OLLAMA_THREADS":"2"}):
                with patch("suryadev.build_opener",return_value=Opener()):
                    self.assertEqual(summarize("Source content",model="qwen3.5:2b"),
                                     "A faithful source summary")
        request, timeout=reqs[0]
        body=json.loads(request.data)
        self.assertEqual(timeout,120)
        self.assertEqual(body["options"]["num_thread"],2)
        self.assertEqual(body["options"]["num_predict"],512)
        self.assertFalse(body["think"])
        self.assertEqual(body["model"],"qwen3.5:2b")


class OneJobProfileTests(unittest.TestCase):
    def test_managed_profile_reduces_workers_to_one(self):
        reading={"available":True, "cpu_percent":12,
                 "ram_percent":27,"disk_percent":15,
                 "ram_used_gb":3,"ram_total_gb":16,
                 "disk_free_gb":100, "gpu":{"available":False}}
        with TemporaryDirectory() as root:
            with patch.dict(os.environ,{"SURYADEV_MAX_PARALLEL":"1",
                                         "SURYADEV_BROWSER_TABS":"1"}):
                with AdaptiveResearchWorkers(root,use_ollama=False,check_seconds=10) as workers:
                    outcome=workers.pump(telemetry=reading)
                    self.assertEqual(outcome["capacity"]["max_total"],1)
                    self.assertEqual(outcome["capacity"]["laptop_profile"],"single-job")
                    self.assertLessEqual(max(outcome["capacity"]["limits"].values()),1)

    def test_hardware_guard_still_blocks_new_work_at_100_percent(self):
        reading={"available":True, "cpu_percent":100,
                 "ram_percent":30,"disk_percent":15,
                 "ram_used_gb":3,"ram_total_gb":16,
                 "disk_free_gb":100, "gpu":{"available":False}}
        with TemporaryDirectory() as root:
            with patch.dict(os.environ,{"SURYADEV_MAX_PARALLEL":"1"}):
                with AdaptiveResearchWorkers(root,use_ollama=False,check_seconds=10) as workers:
                    outcome=workers.pump(telemetry=reading)
                    self.assertFalse(outcome["capacity"]["safe"])
                    self.assertEqual(outcome["capacity"]["max_total"],0)
                    self.assertEqual(outcome["capacity"]["launched_this_cycle"],[])


if __name__=="__main__":
    unittest.main()
