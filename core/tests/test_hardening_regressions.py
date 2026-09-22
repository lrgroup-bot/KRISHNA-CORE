import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from krishna_core.development_operator import DevelopmentOperator
from krishna_core.promotion_runtime import PromotionRuntime
from krishna_core.realtime_session import RealtimeSessionStore


class _Browser:
    pass


class HardeningRegressionTests(unittest.TestCase):
    def test_clean_git_status_is_really_clean(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            subprocess.run(["git","init"],cwd=root,check=True,capture_output=True)
            subprocess.run(["git","config","user.email","krishna@example.invalid"],cwd=root,check=True)
            subprocess.run(["git","config","user.name","KRISHNA Test"],cwd=root,check=True)
            (root/"a.txt").write_text("x",encoding="utf-8")
            subprocess.run(["git","add","a.txt"],cwd=root,check=True)
            subprocess.run(["git","commit","-m","init"],cwd=root,check=True,capture_output=True)
            out=DevelopmentOperator(_Browser()).git_snapshot(root)
            self.assertTrue(out["ok"])
            self.assertTrue(out["clean"])
            self.assertEqual(out["status"],"")

    def test_promotion_runtime_rejects_escape_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shadow=root/"shadow"; working=root/"working"
            shadow.mkdir();working.mkdir()
            (root/"outside.txt").write_text("secret",encoding="utf-8")
            with self.assertRaises(ValueError):
                PromotionRuntime().promote(shadow,working,["../outside.txt"],verified=True)

    def test_realtime_store_hashes_device_filename_and_fails_closed_on_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            store=RealtimeSessionStore(td)
            device="android/../../primary"
            event=store.publish(device,"hello",{"ok":True},idempotency_key="k1")
            self.assertEqual(event["seq"],1)
            path=store._path(device)
            self.assertTrue(path.is_file())
            self.assertNotIn("android",path.name)
            self.assertNotIn("..",path.name)
            path.write_text("{bad-json",encoding="utf-8")
            with self.assertRaises(RuntimeError):
                store.after(device,0)

    def test_realtime_store_migrates_legacy_session_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as td:
            store=RealtimeSessionStore(td)
            device="android-primary"
            legacy=store._legacy_path(device)
            legacy.write_text(json.dumps({"next_seq":2,"events":[{"id":"x","seq":1,"type":"old","payload":{},"ts":1}],"seen":{}}),encoding="utf-8")
            rows=store.after(device,0)
            self.assertEqual(rows[0]["type"],"old")
            self.assertTrue(store._path(device).is_file())
            self.assertTrue(legacy.is_file())


if __name__=="__main__":
    unittest.main()
