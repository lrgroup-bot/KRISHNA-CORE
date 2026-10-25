"""Dashboard book workload is attached to the same worker, with exact SHA approval."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from suryadev_dashboard_worker import DashboardWorkerControl


class FakeProc:
    pid=123456
    def poll(self):
        return None


class DashboardApprovedBookTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        book=self.root/"sample.txt"
        book.write_text("One\nTwo\nThree\n",encoding="utf-8")
        self.book=book
        self.digest=hashlib.sha256(book.read_bytes()).hexdigest()
        (self.root/"book-plan.json").write_text(json.dumps({
            "schema":"suryadev.book-plan.v1",
            "lines_per_step":5,
            "books":[{"path":str(book),"sha256":self.digest}]}),encoding="utf-8")
        self.ctl=DashboardWorkerControl(self.root,self.root)
    def tearDown(self):
        self.ctl.close()
        self.tmp.cleanup()
    def _run(self,mode):
        with patch.object(self.ctl,"_external_lock_held",return_value=False), \
             patch("suryadev_model_router.resolve_model",
                   return_value={"model":mode,"reason":"explicit_operator_selection"}), \
             patch("suryadev_dashboard_worker.subprocess.Popen",
                   return_value=FakeProc()) as spawn:
            result=self.ctl.start(model=mode)
        return result,spawn.call_args.args[0]
    def test_collector_indexes_book_without_ollama(self):
        r,args=self._run("collector")
        self.assertTrue(r["approved_books_loaded"])
        self.assertEqual(r["book_mode"],"indexed_evidence_only")
        self.assertIn("--book-collect-plan",args)
        self.assertNotIn("--book-plan",args)
        self.assertIn("--no-ollama",args)
    def test_local_model_uses_shared_checkpointed_reader(self):
        r,args=self._run("gemma3:4b")
        self.assertEqual(r["book_mode"],"local_model_interpretation_unverified")
        self.assertIn("--book-plan",args)
        self.assertNotIn("--book-collect-plan",args)
        self.assertNotIn("--no-ollama",args)
    def test_modified_source_refuses_worker_start(self):
        self.book.write_text("Different bytes",encoding="utf-8")
        with patch("suryadev_model_router.resolve_model",
                   return_value={"model":"collector","reason":"explicit_operator_selection"}), \
             patch("suryadev_dashboard_worker.subprocess.Popen") as spawn:
            with self.assertRaisesRegex(ValueError,"changed"):
                self.ctl.start(model="collector")
            spawn.assert_not_called()


if __name__=="__main__":
    unittest.main()
