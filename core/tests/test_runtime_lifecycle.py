import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from krishna_core.orchestrator import Orchestrator
from krishna_core.router import ModelRouter
from krishna_core.worker_supervisor import WorkerSupervisor

class RuntimeLifecycleTests(unittest.TestCase):
    def test_close_releases_all_databases_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"runtime.db"
            runtime=Orchestrator(str(path))
            item=runtime.commitments.add("KRISHNA","Preserve this decision")
            runtime.close()
            runtime.close()
            restored=Orchestrator(str(path))
            try: self.assertEqual(restored.commitments.get(item["commitment_id"])["title"],"Preserve this decision")
            finally: restored.close()
            path.rename(Path(td)/"released.db")

    def test_configured_local_model_is_used(self):
        with patch.dict(os.environ,{"KRISHNA_LOCAL_MODEL":"test-local:1"}), patch("urllib.request.urlopen") as opened:
            opened.return_value.__enter__.return_value.read.return_value=b'{"response":"READY"}'
            self.assertEqual(ModelRouter().local("hello"),"READY")
            self.assertEqual(json.loads(opened.call_args.args[0].data)["model"],"test-local:1")

    def test_worker_failure_does_not_hide_other_results(self):
        class Registry:
            def execute(self,name,payload):
                if name=="bad": raise ValueError("expected failure")
                return "verified fixture"
        supervisor=WorkerSupervisor(Registry(),max_workers=2)
        out=supervisor.run([{"worker":"good"},{"worker":"bad"}])
        self.assertEqual({x["worker"]:x["ok"] for x in out},{"good":True,"bad":False})
