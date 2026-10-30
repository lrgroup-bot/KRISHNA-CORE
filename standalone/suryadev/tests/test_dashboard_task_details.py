"""Read-only dashboard task inspection regression tests (no network needed)."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from suryadev_task_details import list_tasks, task_detail


class TaskInspectionTests(unittest.TestCase):
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
        now = time.time()
        self.db.execute("INSERT INTO jobs VALUES (1, ?, 'queued', ?, ?, '')",
                        ("https://www.youtube.com/watch?v=abc", now, now))
        self.db.execute("INSERT INTO jobs VALUES (2, ?, 'done', ?, ?, '')",
                        ("https://example.com/guide", now, now))
        self.db.execute("INSERT INTO jobs VALUES (3, ?, 'failed', ?, ?, 'Network blocked')",
                        ("https://example.com/paper.pdf", now, now))
        self.text = b"Relevant extracted source text"
        digest = hashlib.sha256(self.text).hexdigest()
        folder = self.root / "evidence" / digest[:2]
        folder.mkdir(parents=True)
        (folder / (digest + ".txt")).write_bytes(self.text)
        self.digest = digest
        self.db.execute("INSERT INTO findings VALUES (1, 2, ?, ?, ?, ?, ?, ?, ?)",
                        ("https://example.com/guide", digest, "Guide", "Source summary",
                         "Evidence excerpt", now, "ollama:local"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_all_tasks_are_paginated(self):
        first = list_tasks(self.db, offset=0, limit=2)
        self.assertEqual(first["total"], 3)
        self.assertEqual([t["id"] for t in first["tasks"]], [3, 2])
        self.assertTrue(first["has_more"])
        second = list_tasks(self.db, offset=2, limit=2)
        self.assertEqual([t["id"] for t in second["tasks"]], [1])
        self.assertFalse(second["has_more"])

    def test_filter_by_source_and_status(self):
        videos = list_tasks(self.db, kind="youtube")
        self.assertEqual([t["id"] for t in videos["tasks"]], [1])
        failed = list_tasks(self.db, status="failed")
        self.assertEqual(failed["tasks"][0]["kind"], "pdf")
        search = list_tasks(self.db, q="Guide")
        self.assertEqual([t["id"] for t in search["tasks"]], [2])

    def test_evidence_and_checklist_are_truthful(self):
        detail = task_detail(self.db, self.root, 2)
        self.assertEqual(detail["evidence_state"], "verified")
        stages = {stage["name"]: stage["state"] for stage in detail["steps"]}
        self.assertEqual(stages["Source evidence integrity"], "done")
        self.assertEqual(stages["Entire source processed and verified"], "unverified")
        self.assertEqual(stages["BRAHMAGYAN / Rishi acceptance"], "pending")
        self.assertFalse(detail["complete_verified"])
        self.assertEqual(detail["summary"], "Source summary")

    def test_pdf_text_coverage_is_distinct_from_comprehension(self):
        now=time.time()
        source=b"Simple one-page text"
        digest=hashlib.sha256(source).hexdigest()
        folder=self.root/"evidence"/digest[:2]
        folder.mkdir(parents=True,exist_ok=True)
        (folder/(digest+".txt")).write_bytes(source)
        self.db.execute(
            "INSERT INTO jobs VALUES(4, ?, 'done', ?, ?, '')",
            ("https://example.org/sample.pdf",now,now))
        self.db.execute(
            "INSERT INTO findings VALUES(2,4,?,?,?,?,?,?,?)",
            ("https://example.org/sample.pdf",digest,"Sample",
             "extractive preview","Simple one-page text",now,"extractive_preview"))
        self.db.execute(
            "CREATE TABLE job_provenance(job_id INTEGER PRIMARY KEY, report_json TEXT)")
        self.db.execute(
            "INSERT INTO job_provenance VALUES (?, ?)", (4,json.dumps({
                "pages_total":1,"pages_extracted":1,
                "pages_missing_text":[],"extraction_completed":True,
                "full_document_visuals_verified":False})))
        self.db.commit()
        result=task_detail(self.db,self.root,4)
        self.assertEqual(result["evidence_state"],"verified")
        self.assertTrue(result["text_extraction_verified"])
        self.assertFalse(result["visual_coverage_verified"])
        self.assertFalse(result["comprehension_verified"])
        self.assertFalse(result["complete_verified"])
        detail=next(item for item in result["steps"]
                    if item["name"]=="Entire source processed and verified")
        self.assertIn("coverage is recorded separately",detail["detail"])
        text_step=next(item for item in result["steps"]
                       if item["name"]=="PDF page text extraction")
        self.assertEqual(text_step["state"],"done")

    def test_queue_without_finding_is_not_learned(self):
        task = task_detail(self.db, self.root, 1)
        self.assertEqual(task["status"], "queued")
        self.assertEqual(task["evidence_state"], "not_recorded")
        self.assertFalse(task["finding_id"])
        self.assertIn("video", next(x["detail"] for x in task["steps"]
                                    if x["name"] == "Entire source processed and verified").lower())

    def test_missing_or_corrupted_evidence_is_detected(self):
        path = self.root / "evidence" / self.digest[:2] / (self.digest + ".txt")
        path.write_text("changed evidence", encoding="utf-8")
        self.assertEqual(task_detail(self.db, self.root, 2)["evidence_state"], "hash_mismatch")
        path.unlink()
        self.assertEqual(task_detail(self.db, self.root, 2)["evidence_state"], "missing")

    def test_invalid_task_filters_and_unknown_id(self):
        self.assertIsNone(task_detail(self.db, self.root, 999))
        with self.assertRaises(ValueError):
            list_tasks(self.db, status="drop table")
        with self.assertRaises(ValueError):
            task_detail(self.db, self.root, -3)


if __name__ == "__main__":
    unittest.main()
