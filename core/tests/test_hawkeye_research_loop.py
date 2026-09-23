import json
import unittest
from pathlib import Path


class HawkeyeResearchLoopContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.observer=(cls.root/"core"/"krishna_core"/"hawkeye_learning_observer.py").read_text(encoding="utf-8")
        cls.orchestrator=(cls.root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        cls.server=(cls.root/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
        cls.activity=(cls.root/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8")
        cls.ui=(cls.root/"mobile_v3"/"hawkeye-observer-ui.js").read_text(encoding="utf-8")
        cls.index=(cls.root/"mobile_v3"/"index.html").read_text(encoding="utf-8")
        cls.runtime=json.loads((cls.root/"mobile_v3"/"CANONICAL_RUNTIME.json").read_text(encoding="utf-8"))

    def test_observer_builds_distilled_research_request(self):
        self.assertIn("def research_request(",self.observer)
        self.assertIn('"privacy": "local_only"',self.observer)
        self.assertIn('"raw_media_included": False',self.observer)
        self.assertIn('"automatic_cloud_escalation": False',self.observer)
        self.assertIn('"gyan_auto_approval": False',self.observer)
        self.assertIn("def record_research(",self.observer)

    def test_orchestrator_uses_existing_rishi_live_shared_action(self):
        self.assertIn("def hawkeye_research_observation(",self.orchestrator)
        self.assertIn('"brahmagyan.live.run"',self.orchestrator)
        self.assertIn('actor="hawkeye-learning-observer"',self.orchestrator)
        self.assertIn('"web.read","model.use","evidence.write","memory.write"',self.orchestrator)
        self.assertIn('"gyan_auto_approved":False',self.orchestrator)

    def test_server_exposes_separate_research_endpoint(self):
        self.assertIn('/api/hawkeye/learn/research',self.server)
        self.assertIn("orch.hawkeye_research_observation(observation_id)",self.server)

    def test_mobile_research_runs_off_camera_ui_thread(self):
        self.assertIn("hawkeyeResearchObservation",self.activity)
        self.assertIn('"hawkeye-rishi-research"',self.activity)
        self.assertIn('/api/hawkeye/learn/research',self.activity)
        self.assertIn("raw_media_uploaded",self.activity)
        self.assertIn("onResearchResult",self.ui)
        self.assertIn("Research: queued",self.ui)

    def test_continuous_learning_is_controlled_only_by_learn_toggle(self):
        self.assertIn("isLearning()",self.index)
        self.assertIn("HawkeyeObserverUI.learningTick(false)",self.index)
        self.assertNotIn("Krishna.hawkeyeLearnCapture(",self.index)
        self.assertIn("function isLearning(){return !!state.learn;}",self.ui)

    def test_runtime_declares_no_auto_approval_or_cloud_default(self):
        b=self.runtime["boundaries"]
        self.assertTrue(b["hawkeye_rishi_live_research_handoff"])
        self.assertTrue(b["hawkeye_learning_requires_learn_toggle"])
        self.assertEqual(b["hawkeye_research_model_privacy_default"],"local_only")
        self.assertFalse(b["hawkeye_gyan_auto_approval"])


if __name__=="__main__":
    unittest.main()
