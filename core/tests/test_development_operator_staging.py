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


class DevelopmentRetryFreshnessTests(unittest.TestCase):
    def test_equal_size_rapid_source_repair_is_retested_without_stale_bytecode(self):
        import os
        import py_compile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'tests').mkdir()
            source=root/'answer.py';source.write_text('def answer(): return 1\n',encoding='utf-8')
            stamp=source.stat().st_mtime
            py_compile.compile(str(source),doraise=True)
            source.write_text('def answer(): return 2\n',encoding='utf-8');os.utime(source,(stamp,stamp))
            (root/'tests/test_answer.py').write_text('import unittest\nfrom answer import answer\nclass Check(unittest.TestCase):\n def test_answer(self): self.assertEqual(answer(),2)\n',encoding='utf-8')
            result=DevelopmentOperator(None).verify(root,['python-tests'])
            self.assertTrue(result['verified'],result)
            self.assertEqual(result['steps'][0]['name'],'python-tests')
            self.assertTrue(list((root/'__pycache__').glob('answer*.pyc')),'existing bytecode must be preserved')


if __name__=="__main__":
    unittest.main()
