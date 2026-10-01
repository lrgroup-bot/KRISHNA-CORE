import tempfile,unittest
from pathlib import Path
from krishna_core.pariksha import ABILITIES
from krishna_core.pariksha_orchestrator import ParikshaLedger

class DailyParikshaTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.p=ParikshaLedger(Path(self.t.name)/"p.db")
 def tearDown(self):self.p.close();self.t.cleanup()
 def test_persists_and_dashboard_reports_measured_result(self):
  r=self.p.record(domain="KRISHNA",examiner="PARIKSHA-K",scores={x:.8 for x in ABILITIES},difficulty=.5)
  d=self.p.owner_dashboard("KRISHNA");self.assertEqual(d["latest_kcci"],r["kcci"]);self.assertEqual(d["state"],"measured")
 def test_contaminated_daily_run_fails_closed(self):
  with self.assertRaises(ValueError):self.p.record(domain="KRISHNA",examiner="PARIKSHA-K",scores={},difficulty=.5,unseen_ratio=.5)
 def test_weakness_drives_training_and_delayed_retest(self):
  scores={x:.9 for x in ABILITIES};scores["novel_transfer"]=.2
  failure={"ability":"novel_transfer","failure_type":"cross_domain_transfer"}
  r=self.p.record(domain="KRISHNA",examiner="PARIKSHA-K",scores=scores,difficulty=.6,failures=[failure])
  self.assertEqual(self.p.training_plan(r)[0]["ability"],"novel_transfer")
  ids=self.p.schedule_retests(r["run_id"],[failure],delay_seconds=3600);self.assertEqual(len(ids),1)
 def test_no_run_never_fabricates_score(self):self.assertEqual(self.p.owner_dashboard("KRISHNA")["state"],"no_measured_run")
if __name__=="__main__":unittest.main()
