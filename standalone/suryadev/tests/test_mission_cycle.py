"""Deterministic six-hour mission / ten-minute device-rest regression tests."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from suryadev_mission_cycle import MissionCycle, FILE, WORK_SECONDS, REST_SECONDS
from suryadev_parallel import AdaptiveResearchWorkers
from suryadev_liveops import operations_snapshot
from suryadev import Library


class MissionCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.clock=[1_800_000_000.0]
        self.cycle=MissionCycle(self.root,clock=lambda:self.clock[0])

    def test_six_hours_then_ten_minutes_then_new_six_hour_window(self):
        start=self.cycle.tick(active_jobs=0)
        self.assertEqual(start["phase"],"work")
        self.assertTrue(start["admission_allowed"])
        self.assertEqual(start["mission_number"],1)
        self.clock[0]+=WORK_SECONDS-1
        self.assertEqual(self.cycle.tick(active_jobs=0)["phase"],"work")
        self.clock[0]+=1
        pause=self.cycle.tick(active_jobs=0)
        self.assertEqual(pause["phase"],"rest")
        self.assertFalse(pause["admission_allowed"])
        self.assertEqual(pause["remaining_rest_seconds"],600)
        self.clock[0]+=REST_SECONDS-1
        self.assertEqual(MissionCycle(self.root,clock=lambda:self.clock[0]).tick()["phase"],"rest")
        self.clock[0]+=1
        active=self.cycle.tick()
        self.assertEqual(active["phase"],"work")
        self.assertEqual(active["mission_number"],2)
        self.assertEqual(active["completed_missions"],1)
        self.assertTrue(active["admission_allowed"])
        self.assertEqual(active["remaining_work_seconds"],WORK_SECONDS)

    def test_existing_long_running_task_drains_before_rest_begins(self):
        self.cycle.tick()
        self.clock[0]+=WORK_SECONDS+5
        pending=self.cycle.tick(active_jobs=2)
        self.assertEqual(pending["phase"],"draining")
        self.assertFalse(pending["admission_allowed"])
        self.clock[0]+=900
        self.assertEqual(self.cycle.tick(active_jobs=1)["phase"],"draining")
        finished=self.cycle.tick(active_jobs=0)
        self.assertEqual(finished["phase"],"rest")
        self.assertEqual(finished["remaining_rest_seconds"],600)
        self.clock[0]+=600
        self.assertEqual(self.cycle.tick()["phase"],"work")

    def test_worker_restart_cannot_skip_rest_or_erase_last_window(self):
        self.cycle.tick()
        self.clock[0]+=WORK_SECONDS
        self.cycle.tick()
        first=MissionCycle(self.root,clock=lambda:self.clock[0])
        self.clock[0]+=100
        self.assertEqual(first.tick()["remaining_rest_seconds"],500)
        self.assertTrue((self.root/FILE).is_file())
        self.assertEqual(first.tick()["completed_missions"],0)

    def test_invalid_active_count_and_state_fail_closed(self):
        for active in (-1,1.5,False,1001):
            with self.subTest(active=active),self.assertRaises(ValueError):
                self.cycle.tick(active_jobs=active)
        (self.root/FILE).write_text('{"schema":"unknown"}',encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError,"Unknown mission state"):
            self.cycle.tick()

    def test_capacity_scheduler_supports_nonadmission_without_queue_loss(self):
        reading={"available":True,"cpu_percent":10,"ram_percent":28,
                 "disk_percent":10,"ram_total_gb":16,"ram_used_gb":4.48,
                 "disk_free_gb":100,"gpu":{"available":False}}
        with AdaptiveResearchWorkers(self.root,use_ollama=False,check_seconds=10) as workers:
            paused=workers.pump(telemetry=reading,admit_new=False)["capacity"]
            self.assertFalse(paused["safe"])
            self.assertEqual(paused["max_total"],0)
            self.assertTrue(paused["hardware_safe_before_mission_pause"])
            self.assertFalse(paused["launched_this_cycle"])
        lib = Library(self.root)
        try:
            self.assertEqual(lib.stats().get("done",0),0)
        finally:
            lib.db.close()

    def test_low_battery_or_real_hot_sensor_prevents_new_assignments(self):
        from suryadev_parallel import plan_capacity
        reading={"available":True,"cpu_percent":10,"ram_percent":25,
                 "disk_percent":10,"ram_total_gb":16,"ram_used_gb":4,
                 "disk_free_gb":100,"gpu":{"available":False},
                 "battery_percent":19,"battery_plugged":False}
        self.assertFalse(plan_capacity(reading,collector_only=True)["safe"])
        reading["battery_plugged"]=True
        self.assertTrue(plan_capacity(reading,collector_only=True)["safe"])
        reading["temperature_max_c"]=86
        self.assertFalse(plan_capacity(reading,collector_only=True)["safe"])
        reading["temperature_max_c"]=None
        self.assertTrue(plan_capacity(reading,collector_only=True)["safe"])

    def test_read_only_ops_shows_persisted_mission_cycle(self):
        status=self.cycle.tick()
        lib=Library(self.root)
        try:
            view=operations_snapshot(lib.db,self.root)
            self.assertEqual(view["mission_cycle"]["phase"],status["phase"])
        finally:
            lib.db.close()


if __name__ == "__main__":
    unittest.main()
