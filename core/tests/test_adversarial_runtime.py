import tempfile,time,unittest
from pathlib import Path
from krishna_core.mission_engine import MissionEngine
from krishna_core.world_state import WorldStateLedger
from krishna_core.provider_governor import provider_failure_action

class AdversarialRuntimeTests(unittest.TestCase):
    def test_terminal_mission_cannot_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            m=MissionEngine(Path(td)/"m.db");x=m.create("x");m.transition(x["mission_id"],"RUNNING");m.transition(x["mission_id"],"VERIFYING");m.transition(x["mission_id"],"COMPLETED",verification_status="passed")
            with self.assertRaises(ValueError):m.transition(x["mission_id"],"RUNNING")
            m.close()
    def test_illegal_jump_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            m=MissionEngine(Path(td)/"m.db");x=m.create("x")
            with self.assertRaises(ValueError):m.transition(x["mission_id"],"VERIFYING")
            m.close()
    def test_world_state_expires_to_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            w=WorldStateLedger(Path(td)/"w.db");w.observe("fan","running",True,reality_level="physically_observed",observer="CHANDRADEV",source_family="camera",observed_at=time.time()-10,ttl_seconds=1)
            self.assertEqual(w.current("fan","running")["state"],"unknown");w.close()
    def test_world_state_preserves_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            w=WorldStateLedger(Path(td)/"w.db");w.observe("fan","running",True,reality_level="physically_observed",observer="CHANDRADEV",source_family="camera",ttl_seconds=60);w.observe("fan","running",False,reality_level="physically_observed",observer="HAWKEYE",source_family="mobile",ttl_seconds=60)
            self.assertEqual(w.current("fan","running")["state"],"conflicted");w.close()
    def test_retry_after_is_honored(self):
        r=provider_failure_action(429,1,retry_after="17");self.assertEqual(r["backoff_seconds"],17.0);self.assertTrue(r["retry_after_honored"])

if __name__=="__main__":unittest.main()
