import unittest
from pathlib import Path


class ChandradevCameraIntegrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.orchestrator=(cls.root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        cls.camera=(cls.root/"core"/"krishna_core"/"chandradev_camera.py").read_text(encoding="utf-8")

    def test_existing_chandradev_qc_remains_canonical(self):
        self.assertIn("self.chandradev = ChandradevQC",self.orchestrator)
        self.assertIn("self.chandradev_camera = ChandradevOsmoCameraAdapter",self.orchestrator)
        self.assertNotIn('self.agent_runtime.register(\n            "chandradev","live camera ingest',self.orchestrator)
        self.assertIn('"component":"CHANDRADEV OSMO CAMERA ADAPTER"',self.camera)

    def test_chandradev_status_includes_camera_adapter(self):
        self.assertIn('status=self.chandradev.status()',self.orchestrator)
        self.assertIn('status["camera"]=self.chandradev_camera.status()',self.orchestrator)

    def test_camera_actions_are_namespaced_under_existing_chandradev(self):
        for action in (
            "chandradev.camera.osmo.profile",
            "chandradev.camera.osmo.guide",
            "chandradev.camera.receiver.config",
            "chandradev.camera.receiver.start",
            "chandradev.camera.receiver.stop",
            "chandradev.camera.session.start",
            "chandradev.camera.frame.capture",
            "chandradev.camera.frame.analyze",
        ):
            self.assertIn(f'"{action}"',self.orchestrator)

    def test_network_listener_start_stop_require_owner_approval(self):
        start=self.orchestrator.index('"chandradev.camera.receiver.start"')
        stop=self.orchestrator.index('"chandradev.camera.receiver.stop"')
        self.assertIn("requires_approval=True",self.orchestrator[start:start+650])
        self.assertIn("requires_approval=True",self.orchestrator[stop:stop+650])


if __name__=="__main__":
    unittest.main()
