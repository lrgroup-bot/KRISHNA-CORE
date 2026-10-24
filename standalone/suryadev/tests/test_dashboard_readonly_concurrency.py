"""Dashboard API concurrent polls must be read-only and consistently reachable."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from urllib.request import urlopen

from suryadev import Library
from suryadev_extras import DashboardReader, serve


class ReadOnlyDashboardTests(unittest.TestCase):
    def test_read_connection_refuses_writes_and_preserves_existing_jobs(self):
        with tempfile.TemporaryDirectory() as root:
            lib = Library(root)
            try:
                original = lib.add("https://www.python.org/about/")
                reader = DashboardReader(root)
                try:
                    self.assertEqual(reader.stats().get("queued"), 1)
                    with self.assertRaisesRegex(Exception, "readonly|read-only|prohibited"):
                        reader.db.execute("DELETE FROM jobs")
                finally:
                    reader.db.close()
                self.assertEqual(lib.db.execute("SELECT id FROM jobs").fetchone()[0], original)
            finally:
                lib.db.close()

    def test_multiple_counters_share_a_committed_sqlite_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            lib = Library(root)
            try:
                lib.add("https://www.python.org/about/")
                reader = DashboardReader(root)
                try:
                    first = reader.stats()
                    self.assertEqual(first.get("queued"), 1)
                    # An active worker commits another job while this API
                    # response is still reading. Do not mix two DB revisions.
                    lib.add("https://docs.python.org/3/library/asyncio.html")
                    self.assertEqual(reader.stats(), first)
                finally:
                    reader.db.close()
                newer = DashboardReader(root)
                try:
                    self.assertEqual(newer.stats().get("queued"), 2)
                finally:
                    newer.db.close()
            finally:
                lib.db.close()

    def test_concurrent_api_polls_do_not_migrate_schema_or_drop_connections(self):
        with tempfile.TemporaryDirectory() as root:
            lib = Library(root)
            try:
                lib.add("https://www.python.org/about/")
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                thread = threading.Thread(target=serve, args=(lib, port), daemon=True)
                thread.start()
                base = f"http://127.0.0.1:{port}"
                for _ in range(100):
                    try:
                        with urlopen(base + "/health", timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(0.05)
                else:
                    self.fail("Dashboard server did not start")
                paths = (
                    "/api/live", "/api/tasks", "/api/tasks/1",
                    "/api/diary?date=2026-10-23", "/api/books",
                    "/api/operations", "/api/video/review",
                )
                def poll(path):
                    with urlopen(base + path, timeout=10) as response:
                        self.assertEqual(response.status, 200, path)
                        return json.loads(response.read().decode("utf-8"))
                with ThreadPoolExecutor(max_workers=10) as executor:
                    results = list(executor.map(poll, paths * 4))
                self.assertEqual(len(results), len(paths) * 4)
                self.assertEqual(lib.stats()["queued"], 1)
            finally:
                lib.db.close()


if __name__ == "__main__":
    unittest.main()
