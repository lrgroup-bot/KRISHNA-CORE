"""Quarantined, zero-cost learning ledger for public engineering lessons.

Stores attributed summaries, not scraped code. Never executes source material,
updates prompts, downloads dependencies or promotes knowledge automatically.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from urllib.parse import urlsplit


class ExternalLearningLedger:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        self.db.execute("""CREATE TABLE IF NOT EXISTS lessons (
            id TEXT PRIMARY KEY, source_url TEXT NOT NULL,
            source_revision TEXT NOT NULL, license_id TEXT NOT NULL,
            summary TEXT NOT NULL, evidence TEXT NOT NULL,
            status TEXT NOT NULL, created_at REAL NOT NULL,
            reviewed_at REAL, reviewer TEXT)""")
        self.db.commit()

    @staticmethod
    def _text(value, name, maximum):
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError(f"invalid {name}")
        return value.strip()

    def capture(self, *, source_url, source_revision, license_id, summary, evidence):
        source_url = self._text(source_url, "source_url", 2048)
        parsed = urlsplit(source_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("source must have a public HTTPS URL without credentials")
        source_revision = self._text(source_revision, "source_revision", 160)
        license_id = self._text(license_id, "license_id", 120)
        summary = self._text(summary, "summary", 8000)
        evidence = self._text(evidence, "evidence", 8000)
        # Provenance and content address: repeated capture is idempotent.
        material = json.dumps([source_url, source_revision, license_id, summary, evidence],
                              ensure_ascii=False, separators=(",", ":"))
        lesson_id = hashlib.sha256(material.encode("utf-8")).hexdigest()
        self.db.execute("""INSERT OR IGNORE INTO lessons
            (id,source_url,source_revision,license_id,summary,evidence,status,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",
            (lesson_id, source_url, source_revision, license_id, summary,
             evidence, "quarantined", time.time()))
        self.db.commit()
        return {"id": lesson_id, "status": self.get(lesson_id)["status"]}

    def get(self, lesson_id):
        row = self.db.execute("""SELECT id,source_url,source_revision,license_id,
            summary,evidence,status,reviewer FROM lessons WHERE id=?""", (lesson_id,)).fetchone()
        if row is None:
            raise KeyError("unknown lesson")
        keys = ("id","source_url","source_revision","license_id","summary","evidence","status","reviewer")
        return dict(zip(keys, row))

    def review(self, lesson_id, *, reviewer, tests_passed=False,
               provenance_verified=False, license_verified=False, approved=False):
        reviewer = self._text(reviewer, "reviewer", 128)
        row = self.get(lesson_id)
        if row["status"] != "quarantined":
            raise ValueError("lesson has already been reviewed")
        accepted = all(x is True for x in
                       (tests_passed, provenance_verified, license_verified, approved))
        status = "approved" if accepted else "rejected"
        self.db.execute("""UPDATE lessons SET status=?, reviewed_at=?, reviewer=?
            WHERE id=? AND status='quarantined'""", (status, time.time(), reviewer, lesson_id))
        self.db.commit()
        return {"id": lesson_id, "status": status}

    def approved(self, limit=50):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("invalid limit")
        rows = self.db.execute("""SELECT id,source_url,source_revision,license_id,summary
            FROM lessons WHERE status='approved' ORDER BY reviewed_at DESC LIMIT ?""",
            (limit,)).fetchall()
        return [dict(zip(("id","source_url","source_revision","license_id","summary"), row))
                for row in rows]

    def close(self):
        self.db.close()
