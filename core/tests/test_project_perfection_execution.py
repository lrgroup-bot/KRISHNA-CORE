import tempfile
import unittest
from pathlib import Path

from krishna_core.project_perfection_execution import (
    DesignStudio, MutationRunner, RegressionPersister, VisualBaselineStore,
)


class ExecutionTests(unittest.TestCase):
    def test_regression_persisted_inside_project(self):
        with tempfile.TemporaryDirectory() as td:
            out=RegressionPersister().persist(td,"demo","test('x',()=>{});")
            path=Path(out["path"])
            self.assertTrue(path.is_file())
            self.assertTrue(str(path).startswith(str(Path(td).resolve())))

    def test_mutation_is_restored_and_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"demo.py"
            original="FLAG = True\n"
            path.write_text(original,encoding="utf-8")
            def verify():
                return {"verified":"False" not in path.read_text(encoding="utf-8")}
            out=MutationRunner().run(td,verify,max_mutants=1)
            self.assertEqual(out["executed"],1)
            self.assertTrue(out["passed"])
            self.assertEqual(path.read_text(encoding="utf-8"),original)

    def test_visual_baseline_creation_and_exact_match(self):
        with tempfile.TemporaryDirectory() as td:
            shot=Path(td)/"shot.png";shot.write_bytes(b"not-a-real-png-but-stable")
            store=VisualBaselineStore(Path(td)/"base")
            first=store.compare("demo","mobile",shot,approve_missing=True)
            second=store.compare("demo","mobile",shot)
            self.assertTrue(first["passed"])
            self.assertTrue(second["passed"])
            self.assertEqual(second["mode"],"byte_identical")

    def test_design_studio_requires_rendered_preview_and_submit(self):
        with tempfile.TemporaryDirectory() as td:
            studio=DesignStudio(td)
            state=studio.create("demo",[
                {"preview_url":"http://127.0.0.1:9001/a","reference_url":"https://example.com/a"},
                {"preview_url":"http://127.0.0.1:9001/b","reference_url":"https://example.com/b"},
            ])
            self.assertEqual([x["label"] for x in state["candidates"]],["A","B"])
            chosen=state["candidates"][1]
            submitted=studio.submit(state["session_id"],chosen["id"])
            self.assertTrue(submitted["submitted"])
            self.assertEqual(submitted["selected"]["label"],"B")
            self.assertTrue(submitted["requires_full_regression"])


if __name__=="__main__":
    unittest.main()
