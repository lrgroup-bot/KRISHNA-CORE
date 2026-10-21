"""Measure actual source processing seconds, not queue age or fictional progress."""
from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from suryadev import Library
from suryadev_liveops import operations_snapshot


class LearningTimingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = Library(self.tmp.name)

    def tearDown(self):
        self.lib.db.close()
        self.tmp.cleanup()

    def add(self, url):
        with patch("suryadev.validate_url", return_value=None):
            return self.lib.add(url)

    def test_all_text_segments_and_elapsed_are_measured(self):
        job = self.add("https://example.org/learn")
        source = "A" * 19001
        receipt = {"kind":"website",
                   "coverage_status":"garudanetra_rendered_text_unverified"}
        with patch("suryadev_ingest.ingest_source",
                   return_value=("Learning", source, receipt)), patch(
                   "suryadev.summarize", return_value="Segment checked") as model:
            result = self.lib.run_next(use_ollama=True, model="test-model")
        self.assertEqual(result["status"], "done")
        self.assertEqual(model.call_count, 3)
        row = self.lib.db.execute(
            "SELECT kind,acquisition_seconds,summary_phase_seconds,"
            "elapsed_seconds,outcome FROM job_timing WHERE job_id=?", (job,)
        ).fetchone()
        self.assertEqual(row[0], "website")
        self.assertGreaterEqual(row[1], 0)
        self.assertGreaterEqual(row[2], 0)
        self.assertGreaterEqual(row[3], row[1])
        self.assertEqual(row[4], "done")
        report = operations_snapshot(self.lib.db, self.tmp.name)["timing"]
        self.assertEqual(report["measured_jobs"], 1)
        self.assertEqual(report["historical_jobs_unmeasured"], 0)
        self.assertEqual(report["by_source"]["website"]["done"]["jobs"], 1)
        self.assertEqual(report["recent"][0]["job_id"], job)
        self.assertEqual(self.lib.db.execute(
            "SELECT summary_method FROM findings WHERE job_id=?", (job,)
        ).fetchone()[0], "ollama_chunked:test-model")

    def test_failed_job_still_records_actual_elapsed(self):
        job = self.add("https://example.org/failure.pdf")
        with patch("suryadev_ingest.ingest_source",
                   side_effect=ValueError("PDF needs OCR")):
            result = self.lib.run_next(use_ollama=False)
        self.assertEqual(result["status"], "failed")
        row = self.lib.db.execute(
            "SELECT kind,acquisition_seconds,summary_phase_seconds,"
            "elapsed_seconds,outcome FROM job_timing WHERE job_id=?", (job,)
        ).fetchone()
        self.assertEqual(row[0], "pdf")
        self.assertIsNone(row[1])
        self.assertIsNone(row[2])
        self.assertGreaterEqual(row[3], 0)
        self.assertEqual(row[4], "failed")
        report = operations_snapshot(self.lib.db, self.tmp.name)["timing"]
        self.assertEqual(report["by_source"]["pdf"]["failed"]["jobs"], 1)

    def test_preview_only_is_not_misrepresented_as_ai_learning(self):
        job = self.add("https://www.youtube.com/watch?v=abcdefghijk")
        receipt = {"kind":"youtube", "coverage_status":"caption_timeline_only_unverified",
                   "full_video_visuals_verified":False}
        with patch("suryadev_ingest.ingest_source",
                   return_value=("Captions", "spoken words"*250, receipt)), patch(
                   "suryadev.summarize", side_effect=AssertionError("must not call model")):
            result = self.lib.run_next(use_ollama=False)
        self.assertEqual(result["status"], "done")
        method = self.lib.db.execute(
            "SELECT summary_method FROM findings WHERE job_id=?", (job,)
        ).fetchone()[0]
        self.assertEqual(method, "extractive_preview")
        times = operations_snapshot(self.lib.db, self.tmp.name)["timing"]
        self.assertEqual(times["by_source"]["youtube"]["done"]["jobs"], 1)


if __name__ == "__main__":
    unittest.main()
