from pathlib import Path
import tempfile, unittest
from krishna_core.vishwakarma import VishwakarmaUpdateManager

class VishwakarmaTests(unittest.TestCase):
    def test_frontend_gate_blocks_packaging(self):
        with tempfile.TemporaryDirectory() as d:
            m=VishwakarmaUpdateManager(d); p=m.plan("KRISHNA","stronger runtime")
            self.assertFalse(m.packaging_allowed(p["update_id"])["allowed"])
            m.record(p["update_id"],"IMPLEMENTING")
            m.record(p["update_id"],"TESTED",evidence={"tests_passed":True})
            m.record(p["update_id"],"FRONTEND_READY",evidence={"frontend_proof":"browser evidence"})
            self.assertFalse(m.packaging_allowed(p["update_id"])["allowed"])
            m.record(p["update_id"],"FRONTEND_APPROVED",evidence={"approved":True},actor="OWNER")
            self.assertTrue(m.packaging_allowed(p["update_id"])["allowed"])
    def test_cannot_skip_frontend_or_verification(self):
        with tempfile.TemporaryDirectory() as d:
            m=VishwakarmaUpdateManager(d); p=m.plan("KRISHNA","update")
            with self.assertRaises(ValueError): m.record(p["update_id"],"TESTED",evidence={"tests_passed":True})
    def test_policy_has_no_live_write_or_auto_merge(self):
        with tempfile.TemporaryDirectory() as d:
            m=VishwakarmaUpdateManager(d); p=m.plan("KRISHNA","update")
            self.assertFalse(p["policy"]["live_direct_write"])
            self.assertFalse(p["policy"]["auto_merge"])
            self.assertFalse(p["policy"]["exe_before_frontend_approval"])
if __name__=="__main__": unittest.main()
