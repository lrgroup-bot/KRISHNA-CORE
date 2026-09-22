import tempfile,unittest
from krishna_core.hawkeye_geo_engine import HawkeyeGeoEngine
class GeoTests(unittest.TestCase):
 def test_google_is_visual_only(self):
  with tempfile.TemporaryDirectory() as d:
   g=HawkeyeGeoEngine(d); google=[x for x in g.catalog() if x["provider"].startswith("google")]
   self.assertTrue(google);self.assertTrue(all(not x["analysis"] for x in google))
 def test_pack(self):
  with tempfile.TemporaryDirectory() as d:
   x=HawkeyeGeoEngine(d).make_field_pack("site",[[20,85],[20.1,85.1]])
   self.assertFalse(x["manifest"]["google_cached"])
if __name__=="__main__":unittest.main()
