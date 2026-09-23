import tempfile
import unittest
from pathlib import Path

from krishna_core.field_scene import FieldSceneBuilder


class FieldSceneBuilderTests(unittest.TestCase):
    def test_scene_requires_measured_gnss(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                FieldSceneBuilder(td).build("site",[
                    {"lat":20.2,"lon":85.8,"evidence_state":"UNKNOWN"}
                ])

    def test_scene_keeps_missing_depth_and_photogrammetry_visible(self):
        with tempfile.TemporaryDirectory() as td:
            out=FieldSceneBuilder(td).build("site",[
                {"lat":20.2961,"lon":85.8245,"accuracy_m":1.2,
                 "evidence_state":"MEASURED","fix_type":"rtk_fixed"}
            ],anchors=[{"id":"gate","label":"Gate","lat":20.2962,"lon":85.8247}])
            self.assertTrue(Path(out["path"]).joinpath("scene.json").is_file())
            self.assertFalse(out["scene"]["depth"]["available"])
            self.assertFalse(out["scene"]["photogrammetry"]["available"])
            self.assertTrue(out["scene"]["limitations"])
            packet=FieldSceneBuilder(td).ar_packet(out)
            self.assertFalse(packet["hardware_verified"])
            self.assertEqual(packet["anchors"][0]["id"],"gate")

    def test_measured_depth_is_preserved_without_upgrading_hardware_truth(self):
        with tempfile.TemporaryDirectory() as td:
            depth={
                "measurement_id":"DEPTH-1","evidence_state":"MEASURED",
                "summary":{"min_m":1.0,"max_m":2.0,"median_m":1.5,"mean_m":1.5},
                "survey_grade":True,
            }
            out=FieldSceneBuilder(td).build("site",[
                {"lat":20.2961,"lon":85.8245,"altitude_m":43.0,
                 "accuracy_m":0.02,"evidence_state":"MEASURED","fix_type":"rtk_fixed"}
            ],depth=depth)
            self.assertTrue(out["scene"]["depth"]["available"])
            self.assertTrue(out["scene"]["depth"]["survey_grade"])
            self.assertEqual(out["scene"]["center"]["altitude_m"],43.0)


if __name__=="__main__":
    unittest.main()
