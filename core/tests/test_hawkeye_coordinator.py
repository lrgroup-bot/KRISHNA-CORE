from __future__ import annotations
import tempfile
from pathlib import Path
import unittest

from krishna_core.hawkeye_coordinator import HawkeyeCoordinator

class FakeBhumiputra:
    def status(self):return {"agent":"bhumiputra","ready":True}
    def ping(self):return "pong"

class FakeDiagnostic:
    def should_activate(self,goal):return "fault" in str(goal).lower()

class HawkeyeCoordinatorTests(unittest.TestCase):
    def test_delegation_and_six_specialist_fusion(self):
        with tempfile.TemporaryDirectory() as td:
            h=HawkeyeCoordinator(Path(td),FakeBhumiputra(),diagnostic=FakeDiagnostic())
            self.assertEqual(h.ping(),"pong")
            out=h.enrich_result(
                "s1",{"analysis":"Visible connector is loose","confidence":0.8,"evidence_state":"OBSERVED"},
                sensor_context={"temperature_c":42.0,"activity":"machine_running","timestamp":1},
                goal="inspect fault",modality="image"
            )
            fusion=out["hawkeye_fusion"]
            self.assertEqual(set(fusion["specialists"]),{"PERCEPTION","PHYSIO","BEHAVIOR","TEMPORAL","DIAGNOSTIC","REASONER"})
            self.assertEqual(fusion["specialists"]["PERCEPTION"]["evidence_state"],"OBSERVED")
            self.assertEqual(fusion["specialists"]["PHYSIO"]["evidence_state"],"MEASURED")
            self.assertGreaterEqual(fusion["supported_specialist_count"],4)

    def test_temporal_comparison_uses_prior_retained_observation(self):
        with tempfile.TemporaryDirectory() as td:
            h=HawkeyeCoordinator(Path(td),FakeBhumiputra())
            h.enrich_result("s2",{"analysis":"door closed","confidence":0.7,"evidence_state":"OBSERVED"})
            out=h.enrich_result("s2",{"analysis":"door open","confidence":0.7,"evidence_state":"OBSERVED"})
            obs=out["hawkeye_fusion"]["specialists"]["TEMPORAL"]["observations"]
            self.assertTrue(any("differs" in x for x in obs))

if __name__=="__main__":
    unittest.main()
