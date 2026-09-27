import tempfile
import unittest
from pathlib import Path

from krishna_core.development_operator import DevelopmentOperator


class DevelopmentOperatorStagingTests(unittest.TestCase):
    def test_candidate_copy_prunes_runtime_state_and_cannot_restage_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"project"
            root.mkdir()
            (root/"app.py").write_text("print('ok')\n",encoding="utf-8")

            state=root/".krishna_state"
            state.mkdir()
            (state/"runtime-only.txt").write_text("do not copy",encoding="utf-8")
            staging=state/"promotion-candidates"

            operator=DevelopmentOperator(None,staging_root=staging)
            result=operator.stage(root,[])
            candidate=Path(result["candidate_root"])

            self.assertTrue((candidate/"app.py").is_file())
            self.assertFalse((candidate/".krishna_state").exists())

            with self.assertRaisesRegex(RuntimeError,"cannot stage a promotion candidate"):
                operator.stage(candidate,[])


if __name__=="__main__":
    unittest.main()
