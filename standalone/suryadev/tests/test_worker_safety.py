"""Regression tests for worker exclusivity and atomic queue claims."""
import tempfile
import time
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

    def test_retry_failed_youtube_is_operator_controlled_and_preserves_error_history(self):
        with tempfile.TemporaryDirectory() as root:
            lib = Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    job_id=lib.add("https://www.youtube.com/watch?v=abcdefghijk")
                now=time.time()
                with lib.db:
                    lib.db.execute("UPDATE jobs SET status='failed', error=?,updated=? WHERE id=?",
                        ("RuntimeError: HTTP Error 429: Too Many Requests", now,job_id))
                with worker_lock(root):
                    with self.assertRaisesRegex(RuntimeError,"cooldown"):
                        lib.retry_failed(job_id)
                self.assertEqual(lib.stats()["failed"],1)
                with lib.db:
                    lib.db.execute("UPDATE jobs SET updated=? WHERE id=?",(now-3700,job_id))
                with worker_lock(root):
                    result=lib.retry_failed(job_id)
                self.assertEqual(result["status"],"queued")
                self.assertEqual(lib.stats()["queued"],1)
                history=lib.db.execute(
                    "SELECT previous_error FROM job_attempt_history WHERE job_id=?",
                    (job_id,)).fetchone()
                self.assertIn("429",history[0])
                with worker_lock(root):
                    with self.assertRaisesRegex(ValueError,"Only failed"):
                        lib.retry_failed(job_id)
            finally:
                lib.db.close()

    def test_manual_retry_refuses_to_override_persistent_youtube_cooldown(self):
        from suryadev_parallel import record_youtube_rate_limit
        with tempfile.TemporaryDirectory() as root:
            lib=Library(root)
            try:
                with patch("suryadev.validate_url",return_value=None):
                    job_id=lib.add("https://www.youtube.com/watch?v=abcdefghijk")
                with lib.db:
                    lib.db.execute("UPDATE jobs SET status='failed',error=?,updated=? WHERE id=?",
                                   ("Other download failure",time.time()-3800,job_id))
                record_youtube_rate_limit(root)
                with worker_lock(root):
                    with self.assertRaisesRegex(RuntimeError,"cooldown"):
                        lib.retry_failed(job_id)
                self.assertEqual(lib.stats()["failed"],1)
            finally:
                lib.db.close()

if __name__ == "__main__":
    unittest.main()
