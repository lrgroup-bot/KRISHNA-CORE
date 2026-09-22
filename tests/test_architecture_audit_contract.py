from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"AUDIT_KRISHNA_ARCHITECTURE.py"

class ArchitectureAuditContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location("krishna_arch_audit",SCRIPT)
        cls.mod=importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(cls.mod)

    def test_report_is_non_destructive_and_canonical(self):
        report=self.mod.audit()
        self.assertEqual(report["schema"],"krishna.architecture-audit.v1")
        self.assertEqual(report["canonical_core"],"core/krishna_core")
        self.assertGreater(report["module_count"],50)
        self.assertTrue(report["policy"]["orphan_is_candidate_only"])
        self.assertTrue(report["policy"]["delete_requires_dynamic_packaging_runtime_check"])
        for row in report["orphan_candidates"]:
            self.assertFalse(row["deletion_safe"])

    def test_compatibility_copies_never_become_authority(self):
        report=self.mod.audit()
        self.assertTrue(report["policy"]["compatibility_copy_is_not_authority"])
        for row in report["compatibility_copies"]:
            self.assertIn(row["status"],{"identical_copy","drifted_copy","copy_only"})

if __name__=="__main__":
    unittest.main()
