"""Regression tests for worker exclusivity and atomic queue claims."""
import tempfile
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_lock import worker_lock

class WorkerSafetyTests(unittest.TestCase):
    def test_exclusive_lock(self):
        with tempfile.TemporaryDirectory() as root:
            with worker_lock(root):
                with self.assertRaises(RuntimeError):
                    with worker_lock(root):
                        pass
            with worker_lock(root):
                pass

    def test_two_libraries_cannot_claim_same_job(self):
        with tempfile.TemporaryDirectory() as root:
            a = Library(root)
            b = Library(root)
            try:
                a.db.execute("INSERT INTO jobs(url,status,created,updated) VALUES (?,?,?,?)",
                             ("https://example.org", "queued", 1, 1))
                a.db.commit()
                with patch("suryadev_garudanetra.render_website", return_value=("Example", "Research text", {"kind":"website","coverage_status":"garudanetra_rendered_text_unverified","browser_tab_opened":True,"full_rendered_page_verified":False})):
                    self.assertEqual(a.run_next(use_ollama=False)["status"], "done")
                    self.assertIsNone(b.run_next(use_ollama=False))
                self.assertEqual(a.db.execute("SELECT count(*) FROM findings").fetchone()[0], 1)
            finally:
                a.db.close()
                b.db.close()

if __name__ == "__main__":
    unittest.main()
