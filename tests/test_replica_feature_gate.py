import csv,subprocess,sys,tempfile,unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"tools"/"replica_feature_gate.py"
class GateTests(unittest.TestCase):
 def run_matrix(self,rows):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"features.csv"
   with path.open("w",newline="",encoding="utf-8") as stream:
    writer=csv.DictWriter(stream,fieldnames=["feature_id","priority","status","test_evidence","notes"]);writer.writeheader();writer.writerows(rows)
   return subprocess.run([sys.executable,str(SCRIPT),str(path)],capture_output=True,text=True)
 def test_rejects_unverified_pass(self):
  result=self.run_matrix([dict(feature_id="login",priority="must",status="passed",test_evidence="",notes="")])
  self.assertEqual(result.returncode,1)
 def test_rejects_missing_must_have(self):
  result=self.run_matrix([dict(feature_id="login",priority="must",status="not_tested",test_evidence="",notes="")])
  self.assertEqual(result.returncode,1)
 def test_accepts_verified_feature(self):
  result=self.run_matrix([dict(feature_id="login",priority="must",status="passed",test_evidence="tests/login.spec.ts",notes="")])
  self.assertEqual(result.returncode,0)
if __name__=="__main__":unittest.main()
