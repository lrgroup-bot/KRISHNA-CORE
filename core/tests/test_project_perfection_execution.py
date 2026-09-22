import tempfile
import unittest
from pathlib import Path

from krishna_core.project_perfection_execution import (
    ArtifactExecutor, BrowserRegressionRunner, DesignStudio, MutationRunner, RegressionManifest,
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

    def test_android_process_wait_tolerates_launcher_race(self):
        class FakeExecutor(ArtifactExecutor):
            def __init__(self):
                self.calls=0
            def _cmd(self,args,timeout=120,cwd=None):
                self.calls+=1
                if self.calls<3:
                    return {"executed":True,"passed":False,"exit_code":1,"output":""}
                return {"executed":True,"passed":True,"exit_code":0,"output":"4242\n"}
        executor=FakeExecutor()
        out=executor._wait_android_process("adb","com.krishna.mobile",attempts=4,delay_seconds=0)
        self.assertTrue(out["passed"])
        self.assertEqual(out["attempts"],3)
        self.assertIn("4242",out["output"])

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
