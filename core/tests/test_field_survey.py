from __future__ import annotations
import tempfile
from pathlib import Path
import unittest

from krishna_core.field_survey import FieldSurveyEngine

class FieldSurveyTests(unittest.TestCase):
    BOUNDARY=[
        {"lat":20.3000,"lon":85.8000},
        {"lat":20.3000,"lon":85.8010},
        {"lat":20.3010,"lon":85.8010},
        {"lat":20.3010,"lon":85.8000},
    ]

    def test_geometry_geofence_and_exports(self):
        with tempfile.TemporaryDirectory() as td:
            e=FieldSurveyEngine(Path(td))
            m=e.metrics(self.BOUNDARY)
            self.assertGreater(m["area_m2"],1000)
            self.assertGreater(m["perimeter_m"],100)
            self.assertTrue(e.contains(self.BOUNDARY,{"lat":20.3005,"lon":85.8005})["inside"])
            self.assertEqual(e.geojson("s1",self.BOUNDARY)["features"][0]["geometry"]["type"],"Polygon")
            self.assertIn("<kml",e.kml("s1",self.BOUNDARY))

    def test_volume_requires_depth_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            e=FieldSurveyEngine(Path(td))
            missing=e.volume_estimate(self.BOUNDARY,[])
            self.assertIsNone(missing["volume_m3"])
            measured=e.volume_estimate(self.BOUNDARY,[{"depth_m":2.0,"evidence_state":"MEASURED"},{"depth_m":3.0,"evidence_state":"MEASURED"}])
            self.assertEqual(measured["evidence_state"],"MEASURED")
            self.assertGreater(measured["volume_m3"],measured["area_m2"])

    def test_route_unknowns_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            e=FieldSurveyEngine(Path(td))
            out=e.assess_route([{"id":"a","width_m":4.0},{"id":"b","width_m":2.7,"slope_pct":15,"clearance_m":4.5}])
            self.assertEqual(out["evidence_state"],"UNKNOWN")
            self.assertTrue(out["segments"][0]["issues"])
            self.assertLess(out["segments"][1]["score"],1.0)

if __name__=="__main__":
    unittest.main()
