import tempfile
from contextlib import closing
import unittest
from pathlib import Path
from suryadev import Library
from suryadev_evidence import save_evidence, verify_evidence, backup_database

class EvidenceTests(unittest.TestCase):
    def test_save_deduplicates_and_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            a = save_evidence(d, "a complete source", source="https://example.org")
            b = save_evidence(d, "a complete source", source="https://example.org")
            self.assertEqual(a["sha256"], b["sha256"])
            self.assertEqual(verify_evidence(d), {"checked": 1, "corrupt": []})
            p = Path(d) / a["path"]
            p.write_text("tampered", encoding="utf-8")
            self.assertEqual(len(verify_evidence(d)["corrupt"]), 1)

    def test_online_backup(self):
        with tempfile.TemporaryDirectory() as d:
            lib = Library(d)
            lib.db.execute("INSERT INTO jobs(url,status,created,updated) VALUES (?,?,?,?)",
                           ("https://example.org", "done", 1, 1))
            lib.db.commit()
            destination = Path(d) / "backup.sqlite3"
            result = backup_database(d, destination)
            self.assertEqual(result["integrity"], "ok")
            import sqlite3
            with closing(sqlite3.connect(destination)) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
            lib.db.close()

if __name__ == "__main__":
    unittest.main()
