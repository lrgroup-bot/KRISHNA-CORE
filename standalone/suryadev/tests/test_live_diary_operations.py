"""Regression tests for local day-wise reports, live worker state and safe API auth."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from suryadev_task_details import diary_day, diary_days, list_tasks, validate_day
from suryadev_liveops import (operations_snapshot, connection_indicators,
                             atomic_json, READER_FILE, worker_note)
from suryadev_bridge import authorized, private_address, load_token


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
