import tempfile
import unittest
from pathlib import Path

from krishna_core.bhumiputra import BhumiputraAgent
from krishna_core.hawkeye_coordinator import HawkeyeCoordinator


class FakeVision:
    def analyze_bytes(self,data,content_type,prompt):
        return {
            "provider":"fake-local",
            "model":"fake-vision",
            "local":True,
            "analysis":"visible truck; PPE helmet present; no hidden fault measurement",
        }


class FakeDiagnostic:
    def status(self):
        return {"ready":True,"specialist":"HAWKEYE DIAGNOSTIC"}


class FakeMemory:
    def __init__(self):
        self.events=[]
    def audit(self,*args):
        self.events.append(args)


class HawkeyeCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.memory=FakeMemory()
        self.bhumiputra=BhumiputraAgent(
            Path(self.tmp.name)/"bhumiputra",vision_adapter=FakeVision()
        )
        self.hawkeye=HawkeyeCoordinator(
            Path(self.tmp.name)/"hawkeye",
            bhumiputra=self.bhumiputra,
            diagnostic=FakeDiagnostic(),
            learning=object(),
            field=object(),
            geo=object(),
            memory=self.memory,
        )
        self.session=self.hawkeye.start_live_session(
            project="KRISHNA",purpose="inspect truck and bearing",scene_hint="vehicle"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_live_runtime_is_coordinator_not_bhumiputra_alias(self):
        status=self.hawkeye.status()
        self.assertEqual(status["agent"],"HAWKEYE")
        self.assertEqual(set(status["specialists"]),{
            "perception","physio","behavior","temporal","diagnostic","reasoner"
        })
        self.assertEqual(status["authority"],"KRISHNA")
        self.assertEqual(status["verification"],"SUDARSHAN")

    def test_compatibility_methods_delegate_to_bhumiputra(self):
        sid=self.session["session_id"]
        self.assertEqual(self.hawkeye.get_live_session(sid)["scene_hint"],"vehicle")
        self.assertIn("Bhumiputra",self.hawkeye.live_prompt(user_goal="inspect"))
        self.assertTrue(hasattr(self.hawkeye,"plan_survey"))

    def test_perception_temporal_and_reasoner_are_connected(self):
        sid=self.session["session_id"]
        first=self.hawkeye.record_live_analysis(
            sid,"truck stationary",model="vision-a",
            frame_meta={"sha256":"frame-a","confidence":0.8}
        )
        self.assertEqual(first["hawkeye_lane"]["lane"],"perception")
        self.assertEqual(first["temporal"]["status"],"insufficient_history")
        second=self.hawkeye.record_live_analysis(
            sid,"truck moving",model="vision-a",
            frame_meta={"sha256":"frame-b","confidence":0.85}
        )
        self.assertEqual(second["temporal"]["lane"],"temporal")
        self.assertTrue(second["temporal"]["payload"]["changed"])
        self.assertIn(second["reasoning"]["conclusion_state"],{
            "SUPPORTED","PRELIMINARY"
        })

    def test_existing_bhumiputra_session_is_migrated_without_losing_field_state(self):
        legacy=self.bhumiputra.start_live_session(
            project="KRISHNA",purpose="legacy field scan",scene_hint="terrain"
        )
        sid=legacy["session_id"]
        self.assertFalse(self.hawkeye._path(sid).exists())
        row=self.hawkeye.record_behavior(
            sid,{"action":"excavator stopped"},source_refs=["camera:legacy"]
        )
        self.assertEqual(row["lane"],"behavior")
        self.assertTrue(self.hawkeye._path(sid).exists())
        state=self.hawkeye.get_live_session(sid)
        self.assertEqual(state["scene_hint"],"terrain")
        self.assertEqual(state["hawkeye"]["lane_counts"]["behavior"],1)

    def test_physio_requires_real_numeric_measurement_for_measured_state(self):
        sid=self.session["session_id"]
        with self.assertRaises(ValueError):
            self.hawkeye.record_lane(
                sid,"physio",{"signal":"unknown"},evidence_state="MEASURED"
            )
        row=self.hawkeye.record_physio(
            sid,{"rpm":1450.0,"vibration_mm_s":2.2},
            source_refs=["sensor:accelerometer-1"]
        )
        self.assertEqual(row["evidence_state"],"MEASURED")
        self.assertIn("not proof",row["payload"]["interpretation_limit"])

    def test_behavior_is_observation_only(self):
        sid=self.session["session_id"]
        row=self.hawkeye.record_behavior(
            sid,{"action":"operator switched machine off"},
            source_refs=["camera:frame-10"]
        )
        self.assertIn("observable behavior only",row["payload"]["interpretation_limit"])

    def test_diagnostic_plus_measurement_can_support_reasoning_without_certifying_fault(self):
        sid=self.session["session_id"]
        self.hawkeye.record_physio(
            sid,{"vibration_mm_s":6.1},source_refs=["sensor:vib-1"]
        )
        self.hawkeye.record_diagnostic_result(
            sid,{
                "analysis":"outer-race bearing fault is a hypothesis",
                "evidence_state":"INFERRED",
                "confidence":0.72,
                "next_test":"inspect bearing spectrum and repeat measurement",
            },
            source_refs=["diagnostic:model-1"],
        )
        out=self.hawkeye.reason(sid)
        self.assertEqual(out["conclusion_state"],"SUPPORTED")
        self.assertIn("camera-only hidden faults",out["guardrails"][2])
        self.assertGreaterEqual(out["independent_source_refs"],2)

    def test_open_contradiction_prevents_supported_state(self):
        sid=self.session["session_id"]
        a=self.hawkeye.record_behavior(
            sid,{"action":"machine stopped"},source_refs=["camera:a"]
        )
        b=self.hawkeye.record_behavior(
            sid,{"action":"machine moving"},source_refs=["camera:b"]
        )
        self.hawkeye.add_contradiction(sid,a["fingerprint"],b["fingerprint"],"same timestamp conflict")
        out=self.hawkeye.reason(sid)
        self.assertEqual(out["conclusion_state"],"CONTESTED")
        self.assertEqual(out["open_contradictions"],1)


if __name__=="__main__":
    unittest.main()
