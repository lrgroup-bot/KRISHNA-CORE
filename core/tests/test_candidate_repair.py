import tempfile
import unittest
from pathlib import Path

from krishna_core.candidate_repair import CandidateRepairGuard


class CandidateRepairGuardTests(unittest.TestCase):
    def test_existing_source_patch_and_new_regression_test_are_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"src").mkdir()
            (root/"src"/"logic.py").write_text("FLAG = True\n",encoding="utf-8")
            rows=CandidateRepairGuard.validate_patch(root,[
                {"path":"src/logic.py","content":"FLAG = False\n"},
                {"path":"tests/test_regression.py","content":"def test_regression():\n    assert True\n"},
            ])
            changed=CandidateRepairGuard.apply(root,rows)
            self.assertIn("src/logic.py",changed)
            self.assertTrue((root/"tests"/"test_regression.py").is_file())

    def test_dependency_and_secret_files_are_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"package.json").write_text("{}",encoding="utf-8")
            with self.assertRaises(PermissionError):
                CandidateRepairGuard.validate_patch(root,[{"path":"package.json","content":"{}"}])
            (root/".env").write_text("SECRET=x",encoding="utf-8")
            with self.assertRaises(PermissionError):
                CandidateRepairGuard.validate_patch(root,[{"path":".env","content":"SECRET=y"}])


if __name__=="__main__":
    unittest.main()
