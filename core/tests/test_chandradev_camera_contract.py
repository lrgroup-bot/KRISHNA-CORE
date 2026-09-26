import unittest
from pathlib import Path


class ChandradevCameraIntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.orchestrator=(cls.root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        cls.camera=(cls.root/"core"/"krishna_core"/"chandradev_camera.py").read_text(encoding="utf-8")

    def test_existing_chandradev_is_canonical_pc_camera_owner(self):
        self.assertIn("self.chandradev = ChandradevQC",self.orchestrator)
        self.assertIn("self.chandradev_camera = ChandradevOsmoCameraAdapter",self.orchestrator)
        self.assertIn("chandradev=self.chandradev",self.orchestrator)
        self.assertNotIn("hawkeye=",self.camera.lower())

    def test_chandradev_status_includes_camera_adapter(self):
        self.assertIn('status=self.chandradev.status()',self.orchestrator)
        self.assertIn('status["camera"]=self.chandradev_camera.status()',self.orchestrator)

    def test_camera_actions_are_chandradev_only(self):
        for action in (
            "chandradev.camera.osmo.profile",
            "chandradev.camera.osmo.guide",
            "chandradev.camera.webcam.profile",
            "chandradev.camera.selection",
            "chandradev.camera.receiver.config",
            "chandradev.camera.receiver.start",
            "chandradev.camera.receiver.stop",
            "chandradev.camera.frame.capture",
            "chandradev.camera.frame.analyze",
            "chandradev.camera.screen.focus",
            "chandradev.camera.screen.analyze",
            "chandradev.camera.screen.unlock",
            "chandradev.camera.screen.alignment",
            "chandradev.camera.observations",
        ):
            self.assertIn(f'"{action}"',self.orchestrator)
        self.assertNotIn('"chandradev.camera.session.start"',self.orchestrator)

    def test_network_listener_start_stop_require_owner_approval(self):
        start=self.orchestrator.index('"chandradev.camera.receiver.start"')
        stop=self.orchestrator.index('"chandradev.camera.receiver.stop"')
        self.assertIn("requires_approval=True",self.orchestrator[start:start+650])
        self.assertIn("requires_approval=True",self.orchestrator[stop:stop+650])


if __name__=="__main__":
    unittest.main()
