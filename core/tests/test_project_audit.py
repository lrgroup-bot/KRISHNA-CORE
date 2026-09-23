import os
import tempfile
import unittest
from pathlib import Path

from krishna_core.project_audit import KrishnaProjectAudit


def repository_root():
    configured=str(os.environ.get("KRISHNA_SOURCE_ROOT") or "").strip()
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[2]


class ProjectAuditTests(unittest.TestCase):
    def test_full_source_audit_has_no_contract_failures(self):
        repo=repository_root()
        with tempfile.TemporaryDirectory() as td:
            report=KrishnaProjectAudit(repo,td).run()
        failures=[x for x in report["findings"] if x["status"]=="FAIL"]
        self.assertEqual(failures,[],failures)
        self.assertGreaterEqual(len(report["workers"]),9)
        self.assertGreaterEqual(report["counts"]["PASS"],8)

    def test_repository_audit_ignores_local_backups_and_generated_state(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"source";runtime=root/"runtime"
            (source/"core").mkdir(parents=True)
            (source/"core"/"safe.py").write_text("print('ok')\n",encoding="utf-8")
            (source/"backups"/"old"/"core").mkdir(parents=True)
            (source/"backups"/"old"/"core"/"legacy.py").write_text(
                "import os\nos.system('legacy-only')\n",encoding="utf-8"
            )
            (source/".krishna_state").mkdir()
            (source/".krishna_state"/"state.json").write_text('{"ok": true}',encoding="utf-8")
            audit=KrishnaProjectAudit(source,runtime)
            audit.audit_repository()
        finding=next(x for x in audit.findings if x.name=="whole-source security/syntax scan")
        self.assertEqual(finding.status,"PASS",finding.public())
        self.assertEqual(finding.evidence["file_count"],1)

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
