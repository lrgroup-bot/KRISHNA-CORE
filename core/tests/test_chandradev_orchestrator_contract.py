import unittest
from pathlib import Path


class ChandradevOrchestratorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.orchestrator=(cls.root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        cls.source=(cls.root/"core"/"krishna_core"/"chandradev_stream.py").read_text(encoding="utf-8")

    def test_chandradev_is_bound_to_hawkeye_and_local_vision(self):
        self.assertIn("self.chandradev_vision = VisionAdapter()",self.orchestrator)
        self.assertIn("hawkeye=self.hawkeye",self.orchestrator)
        self.assertIn("vision=self.chandradev_vision",self.orchestrator)
        self.assertIn('status["chandradev"]=self.chandradev.status()',self.orchestrator)

    def test_chandradev_actions_are_registered(self):
        for action in (
            "chandradev.status",
            "chandradev.hardware.osmo_action",
            "chandradev.osmo.guide",
            "chandradev.mediamtx.config",
            "chandradev.server.start",
            "chandradev.server.stop",
            "chandradev.session.start",
            "chandradev.frame.capture",
            "chandradev.frame.analyze",
        ):
            self.assertIn(f'"{action}"',self.orchestrator)

    def test_server_control_remains_owner_approved(self):
        start=self.orchestrator.index('"chandradev.server.start"')
        stop=self.orchestrator.index('"chandradev.server.stop"')
        self.assertIn("requires_approval=True",self.orchestrator[start:start+600])
        self.assertIn("requires_approval=True",self.orchestrator[stop:stop+600])

    def test_chandradev_is_an_agent_without_becoming_main_authority(self):
        self.assertIn('"chandradev","live camera ingest and HAWKEYE visual observation specialist"',self.orchestrator)
        self.assertIn('actions=("chandradev.*","hawkeye.reason","hawkeye.lane.record")',self.orchestrator)
        self.assertIn('"role":"live camera ingest and visual handoff to HAWKEYE"',self.source)


if __name__=="__main__":
    unittest.main()
