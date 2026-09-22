import tempfile
import unittest
from pathlib import Path

from krishna_core.hawkeye_reference import HawkeyeReferenceRegistry


class HawkeyeReferenceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=HawkeyeReferenceRegistry(Path(self.tmp.name)/"refs")

    def tearDown(self):
        self.tmp.cleanup()

    def test_verified_reference_aligns_to_camera(self):
        self.r.register("board1","boardview",{"components":[
            {"id":"A","x":0,"y":0},{"id":"B","x":1,"y":0},{"id":"C","x":0,"y":1}],
            "nets":[{"from":"A","to":"B","label":"VCC"}]},verified=True)
        out=self.r.overlay("board1",[
            {"reference":[0,0],"image":[0.1,0.2]},
            {"reference":[1,0],"image":[0.9,0.2]},
            {"reference":[0,1],"image":[0.1,0.8]},
        ])
        self.assertEqual(out["diagram_mode"],"reference-aligned")
        self.assertTrue(out["reference_verified"])
        self.assertLess(out["registration_rms"],1e-8)
        self.assertEqual(out["flows"][0]["evidence_state"],"MEASURED")

    def test_unverified_reference_cannot_drive_exact_overlay(self):
        self.r.register("board2","netlist",{"components":[
            {"id":"A","x":0,"y":0},{"id":"B","x":1,"y":0},{"id":"C","x":0,"y":1}]},verified=False)
        with self.assertRaises(PermissionError):
            self.r.overlay("board2",[
                {"reference":[0,0],"image":[0,0]},{"reference":[1,0],"image":[1,0]},{"reference":[0,1],"image":[0,1]}
            ])

    def test_csv_reference_adapter(self):
        source="COMPONENT,U1,MCU,0.2,0.3,IC\nCOMPONENT,J1,INPUT,0.1,0.2,connector\nCOMPONENT,R1,R1,0.4,0.3,resistor\nNET,J1,U1,VIN"
        out=self.r.register_source("csv1","boardview",source,verified=True)
        self.assertEqual(out["component_count"],3)
        self.assertEqual(out["net_count"],1)


if __name__=="__main__":
    unittest.main()
