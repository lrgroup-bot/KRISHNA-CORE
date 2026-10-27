"""Regression checks: explicit reset archives evidence, never deletes history."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from suryadev_learning_reset import (
    CONFIRMATION, archive_and_reset, _assert_stopped,
)


def setup_data(parent: Path) -> Path:
    data = parent / "data"
    data.mkdir()
    (data / "fresh-workspace.json").write_text(json.dumps({
        "schema":"suryadev.fresh-workspace.v1", "created_at":"test"
    }), encoding="utf-8")
    (data / "video-trial-selection.json").write_text(
        '{"schema":"suryadev.video-trial-selection.v1","target":3,"job_ids":["prior"]}',
        encoding="utf-8")
    (data / "book-learning.sqlite3").write_bytes(b"do-not-delete")
    (data / "learning-plan.json").write_text(
        '{"approved_urls":["https://www.youtube.com/watch?v=abcdefghijk"]}',
        encoding="utf-8")
    (data / "video-observer-attempts.json").write_text(
        '{"job_ids":["old-attempt"]}',encoding="utf-8")
    return data


class StudyResetTests(unittest.TestCase):
    def test_confirmation_required_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            data=setup_data(Path(temp))
            with self.assertRaises(ValueError):
                archive_and_reset(data, confirm="", inspect_ports=False)
            self.assertTrue((data/"book-learning.sqlite3").exists())
            self.assertEqual(len(list(Path(temp).iterdir())),1)

    def test_archive_clears_all_active_learning_but_retains_prior_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            data=setup_data(Path(temp))
            result=archive_and_reset(data, confirm=CONFIRMATION,
                                     inspect_ports=False)
            self.assertTrue(result["ok"])
            archive=Path(result["archive"])
            self.assertTrue(archive.is_dir())
            self.assertEqual((archive/"book-learning.sqlite3").read_bytes(),
                             b"do-not-delete")
            self.assertTrue((archive/"video-trial-selection.json").exists())
            self.assertTrue((archive/"video-observer-attempts.json").exists())
            self.assertTrue((archive/"learning-plan.json").exists())
            self.assertFalse((data/"book-learning.sqlite3").exists())
            self.assertFalse((data/"learning-plan.json").exists())
            self.assertFalse((data/"video-observer-attempts.json").exists())
            self.assertFalse((data/"video-trial-selection.json").exists())
            new=json.loads((data/"fresh-workspace.json").read_text())
            self.assertEqual(new["schema"],"suryadev.fresh-workspace.v1")
            self.assertFalse(result["old_book_progress_carried_over"])
            self.assertFalse(result["approvals_carried_over"])

    def test_refuses_unmarked_directory_and_worker_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            data=setup_data(Path(temp))
            (data/"fresh-workspace.json").unlink()
            with self.assertRaises(ValueError):
                archive_and_reset(data,confirm=CONFIRMATION,inspect_ports=False)
            self.assertTrue((data/"book-learning.sqlite3").exists())

    def test_running_dashboard_refuses_before_archiving(self):
        with tempfile.TemporaryDirectory() as temp:
            data=setup_data(Path(temp))
            with patch("suryadev_learning_reset._assert_stopped",
                       side_effect=RuntimeError("worker active")):
                with self.assertRaises(RuntimeError):
                    archive_and_reset(data,confirm=CONFIRMATION)
            self.assertTrue((data/"book-learning.sqlite3").exists())

    def test_missing_directory_never_created_on_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)/"missing"
            with self.assertRaises(ValueError):
                archive_and_reset(data, confirm=CONFIRMATION,inspect_ports=False)
            self.assertFalse(data.exists())


if __name__ == "__main__":
    unittest.main()
