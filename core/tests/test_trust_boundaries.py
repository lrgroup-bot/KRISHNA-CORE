import tempfile
import time
import unittest
from pathlib import Path
from krishna_core.memory import MemoryStore
from krishna_core.reality_grounding import reality_record, reality_gate

class TrustBoundaryTests(unittest.TestCase):
    def test_revalidation_needs_evidence_gate(self):
        with tempfile.TemporaryDirectory() as td:
            m=MemoryStore(Path(td)/"m.db")
            r=m.learn("KRISHNA","topic","candidate")
            m.invalidate_learning_tree("KRISHNA",r["fingerprint"],"changed")
            with self.assertRaises(ValueError):
                m.verify_learning("KRISHNA",r["fingerprint"],{})
            m.close()

    def test_mirrors_are_one_family(self):
        rows=[reality_record(claim="x",level="digitally_observed",source_ref="u1",source_family="mirror"),
              reality_record(claim="x",level="digitally_observed",source_ref="u2",source_family="mirror")]
        self.assertFalse(reality_gate(rows)["independent_source_refs"])

    def test_expired_physical_observation_is_not_current_grounding(self):
        rows=[reality_record(claim="x",level="physically_observed",source_ref="cam",source_family="cam",observed_at=time.time()-100,ttl_seconds=1),
              reality_record(claim="x",level="digitally_observed",source_ref="api",source_family="api",observed_at=time.time(),ttl_seconds=60)]
        out=reality_gate(rows,high_impact=True)
        self.assertEqual(out["status"],"needs_real_world_validation")
        self.assertEqual(out["stale_records"],1)

if __name__=="__main__": unittest.main()
