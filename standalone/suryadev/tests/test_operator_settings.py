"""Local operator UI settings, storage migration and cleanup safety contracts."""
from pathlib import Path
import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from suryadev import Library
from suryadev_settings import (validate_core, diagnose_core, save_core, read_settings,
                               write_settings)
from suryadev_storage import inspect_storage, migrate_storage
from suryadev_cleanup import stage_extracted_text, cleanup_completed
from suryadev_evidence import save_evidence
from suryadev_operator_api import settings_snapshot, handle_operator_action


class ServerSettingsTests(unittest.TestCase):
    def test_private_ip_validation(self):
        self.assertEqual(validate_core("192.168.0.100", 8766),
                         ("192.168.0.100", 8766))
        for ip in ("8.8.8.8", "0.0.0.0", "http://192.168.0.100",
                   "192.168.0.100/health", "notanip", "169.254.1.1",
                   "224.0.0.1", ""):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                validate_core(ip, 8766)
        with self.assertRaises(ValueError):
            validate_core("192.168.0.100", 0)
        with self.assertRaises(ValueError):
            validate_core("192.168.0.100", 65536)

    def test_server_ip_persists_without_pairing(self):
        with tempfile.TemporaryDirectory() as root:
            receipt = save_core(root, "192.168.0.100", 8766)
            self.assertFalse(receipt["paired"])
            self.assertFalse(receipt["identity_verified"])
            self.assertEqual(read_settings(root)["server"]["ip"], "192.168.0.100")
            snapshot = settings_snapshot(root)
            self.assertFalse(snapshot["paired"])

    @patch("suryadev_settings.build_opener")
    @patch("suryadev_settings.socket.create_connection")
    def test_core_health_is_not_identity_verification(self, tcp, opener):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"instance_id":"candidate-only","status":"ok"}'
        opener.return_value.open.return_value.__enter__.return_value = response
        result = diagnose_core("192.168.0.100", 8766)
        self.assertTrue(result["tcp_open"])
        self.assertTrue(result["health_reachable"])
        self.assertEqual(result["reported_instance_id"], "candidate-only")
        self.assertFalse(result["paired"])
        self.assertFalse(result["authenticated"])
        self.assertFalse(result["identity_verified"])

    @patch("suryadev_settings.socket.create_connection", side_effect=OSError("blocked"))
    def test_unreachable_core_does_not_claim_success(self, tcp):
        result = diagnose_core("192.168.0.100")
        self.assertFalse(result["tcp_open"])
        self.assertFalse(result["health_reachable"])
        self.assertFalse(result["paired"])


class StorageAndCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "active"
        self.root.mkdir()
        self.lib = Library(self.root)

    def tearDown(self):
        self.lib.db.close()
        self.tmp.cleanup()

    def _completed_job(self, content="Archived source evidence"):
        sha = save_evidence(self.root, content, source="https://example.com", kind="website")["sha256"]
        with self.lib.db:
            cur = self.lib.db.execute(
                "INSERT INTO jobs(url,status,created,updated,error) VALUES (?, ?,1,2,'')",
                ("https://example.com", "done"))
            job_id = cur.lastrowid
            self.lib.db.execute(
                "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created,summary_method)"
                " VALUES (?,?,?,?,?,?,3,?)",
                (job_id, "https://example.com", sha, "Test", "Summary",
                 content, "extractive_preview"))
        return job_id, sha

    def test_space_preview_and_protected_nested_destination(self):
        with patch("suryadev_storage.MIN_FREE_BYTES",0), patch("suryadev_storage.SAFETY_BYTES",0):
            report = inspect_storage(self.root, str(self.base / "new-data"))
        self.assertTrue(report["ready_to_migrate"])
        self.assertEqual(report["current_root"], str(self.root.resolve()))
        self.assertGreaterEqual(report["free_bytes"],0)
        with self.assertRaises(ValueError):
            inspect_storage(self.root, str(self.root / "inside"))
        with self.assertRaises(ValueError):
            inspect_storage(self.root, str(self.base))

    def test_verified_copy_keeps_original_and_requires_restart(self):
        job_id, digest = self._completed_job()
        source_db = self.root / "suryadev.sqlite3"
        copy_path = self.base / "new-research"
        with patch("suryadev_storage.MIN_FREE_BYTES",0), patch("suryadev_storage.SAFETY_BYTES",0):
            result = migrate_storage(self.root, str(copy_path))
        self.assertTrue(result["restart_required"])
        self.assertTrue(source_db.is_file())
        self.assertTrue((copy_path / "suryadev.sqlite3").is_file())
        self.assertTrue((copy_path / "evidence" / digest[:2] / (digest+".txt")).is_file())
        self.assertTrue((self.root / "evidence" / digest[:2] / (digest+".txt")).is_file())
        with closing(sqlite3.connect(copy_path / "suryadev.sqlite3")) as moved:
            self.assertEqual(moved.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 1)
            self.assertEqual(moved.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(read_settings(self.root)["pending_data_root"], str(copy_path.resolve()))
        self.assertEqual(read_settings(copy_path)["pending_data_root"], "")

    def test_refuse_nonempty_destination(self):
        self._completed_job()
        bad = self.base / "has-files"
        bad.mkdir()
        (bad / "keep.txt").write_text("user file")
        with patch("suryadev_storage.MIN_FREE_BYTES",0), patch("suryadev_storage.SAFETY_BYTES",0):
            with self.assertRaises(ValueError):
                migrate_storage(self.root, str(bad))
        self.assertEqual((bad / "keep.txt").read_text(), "user file")

    def test_cleanup_only_owned_staged_success_after_hash_validation(self):
        job_id, digest = self._completed_job()
        content = "Archived source evidence"
        self.assertEqual(stage_extracted_text(self.root, job_id, content), digest)
        user_original = self.root / "original-video.mp4"
        user_original.write_bytes(b"user-asset")
        staged = self.root / "staging" / "jobs" / str(job_id) / "source.txt"
        before = cleanup_completed(self.lib.db, self.root, dry_run=True)
        self.assertEqual(before["eligible_jobs"], 1)
        self.assertTrue(staged.exists())
        after = cleanup_completed(self.lib.db, self.root)
        self.assertEqual(after["deleted_jobs"], 1)
        self.assertFalse(staged.exists())
        self.assertEqual(user_original.read_bytes(), b"user-asset")
        self.assertTrue((self.root / "evidence" / digest[:2] / (digest+".txt")).is_file())
        self.assertTrue((self.root / "suryadev.sqlite3").is_file())

    def test_failed_jobs_and_missing_evidence_never_cleaned(self):
        job_id, digest = self._completed_job()
        staged = self.root / "staging" / "jobs" / str(job_id) / "source.txt"
        stage_extracted_text(self.root, job_id, "Archived source evidence")
        with self.lib.db:
            self.lib.db.execute("UPDATE jobs SET status='failed' WHERE id=?", (job_id,))
        self.assertEqual(cleanup_completed(self.lib.db, self.root)["deleted_jobs"], 0)
        self.assertTrue(staged.exists())
        with self.lib.db:
            self.lib.db.execute("UPDATE jobs SET status='done' WHERE id=?", (job_id,))
        (self.root / "evidence" / digest[:2] / (digest+".txt")).unlink()
        self.assertEqual(cleanup_completed(self.lib.db, self.root)["deleted_jobs"], 0)
        self.assertTrue(staged.exists())

    def test_cleanup_policy_can_disable_automatic_removal(self):
        job_id, _ = self._completed_job()
        stage_extracted_text(self.root, job_id, "Archived source evidence")
        saved = read_settings(self.root)
        saved["cleanup"] = {"enabled":False,"retention_hours":0}
        write_settings(self.root, saved)
        self.assertFalse(cleanup_completed(self.lib.db, self.root)["enabled"])
        self.assertTrue((self.root / "staging" / "jobs" / str(job_id) / "source.txt").exists())

    def test_actions_validate_confirmation_and_retention(self):
        with self.assertRaises(ValueError):
            handle_operator_action(self.root, "/api/operator/storage/migrate",
                                   {"path":str(self.base / "new"),"confirm":"YES"})
        with self.assertRaises(ValueError):
            handle_operator_action(self.root, "/api/operator/cleanup/save",
                                   {"enabled":True,"retention_hours":-1})
        result = handle_operator_action(self.root, "/api/operator/cleanup/save",
                                        {"enabled":True,"retention_hours":24})
        self.assertEqual(result["cleanup"]["retention_hours"],24)


class SettingsUiWiringTests(unittest.TestCase):
    def test_sidebar_menus_popups_and_js_actions_exist(self):
        folder = Path(__file__).resolve().parents[1]
        html = (folder / "dashboard.html").read_text(encoding="utf-8")
        script = (folder / "dashboard-settings.js").read_text(encoding="utf-8")
        css = (folder / "dashboard-settings.css").read_text(encoding="utf-8")
        for key in ("open-server-settings","open-storage-settings","server-settings-dialog",
                    "storage-settings-dialog","server-ip","server-port","diagnose-server",
                    "storage-location","browse-storage","check-storage",
                    "migrate-storage","cleanup-enabled","cleanup-hours",
                    "preview-cleanup","run-cleanup"):
            with self.subTest(key=key):
                self.assertIn('id="' + key + '"', html)
                self.assertIn('"' + key + '"', script)
        self.assertIn('src="/dashboard-settings.js"', html)
        self.assertIn('href="/dashboard-settings.css"', html)
        self.assertIn(".settings-dialog", css)
        extras = (folder / "suryadev_extras.py").read_text(encoding="utf-8")
        self.assertIn('"/api/operator/settings"', extras)
        self.assertIn('def do_POST(self):', extras)
        self.assertIn('X-SURYADEV-CSRF', extras)


if __name__ == "__main__":
    unittest.main()
