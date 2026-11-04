import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.bhumiputra import BhumiputraAgent
from krishna_core.hawkeye_edge_reflex import HawkeyeEdgeReflex
from krishna_core.hawkeye_target_lock import (
    HawkeyeTargetBackendPlan,
    HawkeyeTargetLock,
    TargetDescriptionParser,
)


class HawkeyeVisualTargetLockTests(unittest.TestCase):
    def test_parser_extracts_visual_description(self):
        q=TargetDescriptionParser.parse("Hawkeye lock the blue shirt person with backpack")
        self.assertEqual(q.object_class,"person")
        self.assertIn("blue",q.colors)
        self.assertIn("shirt",q.clothing)
        self.assertIn("backpack",q.accessories)

    def test_description_acquires_unique_blue_target(self):
        lock=HawkeyeTargetLock(acquire_threshold=.5)
        rows=[
            {"tracking_id":1,"label":"person","confidence":.9,"attributes":{"colors":["red"],"clothing":["shirt"]},"bbox":[.1,.1,.2,.6]},
            {"tracking_id":2,"label":"person","confidence":.9,"attributes":{"colors":["blue"],"clothing":["shirt"]},"bbox":[.5,.1,.2,.6]},
        ]
        out=lock.acquire("lock blue shirt person",rows)
        self.assertEqual(out["state"],"LOCKED")
        self.assertEqual(out["tracking_id"],2)
        self.assertFalse(out["biometric_identity_persisted"])

    def test_ambiguous_people_fail_closed(self):
        lock=HawkeyeTargetLock(acquire_threshold=.5,ambiguity_margin=.1)
        rows=[
            {"tracking_id":1,"label":"person","confidence":.9,"attributes":{"colors":["blue"],"clothing":["shirt"]}},
            {"tracking_id":2,"label":"person","confidence":.89,"attributes":{"colors":["blue"],"clothing":["shirt"]}},
        ]
        out=lock.acquire("blue shirt person",rows)
        self.assertEqual(out["state"],"AMBIGUOUS")
        self.assertIsNone(out["tracking_id"])

    def test_occlusion_then_reid_reacquires_without_identity_database(self):
        lock=HawkeyeTargetLock(acquire_threshold=.5,reid_threshold=.75,max_missing_frames=2)
        first=lock.acquire("blue shirt person",[
            {"tracking_id":7,"label":"person","confidence":.9,"attributes":{"colors":["blue"],"clothing":["shirt"]}}
        ])
        self.assertEqual(first["state"],"LOCKED")
        self.assertEqual(lock.update([])["state"],"OCCLUDED")
        again=lock.update([
            {"tracking_id":42,"label":"person","confidence":.85,"reid_similarity":.92,
             "attributes":{"colors":["blue"],"clothing":["shirt"]}}
        ])
        self.assertEqual(again["state"],"REACQUIRED")
        self.assertEqual(again["tracking_id"],42)

    def test_backend_plan_prefers_grounding_and_reid_when_available(self):
        plan=HawkeyeTargetBackendPlan.plan("blue shirt person",edge_available=True,reid_available=True,grounding_available=True)
        self.assertEqual(plan["acquisition"],"grounding_dino")
        self.assertEqual(plan["tracking"],"bot_sort_reid")
        self.assertEqual(plan["edge_reflex"],"esp_who_bytetrack")

    def test_edge_reflex_emits_camera_follow_hint_only(self):
        edge=HawkeyeEdgeReflex()
        out=edge.ingest({"source":"esp32-p4","tracking_id":4,"class":"person","confidence":.9,"bbox":[.7,.2,.2,.5]})
        self.assertTrue(out["accepted"])
        self.assertGreater(out["camera_follow_hint"]["offset_x"],0)
        self.assertEqual(out["actuation_scope"],"camera framing only")

    def test_bhumiputra_exposes_vtal_and_reflex(self):
        with tempfile.TemporaryDirectory() as td:
            agent=BhumiputraAgent(Path(td)/"hawk")
            out=agent.acquire_visual_target("red car",[
                {"tracking_id":3,"label":"car","confidence":.9,"attributes":{"colors":["red"]}}
            ])
            self.assertEqual(out["state"],"LOCKED")
            self.assertIn("visual_target_lock",agent.status())
            self.assertTrue(agent.ingest_edge_reflex({"confidence":.9,"bbox":[.1,.1,.2,.2]})["accepted"])


class HawkeyeMobileVisualLockContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.mobile=cls.root/"mobile_v3"
        cls.active=(cls.mobile/"hawkeye-active-vision.js").read_text(encoding="utf-8")
        cls.ui=(cls.mobile/"hawkeye-observer-ui.js").read_text(encoding="utf-8")
        cls.index=(cls.mobile/"index.html").read_text(encoding="utf-8")
        cls.runtime=json.loads((cls.mobile/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))

    def test_mobile_supports_description_match_and_color_evidence(self):
        self.assertIn("matchByDescription",self.active)
        self.assertIn("descriptorQuery",self.active)
        self.assertIn("upper_color",self.ui)
        self.assertIn("lockByDescription",self.ui)

    def test_voice_lock_routes_to_hawkeye(self):
        self.assertIn("wantsLock",self.index)
        self.assertIn("lockByDescription",self.index)
        self.assertIn("unlock|release",self.index)

    def test_runtime_declares_visual_target_lock(self):
        b=self.runtime["boundaries"]
        self.assertTrue(b["natural_language_visual_target_lock"])
        self.assertTrue(b["session_local_target_identity"])
        self.assertTrue(b["fail_closed_target_ambiguity"])
        self.assertTrue(b["edge_reflex_ready"])


if __name__=="__main__":
    unittest.main()
