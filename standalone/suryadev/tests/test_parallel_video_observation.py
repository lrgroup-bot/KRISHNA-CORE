"""Video observer scheduling uses one owner's worker and fails closed.

No YouTube network requests or browser launches; the executor is a stub.
"""
from pathlib import Path
import json
import tempfile
import threading
import time
import unittest

from suryadev_parallel_videos import ParallelVideoReader


URLS = (
    "https://www.youtube.com/watch?v=mgBpcQRDtl0",
    "https://www.youtube.com/watch?v=abcdefghijk",
    "https://www.youtube.com/watch?v=123456789ab",
)


class ParallelVideoObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.app=self.root/"application"
        self.app.mkdir()
        (self.app/"suryadev_r39_worker.py").write_text("# test placeholder\n")
        (self.app/"suryadev_r39_adapter.py").write_text("# test placeholder\n")
        (self.root/"learning-plan.json").write_text(json.dumps({
            "approved_urls":list(URLS),"allowed_source_hosts":["www.youtube.com"],
            "approved_feeds":[],"max_new_per_cycle":5,"max_queued":20
        }),encoding="utf-8")

    def enable(self):
        (self.root/"video-auto.json").write_text(json.dumps({
            "schema":"suryadev.video-auto.v1","enabled":True
        }),encoding="utf-8")

    def test_off_by_default_requires_explicit_owner_activation(self):
        called=[]
        video=ParallelVideoReader(self.root,self.app,execute=lambda p:called.append(p))
        try:
            ready={"safe":True,"max_total":45,"reserved_video_slots":10}
            result=video.tick(capacity=ready)
            self.assertFalse(result["enabled"])
            self.assertEqual(result["active"],0)
            self.assertEqual(called,[])
            self.assertEqual(list((self.root/"video-review").glob("**/approved-inbox/*.json")),[])
        finally:
            video.close()

    def test_multiple_distinct_browser_sessions_can_be_scheduled_without_duplicate(self):
        self.enable()
        lock=threading.Lock()
        arrivals=[]
        go=threading.Event()
        def fake_runner(path):
            with lock:
                arrivals.append(path.stem)
            go.wait(timeout=3)
            return {"state":"evidence_ready_not_verified","job":path.stem}
        video=ParallelVideoReader(self.root,self.app,execute=fake_runner)
        try:
            cap={"safe":True,"max_total":45,"reserved_video_slots":10}
            result=video.tick(capacity=cap,source_active=20,books_active=5)
            self.assertEqual(result["active"],3)
            self.assertEqual(len(result["started_this_tick"]),3)
            until=time.monotonic()+3
            while len(arrivals)<3 and time.monotonic()<until:
                time.sleep(.02)
            self.assertEqual(len(arrivals),3)
            second=video.tick(capacity=cap,source_active=20,books_active=5)
            self.assertEqual(second["started_this_tick"],[])
            go.set()
            for _ in range(80):
                status=video.tick(capacity=cap,source_active=20,books_active=5)
                if not video.futures:
                    break
                time.sleep(.02)
            self.assertFalse(video.futures)
            self.assertEqual(len(status["finished"]),3)
            self.assertTrue(all(not x.get("core_acceptance_verified",False)
                                for x in status["finished"]))
        finally:
            go.set()
            video.close()
        # Reboot never silently replays approved jobs with existing evidence.
        resumed=ParallelVideoReader(self.root,self.app,execute=fake_runner)
        try:
            outcome=resumed.tick(capacity=cap)
            self.assertEqual(outcome["started_this_tick"],[])
        finally:
            resumed.close()

    def test_hardware_and_book_source_slots_limit_video_launch(self):
        self.enable()
        go=threading.Event()
        pool=ParallelVideoReader(self.root,self.app,execute=lambda p:go.wait(2))
        try:
            deny=pool.tick(capacity={"safe":False,"max_total":0,
                                     "reserved_video_slots":0})
            self.assertEqual(deny["active"],0)
            small=pool.tick(capacity={"safe":True,"max_total":3,
                                      "reserved_video_slots":2},
                            source_active=1,books_active=1)
            self.assertEqual(small["active"],1)
            self.assertEqual(len(small["started_this_tick"]),1)
        finally:
            go.set()
            pool.close()


if __name__=="__main__":
    unittest.main()
