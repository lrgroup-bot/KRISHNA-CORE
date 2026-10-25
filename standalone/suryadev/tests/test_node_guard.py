"""A crashed SURYADEV node can be restarted without OS process scanning."""
import json
from pathlib import Path
import tempfile
import unittest

from suryadev_node_guard import NodeGuard, FILE


class FakeProcess:
    pid=544332
    def __init__(self, code):
        self.code=code
    def wait(self):
        return self.code
    def poll(self):
        return self.code


class NodeGuardTests(unittest.TestCase):
    def setup_files(self, root):
        app=root/"app"
        app.mkdir()
        (app/"start-node.py").write_text("# test marker",encoding="utf-8")
        data=root/"data"
        return app,data

    def test_crash_loop_quarantines_after_three_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            app,data=self.setup_files(Path(tmp))
            records=[]
            def launch(args,**kwargs):
                records.append((args,kwargs))
                return FakeProcess(7)
            guard=NodeGuard(app,data,model="collector",
                            adaptive=True,continuous=True,
                            runner=launch,clock=lambda:1000,sleeper=lambda _:None)
            self.assertEqual(guard.run(),3)
            self.assertEqual(len(records),3)
            state=json.loads((data/FILE).read_text(encoding="utf-8"))
            self.assertEqual(state["state"],"quarantined_crash_loop")
            self.assertEqual(state["launches"],3)
            self.assertTrue(state["no_unrelated_process_termination"])
            self.assertIn("--continuous",records[0][0])
            self.assertIn("--adaptive-fleet",records[0][0])
            self.assertFalse(records[0][1]["shell"])

    def test_transient_crash_recovers_and_preserves_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            app,data=self.setup_files(Path(tmp))
            data.mkdir()
            (data/"existing-learning.txt").write_text("KEEP",encoding="utf-8")
            codes=iter([1,0])
            guard=NodeGuard(app,data,runner=lambda *a,**kw:FakeProcess(next(codes)),
                            clock=lambda:1000,sleeper=lambda _:None)
            self.assertEqual(guard.run(),0)
            self.assertEqual((data/"existing-learning.txt").read_text(),"KEEP")
            state=json.loads((data/FILE).read_text(encoding="utf-8"))
            self.assertEqual(state["state"],"stopped_normally")
            self.assertEqual(state["launches"],2)

    def test_owner_stop_never_restarts(self):
        with tempfile.TemporaryDirectory() as tmp:
            app,data=self.setup_files(Path(tmp))
            called=[]
            guard=NodeGuard(app,data,runner=lambda *a,**kw:called.append(True),
                            clock=lambda:1000,sleeper=lambda _:None)
            guard.request_stop()
            self.assertEqual(guard.run(),0)
            self.assertEqual(called,[])
            self.assertEqual(json.loads((data/FILE).read_text())["state"],
                             "stopping_by_operator")


if __name__=="__main__":
    unittest.main()
