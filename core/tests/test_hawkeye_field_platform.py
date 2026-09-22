import tempfile,unittest
from pathlib import Path
from krishna_core.hawkeye_field_platform import HawkeyeFieldPlatform

class FieldPlatformTests(unittest.TestCase):
 def test_device_and_pack(self):
  with tempfile.TemporaryDirectory() as d:
   h=HawkeyeFieldPlatform(d)
   x=h.register_device("phone","android",["VIDEO","GNSS","IMU"],["offline"])
   self.assertIn("GNSS",x["sensors"])
   self.assertFalse(h.field_pack_manifest("q1",[[1,2]])["google_content_cached"])
 def test_queue_hashes_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"x.jpg";p.write_bytes(b"abc")
   h=HawkeyeFieldPlatform(Path(d)/"state")
   q=h.queue_observation("s",p,"OBSERVED")
   self.assertEqual(len(q["sha256"]),64)
   self.assertEqual(len(h.pending()),1)

if __name__=="__main__":unittest.main()
