import tempfile,unittest
from pathlib import Path
from krishna_core.power_runtime import KrishnaPowerRuntime
from krishna_core.brahma_daily_scheduler import BrahmaDailyScheduler
from krishna_core.architecture_ledger import ArchitectureLedger
class PowerRuntimeTests(unittest.TestCase):
 def test_facade_and_karma(self):
  with tempfile.TemporaryDirectory() as d:
   p=KrishnaPowerRuntime(d);self.assertTrue(p.status()["free_first"])
   for _ in range(3):p.karma.event("bad","UNSAFE_ATTEMPT")
   self.assertFalse(p.agent_allowed("bad",mutating=True))
 def test_daily_once(self):
  with tempfile.TemporaryDirectory() as d:
   p=KrishnaPowerRuntime(d);s=BrahmaDailyScheduler(p.council,lambda:([{"name":"A","active":True}],[]))
   self.assertTrue(s.run_if_due()["ran"]);self.assertFalse(s.run_if_due()["ran"])
 def test_verified_ledger_only(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"ledger.txt";path.write_text("truth",encoding="utf-8");l=ArchitectureLedger(path)
   with self.assertRaises(ValueError):l.append_verified({"status":"PROPOSED"})
   self.assertTrue(l.append_verified({"status":"VERIFIED","deployed_commit":"abc"})["appended"])
if __name__=="__main__":unittest.main()
