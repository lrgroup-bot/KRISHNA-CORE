"""Auto-hardware workload ceilings (100 PDFs) and multi-book safety tests."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from suryadev_parallel import plan_capacity, TOTAL_TARGET, SOURCE_TARGETS, BOOK_TARGET, AdaptiveResearchWorkers
from suryadev_parallel_books import ParallelBookReader
from suryadev_book_continuity import approve_book
from suryadev_book_reader import BookLedger


def hardware(cpu=10,ram=30,ram_total=128,ram_used=30):
    return {"available":True,"cpu_percent":cpu,"ram_percent":ram,
            "ram_total_gb":ram_total,"ram_used_gb":ram_used,
            "disk_percent":15,"disk_free_gb":300,
            "gpu":{"available":False}}


class ConcurrentLearningTests(unittest.TestCase):
    def test_large_workload_budget_does_not_override_measured_limits(self):
        self.assertEqual(SOURCE_TARGETS,{"website":10,"youtube":10,"pdf":100})
        self.assertEqual(BOOK_TARGET,5)
        self.assertEqual(TOTAL_TARGET,125)
        big=plan_capacity(hardware(),logical_cpus=128)
        self.assertEqual(big["target_total"],125)
        self.assertEqual(big["limits"]["website"],10)
        self.assertEqual(big["limits"]["pdf"], min(100,big["max_total"]))
        self.assertEqual(big["limits"]["book"],5)
        self.assertEqual(big["capacity_mode"],"automatic_hardware")
        self.assertTrue(big["backlog_is_not_running"])
        self.assertEqual(big["youtube_provider_concurrent_limit"],1)
        small=plan_capacity(hardware(cpu=38,ram=68,ram_total=16,ram_used=10.9),
                            logical_cpus=12)
        self.assertLess(small["max_total"],125)
        for sample in (hardware(cpu=85),hardware(ram=85),
                       dict(hardware(),disk_percent=85),
                       dict(hardware(),gpu={"available":True,
                                           "usage_percent":85,"vram_percent":1})):
            self.assertEqual(plan_capacity(sample,logical_cpus=64)["max_total"],0)

    def test_future_large_server_can_admit_more_than_old_fixed_45_cap(self):
        node=hardware(cpu=10,ram=22,ram_total=512,ram_used=100)
        admitted=plan_capacity(node,logical_cpus=256)
        self.assertGreater(admitted["max_total"],45)
        self.assertEqual(admitted["limits"]["pdf"],100)
        self.assertEqual(admitted["capacity_mode"],"automatic_hardware")
        self.assertEqual(admitted["youtube_provider_concurrent_limit"],1)

    def test_one_hundred_pdf_tasks_can_wait_in_queue_without_launch(self):
        from suryadev import Library
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            lib=Library(folder)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    for i in range(100):
                        lib.add("https://example.com/manual-%03d.pdf" % i)
                self.assertEqual(lib.stats()["queued"],100)
                with AdaptiveResearchWorkers(folder,use_ollama=False) as pool:
                    with patch("suryadev_parallel.os.cpu_count",return_value=12):
                        report=pool.pump(telemetry=hardware(cpu=85))
                    self.assertEqual(report["capacity"]["active_total"],0)
                    self.assertEqual(report["capacity"]["queued"]["pdf"],100)
                    self.assertEqual(report["capacity"]["max_total"],0)
                self.assertEqual(lib.stats()["queued"],100)
            finally:
                lib.db.close()

    def test_book_reserved_slots_do_not_exceed_available_capacity(self):
        with tempfile.TemporaryDirectory() as root:
            with AdaptiveResearchWorkers(root,use_ollama=False,books_enabled=True) as pool:
                with patch("suryadev_parallel.os.cpu_count",return_value=96):
                    c=pool.pump(telemetry=hardware())["capacity"]
                self.assertEqual(c["reserved_book_slots"],5)
                self.assertEqual(c["source_execution_slots"],
                                 c["max_total"]-5)

    def test_external_books_and_videos_reduce_new_source_admission(self):
        with tempfile.TemporaryDirectory() as root:
            with AdaptiveResearchWorkers(root,use_ollama=False,books_enabled=True) as pool:
                pool.video_enabled = True
                pool.external_active = 6
                with patch("suryadev_parallel.os.cpu_count",return_value=12):
                    result=pool.pump(telemetry=hardware())["capacity"]
                self.assertEqual(result["source_execution_slots"],0)
                self.assertEqual(result["non_source_active"],6)
                self.assertEqual(result["launched_this_cycle"],[])

    def test_five_books_advance_with_serial_model_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for i in range(5):
                item=root/("approved-"+str(i)+".txt")
                item.write_text("one\nsecond\nthird "+str(i),encoding="utf-8")
                approve_book(root,item)
            lock=threading.Lock()
            concurrency=[0]
            maximum=[0]
            def model(prompt,name):
                with lock:
                    concurrency[0]+=1
                    maximum[0]=max(maximum[0],concurrency[0])
                time.sleep(.035)
                with lock:
                    concurrency[0]-=1
                return "Unverified local note"
            pool=ParallelBookReader(root,root/"book-plan.json",
                                    model="test-model",observe=model)
            try:
                capacity={"safe":True,"max_total":125,"reserved_book_slots":5}
                started=pool.tick(capacity=capacity,source_active=20)
                self.assertEqual(len(started["started_this_tick"]),5)
                self.assertEqual(started["active"],5)
                until=time.monotonic()+8
                while pool.futures and time.monotonic()<until:
                    time.sleep(.04)
                    pool.tick(capacity={"safe":False,"max_total":0,
                                        "reserved_book_slots":0})
                self.assertFalse(pool.futures)
                self.assertEqual(maximum[0],1)
                ledger=BookLedger(root)
                try:
                    books=ledger.status()["books"]
                    self.assertEqual(len(books),5)
                    self.assertTrue(all(
                        x["sessions"]["ollama:test-model"]["lines_processed"]==1
                        for x in books))
                finally:
                    ledger.close()
            finally:
                pool.close()

    def test_small_laptop_reserves_only_one_book_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/"one.txt"
            source.write_text("first",encoding="utf-8")
            approve_book(root,source)
            pool=ParallelBookReader(root,root/"book-plan.json",model="test",
                                    observe=lambda *_:"Model candidate")
            try:
                state=pool.tick(capacity={"safe":False,"max_total":0,
                                          "reserved_book_slots":0})
                self.assertEqual(state["active"],0)
                state=pool.tick(capacity={"safe":True,"max_total":2,
                                          "reserved_book_slots":1},source_active=1)
                self.assertEqual(len(state["started_this_tick"]),1)
            finally:
                pool.close()


if __name__=="__main__":
    unittest.main()
