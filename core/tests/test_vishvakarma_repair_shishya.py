import tempfile
import unittest

from krishna_core.vishvakarma_learning import VishvakarmaLearning
from krishna_core.vishvakarma_repair_shishya import (
    RepairResearchFinding,
    VishvakarmaRepairShishya,
)


class VishvakarmaRepairShishyaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.learning=VishvakarmaLearning(self.tmp.name+"/learning")
        self.shishya=VishvakarmaRepairShishya(self.tmp.name+"/repair",self.learning)

    def tearDown(self):
        self.tmp.cleanup()

    def test_permanent_research_mission_and_learning(self):
        mission=self.shishya.research_mission("laptop motherboard no power")
        self.assertTrue(mission["permanent"])
        self.assertIn("startup sequence", " ".join(mission["research_questions"]))
        row=self.shishya.save_research(RepairResearchFinding(
            source="datasheet",
            source_version="rev-a",
            license="public-reference",
            topic="buck regulator",
            lesson="verify VIN before replacing controller",
            evidence="datasheet VIN operating range and bench reading",
            confidence=0.9,
        ))
        self.assertEqual(row["status"],"candidate")
        self.assertTrue(row["brahma_review_required"])

    def test_human_style_sequence_requires_visual_observation_first(self):
        out=self.shishya.start_session(
            device_type="motherboard",
            symptom="no power",
            model="example",
        )
        sid=out["session"]["session_id"]
        self.assertEqual(out["next"]["stage"],"VISUAL_INSPECTION")
        nxt=self.shishya.add_observation(
            sid,"No burn marks. DC input connector and fuse are visible."
        )["next"]
        self.assertEqual(nxt["stage"],"POWER_PATH_IDENTIFICATION")

    def test_verified_test_point_can_point_hawkeye_target(self):
        out=self.shishya.start_session(
            device_type="motherboard",
            symptom="no power",
            reference_id="boardview-1",
            reference_verified=True,
            test_points=[{
                "label":"VIN_REG1",
                "component_id":"U10",
                "bbox":[0.4,0.2,0.1,0.1],
                "quantity":"voltage",
                "expected_min":11.5,
                "expected_max":12.5,
                "unit":"V",
                "reason":"verify regulator input before checking output",
            }],
        )
        sid=out["session"]["session_id"]
        self.shishya.add_observation(sid,"Input area inspected; no visible damage.")
        nxt=self.shishya.next_step(sid)
        self.assertEqual(nxt["stage"],"VERIFIED_TEST_POINT")
        self.assertEqual(nxt["target"]["component_id"],"U10")
        self.assertEqual(nxt["target"]["bbox"],[0.4,0.2,0.1,0.1])

    def test_zero_voltage_branches_upstream_not_to_ic_replacement(self):
        out=self.shishya.start_session(
            device_type="motherboard",
            symptom="no power",
        )
        sid=out["session"]["session_id"]
        self.shishya.add_observation(sid,"Board inspected; input connector visible.")
        got=self.shishya.record_measurement(
            sid,point="DC_IN",quantity="voltage",value=0,unit="V"
        )
        self.assertEqual(got["next"]["stage"],"ZERO_VOLTAGE_BRANCH")
        self.assertIn("upstream",got["next"]["instruction"].lower())

    def test_high_voltage_measurement_stops_live_probing(self):
        out=self.shishya.start_session(device_type="power supply",symptom="dead")
        sid=out["session"]["session_id"]
        self.shishya.add_observation(sid,"Power stage visible.")
        got=self.shishya.record_measurement(
            sid,point="BUS",quantity="voltage",value=325,unit="V",circuit_state="high_voltage"
        )
        self.assertTrue(got["recorded"]["hazardous_voltage_possible"])
        self.assertEqual(got["next"]["stage"],"SAFETY_STOP")

    def test_real_repair_outcome_is_saved_to_vishvakarma_learning(self):
        out=self.shishya.start_session(
            device_type="laptop motherboard",
            symptom="no charge",
            model="board-x",
        )
        sid=out["session"]["session_id"]
        self.shishya.add_observation(sid,"DC jack solder joint cracked.")
        self.shishya.record_action(sid,"resoldered DC jack",result="stable continuity")
        done=self.shishya.finish_session(
            sid,
            outcome="Charging restored after DC jack repair.",
            repaired=True,
            verification="Booted and charged battery for 20 minutes without dropout.",
        )
        self.assertEqual(done["knowledge_status"],"candidate")
        rows=self.learning.list(topic="board-x")
        self.assertEqual(len(rows),1)
        self.assertIn("Charging restored",rows[0]["lesson"])


if __name__=="__main__":
    unittest.main()
