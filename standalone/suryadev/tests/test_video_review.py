"""Checks for local, explicitly approved GitHub-UI browser-video jobs."""
import json
from pathlib import Path
import tempfile
import unittest
from suryadev_video_review import VideoReview, validate_job


class VideoReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.url = "https://www.youtube.com/watch?v=a1b2c3"
        (self.root / "learning-plan.json").write_text(
            json.dumps({"approved_urls": [self.url]}), encoding="utf-8")
        self.review = VideoReview(self.root, self.root)
        self.job = {"schema": "krishna.suryadev.job.v1", "job_id": "study_01",
                    "kind": "video_research", "target": self.url,
                    "constraints": {"duration_seconds": 60}}

    def test_approval_exact_url_and_query_preserved(self):
        self.review.import_job(self.job)
        result = self.review.snapshot()
        self.assertEqual(result["jobs"][0]["target"], self.url)
        self.assertEqual(result["jobs"][0]["status"], "QUEUED_FOR_REVIEW")

    def test_duplicate_does_not_overwrite(self):
        self.review.import_job(self.job)
        self.assertTrue(self.review.import_job(self.job)["duplicate"])
        with self.assertRaisesRegex(ValueError, "different contents"):
            self.review.import_job({**self.job, "constraints": {"duration_seconds": 600}})

    def test_disallowed_urls_and_private_targets(self):
        for url in ["http://127.0.0.1/", "https://192.168.1.2/",
                    "https://localhost/", "https://example.com/",
                    "https://www.youtube.com/watch?v=other"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_job({**self.job, "target": url}, self.root / "learning-plan.json")

    def test_requires_selected_hash_and_explicit_approval(self):
        result = self.review.import_job(self.job)
        with self.assertRaisesRegex(ValueError, "Explicit approval"):
            self.review.run_job("study_01", False, result["sha256"])
        with self.assertRaisesRegex(ValueError, "changed"):
            self.review.run_job("study_01", True, "wrong")
        with self.assertRaisesRegex(RuntimeError, "not installed"):
            self.review.run_job("study_01", True, result["sha256"])

    def test_duration_and_id_bounds(self):
        with self.assertRaises(ValueError):
            validate_job({**self.job, "constraints": {"duration_seconds": 21600}},
                         self.root / "learning-plan.json")
        with self.assertRaises(ValueError):
            validate_job({**self.job, "job_id": "../escape"}, self.root / "learning-plan.json")


if __name__ == "__main__":
    unittest.main()
