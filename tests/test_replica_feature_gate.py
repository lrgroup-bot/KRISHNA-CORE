import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/"tools"/"replica_feature_gate.py"


class GateTests(unittest.TestCase):
    def run_matrix(self, rows, proof_files=()):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"features.csv"
            with path.open("w",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(
                    stream,fieldnames=["feature_id","priority","status","test_evidence","notes"])
                writer.writeheader()
                writer.writerows(rows)
            for proof in proof_files:
                artifact=(Path(directory)/proof)
                artifact.parent.mkdir(parents=True,exist_ok=True)
                artifact.write_text("test output - independent verification pending")
            return subprocess.run([sys.executable,str(SCRIPT),str(path)],
                                  capture_output=True,text=True)

    def _row(self, status="passed", evidence="tests/login.spec.ts"):
        return dict(feature_id="login",priority="must",status=status,
                    test_evidence=evidence,notes="")

    def test_rejects_unverified_pass(self):
        result=self.run_matrix([self._row(evidence="")])
        self.assertEqual(result.returncode,1)
        self.assertTrue(json.loads(result.stdout)["errors"])

    def test_rejects_missing_must_have(self):
        result=self.run_matrix([self._row(status="not_tested",evidence="")])
        self.assertEqual(result.returncode,1)

    def test_rejects_fake_evidence_path(self):
        result=self.run_matrix([self._row()])
        self.assertEqual(result.returncode,1)
        self.assertTrue(json.loads(result.stdout)["errors"])

    def test_existing_evidence_alone_cannot_release(self):
        result=self.run_matrix([self._row()],proof_files=["tests/login.spec.ts"])
        self.assertEqual(result.returncode,1)
        report=json.loads(result.stdout)
        self.assertTrue(report["evidence_claims_complete"])
        self.assertFalse(report["release_ready"])
        self.assertFalse(report["errors"])

    def test_old_gate_path_cannot_claim_release(self):
        from tools.sudarshan_35_gates import GATES,evaluate
        claims={name:{"passed":True,"evidence_id":"sha256:example",
                      "reviewer":"self"} for name in GATES}
        self.assertEqual(len(GATES),35)
        self.assertFalse(evaluate(claims)["release_ready"])


if __name__=="__main__":
    unittest.main()
