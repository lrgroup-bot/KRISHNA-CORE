import sqlite3
import tempfile
import unittest
from pathlib import Path

from krishna_core.gyan_bhandar import GyanBhandarAgent


class MemoryStub:
    def __init__(self, path):
        self.db=sqlite3.connect(str(path))
        self.audit_rows=[]

    def audit(self, action, status, details):
        self.audit_rows.append((action,status,details))


class GyanBhandarRightsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name)
        self.memory=MemoryStub(root/"memory.db")
        self.gyan=GyanBhandarAgent(self.memory,None)
        self.sample=root/"sample.txt"
        self.sample.write_text("lawful knowledge sample",encoding="utf-8")

    def tearDown(self):
        self.memory.db.close()
        self.tmp.cleanup()

    def test_unknown_pmc_rights_block_fulltext_archive(self):
        with self.assertRaises(PermissionError):
            self.gyan.archive_knowledge_file(
                "KRISHNA",self.sample,source_id="pmc",license_id="",
                source_url="https://pmc.ncbi.nlm.nih.gov/articles/example",
            )
        self.assertEqual(self.gyan.archive_status()["files"],0)

    def test_cc_by_open_article_is_archived_with_rights_record(self):
        out=self.gyan.archive_knowledge_file(
            "KRISHNA",self.sample,topic="Open paper",source_id="doaj",
            license_id="CC-BY-4.0",source_url="https://example.org/paper",
            identifier="doi:10.1/example",authors=["A. Researcher"],
            provenance={"retrieved_by":"rishi-test"},
        )
        self.assertTrue(out["rights_verified"])
        self.assertTrue(out["knowledge_source"]["rights"]["attribution_required"])
        status=self.gyan.archive_status()
        self.assertEqual(status["files"],1)
        self.assertEqual(status["rights_verified_knowledge_records"],1)

    def test_openstax_noncommercial_license_blocks_lr_commercial_archive(self):
        with self.assertRaises(PermissionError):
            self.gyan.archive_knowledge_file(
                "LR_Technology",self.sample,source_id="openstax",
                license_id="CC-BY-NC-SA-4.0",commercial_context=True,
            )

    def test_rfc_official_archive_policy_can_archive_without_item_license(self):
        out=self.gyan.archive_knowledge_file(
            "KRISHNA",self.sample,topic="RFC mirror test",source_id="rfc-editor",
            license_id="",
        )
        self.assertTrue(out["rights_verified"])
        self.assertEqual(out["knowledge_source"]["source_policy"]["default_max_mode"],"archive")

    def test_standard_ebooks_cc0_can_archive_despite_read_default(self):
        out=self.gyan.archive_knowledge_file(
            "KRISHNA",self.sample,source_id="standard-ebooks",license_id="CC0-1.0"
        )
        self.assertTrue(out["rights_verified"])
        self.assertTrue(out["knowledge_source"]["rights"]["commercial_allowed"])

    def test_khronos_unknown_spec_rights_do_not_auto_archive(self):
        with self.assertRaises(PermissionError):
            self.gyan.archive_knowledge_file(
                "KRISHNA",self.sample,source_id="khronos",license_id=""
            )

    def test_cc0_training_candidate_gets_checksum_and_can_pass(self):
        out=self.gyan.training_candidate_gate(
            self.sample,source_id="doab",license_id="CC0-1.0"
        )
        self.assertTrue(out["training_allowed"])
        self.assertEqual(len(out["sha256"]),64)

    def test_mit_code_license_does_not_auto_authorize_model_training(self):
        out=self.gyan.training_candidate_gate(
            self.sample,source_id="github",license_id="MIT"
        )
        self.assertFalse(out["training_allowed"])
        self.assertFalse(out["allowed"])
        self.assertIn("keep out",out["next_action"])

    def test_explicit_permission_is_recordable_escape_hatch(self):
        out=self.gyan.archive_knowledge_file(
            "KRISHNA",self.sample,source_id="unregistered-source",license_id="",
            explicit_permission=True,provenance={"permission_record":"contract-123"},
        )
        self.assertTrue(out["rights_verified"])
        self.assertEqual(out["knowledge_source"]["provenance"]["permission_record"],"contract-123")


if __name__ == "__main__":
    unittest.main()
