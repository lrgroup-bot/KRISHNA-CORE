"""Regression tests for local day-wise reports, live worker state and safe API auth."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from suryadev_task_details import diary_day, diary_days, list_tasks, validate_day, task_detail
from suryadev_liveops import (operations_snapshot, connection_indicators,
                             atomic_json, READER_FILE, worker_note)
from suryadev_bridge import authorized, private_address, load_token
from suryadev_core_reader import validate_endpoint


class DiaryAndOperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE jobs (id INTEGER PRIMARY KEY, url TEXT NOT NULL, status TEXT NOT NULL,
              created REAL NOT NULL, updated REAL NOT NULL, error TEXT NOT NULL DEFAULT '');
            CREATE TABLE findings (id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL,
              url TEXT NOT NULL, sha256 TEXT NOT NULL, title TEXT NOT NULL,
              summary TEXT NOT NULL, excerpt TEXT NOT NULL, created REAL NOT NULL,
              summary_method TEXT NOT NULL);
        """)
        today = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        self.today = today.date().isoformat()
        self.yesterday = yesterday.date().isoformat()
        self.db.execute("INSERT INTO jobs VALUES (1, ?, 'done', ?, ?, '')",
                        ("https://example.com/page", yesterday.timestamp(), today.timestamp()))
        self.db.execute("INSERT INTO jobs VALUES (2, ?, 'failed', ?, ?, 'Failed')",
                        ("https://www.youtube.com/watch?v=abc", today.timestamp(), today.timestamp()))
        self.db.execute("INSERT INTO findings VALUES (1, 1, ?, ?, ?, ?, ?, ?, ?)",
                        ("https://example.com/page", "f"*64, "Yesterday read",
                         "Evidence", "Excerpt", today.timestamp(), "ollama:local"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_daily_activity_counts_distinguish_created_and_finished(self):
        today = diary_day(self.db, self.today)
        self.assertEqual(today["assignments"], 1)
        self.assertEqual(today["completed"], 1)
        self.assertEqual(today["failed"], 1)
        self.assertEqual(today["findings"], 1)
        earlier = diary_day(self.db, self.yesterday)
        self.assertEqual(earlier["assignments"], 1)
        self.assertEqual(earlier["completed"], 0)
        self.assertEqual(earlier["findings"], 0)
        self.assertEqual(diary_days(self.db)[0]["date"], self.today)

    def test_date_filter_includes_assignment_outcomes_and_findings(self):
        tasks = list_tasks(self.db, day=self.today)
        self.assertEqual({t["id"] for t in tasks["tasks"]}, {1,2})
        earlier = list_tasks(self.db, day=self.yesterday)
        self.assertEqual([t["id"] for t in earlier["tasks"]], [1])
        self.assertEqual(list_tasks(self.db, day="2000-01-01")["total"], 0)

    def test_invalid_calendar_date_is_rejected(self):
        for value in ["2026-02-29", "2026-2-1", "yesterday", "2026-10-21;drop",
                      "2026-13-01", ""]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_day(value)
        self.assertEqual(validate_day("2024-02-29"), "2024-02-29")

    def test_worker_status_is_factual_and_reports_order(self):
        initial = operations_snapshot(self.db, self.root)
        self.assertEqual(initial["worker"]["state"], "offline")
        self.assertIsNone(initial["worker"]["next_check_at"])
        self.assertEqual(initial["running_total"], 0)
        now = time.time()
        self.db.execute("UPDATE jobs SET status='queued' WHERE id=2")
        worker_note(self.root, "idle", 60, next_check_at=now+60)
        status = operations_snapshot(self.db, self.root)
        self.assertEqual(status["worker"]["state"], "idle")
        self.assertEqual(status["upcoming"][0]["id"], 2)
        self.assertIsNone(status["upcoming"][0]["scheduled_at"])
        self.assertEqual(status["by_source"]["youtube"]["queued"], 1)

    def test_offline_dashboard_reports_real_hardware_without_starting_worker(self):
        reading = {"available":True, "cpu_percent":15, "ram_percent":47,
                   "ram_total_gb":15.73,"ram_used_gb":7.39,
                   "disk_free_gb":192.14, "disk_percent":31.2,
                   "gpu":{"available":False}}
        with patch("suryadev_resources.snapshot", return_value=reading):
            view = operations_snapshot(self.db, self.root)
        self.assertEqual(view["worker"]["state"], "offline")
        self.assertFalse(view["worker_running"])
        self.assertEqual(view["capacity"]["max_total"],0)
        self.assertEqual(view["hardware"]["cpu_percent"],15)
        self.assertEqual(view["hardware"]["ram_percent"],47)
        self.assertGreater(view["hardware"]["potential_total_if_worker_started"],0)
        self.assertFalse(view["research_plan"]["present"])
        self.assertFalse((self.root / "learning-plan.json").exists())
        self.assertFalse((self.root / "worker-runtime.json").exists())

    def test_idle_worker_capacity_sample_survives_60_second_interval(self):
        now = time.time()
        worker_note(self.root, "idle", 60, "Next refresh in one minute",
                    next_check_at=now + 60)
        atomic_json(self.root, "capacity-runtime.json", {
            "sample_time": now-48, "state":"idle",
            "safe":True,"max_total":3,
            "limits":{"website":2,"youtube":1,"pdf":1},
            "cpu_percent":5,"ram_percent":47,
        })
        view = operations_snapshot(self.db, self.root)
        self.assertTrue(view["worker_running"])
        self.assertEqual(view["capacity"]["max_total"],3)
        self.assertEqual(view["hardware"]["source"],"worker_scheduler")
        worker_note(self.root, "stopped", 60, "Worker stopped")
        with patch("suryadev_resources.snapshot", return_value={
            "available":False,"reason":"no psutil installed"}):
            stopped = operations_snapshot(self.db, self.root)
        self.assertFalse(stopped["worker_running"])
        self.assertEqual(stopped["capacity"]["max_total"],0)
        self.assertEqual(stopped["hardware"]["source"],"dashboard_read_only")

    def test_queued_youtube_reports_worker_offline_without_false_processing(self):
        self.db.execute("UPDATE jobs SET status='queued' WHERE id=2")
        details = task_detail(self.db, self.root, 2)
        self.assertEqual(details["status"], "queued")
        self.assertIsNone(details["finding_id"])
        self.assertEqual(details["queue_diagnosis"]["worker_state"], "offline")
        self.assertIn("No recent", details["queue_diagnosis"]["message"])
        execution = next(x for x in details["steps"] if x["name"] == "Worker execution")
        self.assertEqual(execution["state"], "pending")
        self.assertIn("read-only", execution["detail"])

    def test_queued_task_state_distinguishes_heartbeat_and_paused_worker(self):
        self.db.execute("UPDATE jobs SET status='queued' WHERE id=2")
        worker_note(self.root, "idle", 10, "No pending threads")
        current = task_detail(self.db, self.root, 2)
        self.assertEqual(current["queue_diagnosis"]["worker_state"], "idle")
        self.assertIn("heartbeat present", current["queue_diagnosis"]["message"])
        worker_note(self.root, "paused", 10, "RAM above 85%")
        paused = task_detail(self.db, self.root, 2)
        self.assertEqual(paused["queue_diagnosis"]["worker_state"], "paused")
        self.assertIn("RAM above 85%", paused["queue_diagnosis"]["message"])
        worker_note(self.root, "stopped", 10, "Stopped by operator")
        stopped = task_detail(self.db, self.root, 2)
        self.assertEqual(stopped["queue_diagnosis"]["worker_state"], "stopped")
        atomic_json(self.root, "worker-runtime.json",
                    {"state":"busy", "interval_seconds":10,
                     "heartbeat_at":time.time()-400})
        old = task_detail(self.db, self.root, 2)
        self.assertEqual(old["queue_diagnosis"]["worker_state"], "offline")

    def test_queued_detail_frontend_does_not_call_unprocessed_sources_legacy(self):
        js = (Path(__file__).resolve().parents[1] / "dashboard.js").read_text(encoding="utf-8")
        self.assertIn('task.queue_diagnosis?.message', js)
        self.assertIn("Not processed yet. Evidence and source coverage", js)

    def test_connection_leds_fail_closed(self):
        self.assertFalse(connection_indicators(self.root)["krishna"]["connected"])
        atomic_json(self.root, READER_FILE,
                    {"type": "authenticated_tls_read", "last_read_at": time.time()})
        result = connection_indicators(self.root)
        self.assertFalse(result["krishna"]["connected"])
        self.assertTrue(result["krishna"]["reader_active"])
        self.assertFalse(result["brahmagyan"]["connected"])
        self.assertFalse(result["rishi"]["connected"])


class BridgeAuthTests(unittest.TestCase):
    def test_rejects_unauthorized_or_missing_bearer(self):
        secret = "r"*64
        self.assertFalse(authorized(None, secret))
        self.assertFalse(authorized("Bearer wrong", secret))
        self.assertFalse(authorized("Token " + secret, secret))
        self.assertTrue(authorized("Bearer " + secret, secret))

    def test_explicit_private_addresses_only(self):
        self.assertEqual(private_address("127.0.0.1"), "127.0.0.1")
        self.assertEqual(private_address("192.168.1.40"), "192.168.1.40")
        for address in ("0.0.0.0", "8.8.8.8", "2001:4860:4860::8888"):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    private_address(address)

    def test_core_reader_rejects_unpinned_and_public_endpoints(self):
        fingerprint = "a" * 64
        url, pin = validate_endpoint("https://192.168.1.50:8770/api/operations", fingerprint)
        self.assertEqual(url.hostname, "192.168.1.50")
        self.assertEqual(pin, fingerprint)
        for endpoint in ("http://192.168.1.50:8770/api/live",
                         "https://8.8.8.8/api/live",
                         "https://192.168.1.50/control/start",
                         "https://me:pass@192.168.1.50/api/live"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    validate_endpoint(endpoint, fingerprint)
        with self.assertRaises(ValueError):
            validate_endpoint("https://192.168.1.50/api/live", "fake-pin")

    def test_token_from_file_without_logging_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret.txt"
            path.write_text("a"*64, encoding="ascii")
            self.assertEqual(len(load_token(path)),64)
            path.write_text("short", encoding="ascii")
            with self.assertRaises(ValueError):
                load_token(path)


if __name__ == "__main__":
    unittest.main()
