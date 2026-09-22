import tempfile
import unittest
from pathlib import Path

from krishna_core.project_perfection_execution import (
    BrowserRegressionRunner, DatabaseChaosRunner, DesignStudio, MutationRunner, RegressionManifest,
    RegressionPersister, VisualBaselineStore,
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

    def test_frontend_mutation_is_generated_and_restored(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"index.html"
            original="<!doctype html><html><head></head><body><main>Hello</main></body></html>"
            path.write_text(original,encoding="utf-8")
            def verify():
                text=path.read_text(encoding="utf-8")
                return {"verified":"data-krishna-mutant" not in text}
            out=MutationRunner().run(td,verify,max_mutants=1)
            self.assertEqual(out["executed"],1)
            self.assertTrue(out["passed"])
            self.assertEqual(path.read_text(encoding="utf-8"),original)

    def test_regression_manifest_persists_portable_routes_and_replays(self):
        with tempfile.TemporaryDirectory() as td:
            store=RegressionManifest()
            receipt=store.persist(td,"demo",{
                "nodes":[{"url":"http://127.0.0.1:9999/"},{"url":"http://127.0.0.1:9999/settings?tab=ui"}],
                "edges":[],
            })
            self.assertEqual(receipt["route_count"],2)
            manifest=store.load(td,"demo")
            self.assertIn("/settings?tab=ui",manifest["routes"])
            class Browser:
                def inspect(self,url):
                    return {"ok":True,"findings":[],"layout":{}}
            replay=BrowserRegressionRunner().run(Browser(),"http://127.0.0.1:1234/app",manifest)
            self.assertTrue(replay["passed"])
            self.assertTrue(any("127.0.0.1:1234" in x["url"] for x in replay["routes"]))

    def test_visual_baseline_creation_and_exact_match(self):
        with tempfile.TemporaryDirectory() as td:
            shot=Path(td)/"shot.png";shot.write_bytes(b"not-a-real-png-but-stable")
            store=VisualBaselineStore(Path(td)/"base")
            first=store.compare("demo","mobile",shot,approve_missing=True)
            second=store.compare("demo","mobile",shot)
            self.assertTrue(first["passed"])
            self.assertTrue(second["passed"])
            self.assertEqual(second["mode"],"byte_identical")

    def test_database_chaos_uses_isolated_copy_and_recovers(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"demo.db"
            conn=sqlite3.connect(db);conn.execute("CREATE TABLE demo(id INTEGER)");conn.commit();conn.close()
            out=DatabaseChaosRunner().run(db)
            self.assertTrue(out["executed"])
            self.assertTrue(out["injection_observed"])
            self.assertTrue(out["recovery_observed"])
            self.assertTrue(out["passed"])
            conn=sqlite3.connect(db)
            tables={x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            conn.close()
            self.assertNotIn("krishna_chaos_probe",tables)

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
