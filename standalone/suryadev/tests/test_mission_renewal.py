"""Six-hour KRISHNA request contracts without false delivery claims."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_liveops import operations_snapshot
from suryadev_mission_renewal import RENEWAL_FILE, renewal_tick


class MissionRenewalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lib = Library(self.root)

    def tearDown(self):
        self.lib.db.close()
        self.temp.cleanup()

    def add(self, url):
        with patch("suryadev.validate_url", return_value=None):
            return self.lib.add(url)

    def test_empty_queue_requests_exactly_one_six_hour_batch(self):
        first = renewal_tick(self.lib, now=1000)
        self.assertEqual(first["status"], "awaiting_assignment")
        self.assertEqual(first["request"]["desired_hours"], 6)
        self.assertEqual(first["transport"], "read_only_bridge_outbox")
        self.assertFalse(first["delivered_to_krishna"])
        self.assertFalse(first["krishna_assignment_acknowledged"])
        self.assertFalse(first["brahmagyan_acknowledged"])
        second = renewal_tick(self.lib, now=4000)
        self.assertEqual(first, second)
        self.assertTrue((self.root / RENEWAL_FILE).is_file())
        visible = operations_snapshot(self.lib.db, self.root)["mission_renewal"]
        self.assertEqual(visible["request"]["request_id"],
                         first["request"]["request_id"])

    def test_local_sources_do_not_fabricate_core_delivery(self):
        request = renewal_tick(self.lib, now=100)
        for n in range(3):
            self.add("https://example.org/research-" + str(n))
        available = renewal_tick(self.lib, now=200)
        self.assertEqual(available["status"], "local_work_available")
        self.assertEqual(available["eligible_queued_or_running"], 3)
        self.assertEqual(available["request"]["request_id"],
                         request["request"]["request_id"])
        self.assertFalse(available["delivered_to_krishna"])
        self.assertFalse(available["krishna_assignment_acknowledged"])
        self.lib.db.execute("UPDATE jobs SET status='done'")
        self.lib.db.commit()
        again = renewal_tick(self.lib, now=300)
        self.assertEqual(again["status"], "awaiting_assignment")
        self.assertNotEqual(again["request"]["request_id"],
                            request["request"]["request_id"])

    def test_rate_limited_youtube_is_not_executable_backlog(self):
        self.add("https://www.youtube.com/watch?v=mgBpcQRDtl0")
        ready = renewal_tick(self.lib, now=100, low_water=1)
        self.assertEqual(ready["status"], "local_work_available")
        blocked = renewal_tick(self.lib, now=200, low_water=1,
                               youtube_blocked=True)
        self.assertEqual(blocked["blocked_youtube"], 1)
        self.assertEqual(blocked["eligible_queued_or_running"], 0)
        self.assertEqual(blocked["status"], "awaiting_assignment")

    def test_deadline_is_reported_not_automatically_extended(self):
        state = renewal_tick(self.lib, now=100, session_ends_at=21700)
        self.assertEqual(state["session_ends_at"], 21700)
        self.assertEqual(state["request"]["desired_hours"], 6)
        self.assertFalse(state["delivered_to_krishna"])

    def test_invalid_parameters_fail_without_creating_requests(self):
        with self.assertRaises(ValueError):
            renewal_tick(self.lib, low_water=0)
        with self.assertRaises(ValueError):
            renewal_tick(self.lib, now=-100)
        self.assertFalse((self.root / RENEWAL_FILE).exists())

    def test_launcher_and_worker_integrations_ship_module(self):
        source = Path(__file__).resolve().parents[1]
        worker = (source / "suryadev_extras.py").read_text(encoding="utf-8")
        mission = (source / "suryadev_mission.py").read_text(encoding="utf-8")
        installer = (source / "install-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("renewal_tick(lib, youtube_blocked=", worker)
        self.assertIn("session_ends_at=deadline", mission)
        self.assertIn("'suryadev_mission_renewal.py'", installer)
        self.assertIn("suryadev_mission_renewal", installer)

    def test_work_loop_emits_request_without_remote_connection(self):
        import suryadev_extras
        class FakeFeeder:
            next_due = 12345
            def __init__(self, *args, **kwargs): pass
            def tick(self, *args, **kwargs): return None
            def stop(self): pass
        class FakeWorkers:
            youtube_access = {"state": "ready"}
            def __init__(self, *args, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            futures = {}
            def pump(self, *, admit_new=True):
                return {"finished": [], "capacity": {"active_total": 0}}
        plan = self.root / "learning-plan.json"
        plan.write_text('{"approved_urls":[],"approved_feeds":[],"allowed_source_hosts":[]}',
                        encoding="utf-8")
        with patch.object(suryadev_extras, "ContinuityFeeder", FakeFeeder), \
             patch.object(suryadev_extras, "AdaptiveResearchWorkers", FakeWorkers), \
             patch.object(suryadev_extras.time, "sleep",
                          side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                suryadev_extras.work_loop(self.lib, 10, False, "unused",
                                         plan_path=plan, refill_minutes=5)
        self.assertEqual(operations_snapshot(self.lib.db, self.root)
                         ["mission_renewal"]["status"], "awaiting_assignment")


if __name__ == "__main__":
    unittest.main()
