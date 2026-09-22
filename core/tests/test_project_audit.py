import tempfile
import unittest
from pathlib import Path

from krishna_core.project_audit import KrishnaProjectAudit


class ProjectAuditTests(unittest.TestCase):
    def test_full_source_audit_has_no_contract_failures(self):
        repo=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as td:
            report=KrishnaProjectAudit(repo,td).run()
        failures=[x for x in report["findings"] if x["status"]=="FAIL"]
        self.assertEqual(failures,[],failures)
        self.assertGreaterEqual(len(report["workers"]),9)
        self.assertGreaterEqual(report["counts"]["PASS"],8)

    def test_ui_auditor_covers_inputs_handlers_and_routes(self):
        repo=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as td:
            audit=KrishnaProjectAudit(repo,td)
            audit.audit_ui()
        names={x.name:x for x in audit.findings}
        for name in ("textbox/select wiring","inline function handlers","UI to Core API wiring","DOM id references"):
            self.assertEqual(names[name].status,"PASS",names[name].public())


if __name__=="__main__":
    unittest.main()
