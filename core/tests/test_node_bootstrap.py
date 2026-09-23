import tempfile, unittest
from pathlib import Path
from krishna_core.node_bootstrap import portable_manifest, delta, sync_files, TrustedNodeBootstrap

class TestNodeBootstrap(unittest.TestCase):
 def test_delta_and_verified_copy(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   Path(a,"gyan").mkdir(); Path(a,"gyan/x.txt").write_text("learned",encoding="utf-8")
   s=portable_manifest(a); t=portable_manifest(b); self.assertEqual(delta(s,t),["gyan/x.txt"])
   sync_files(a,b,delta(s,t)); self.assertEqual(portable_manifest(a).files,portable_manifest(b).files)
 def test_requires_trust(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   self.assertEqual(TrustedNodeBootstrap().plan(portable_manifest(a),portable_manifest(b))["status"],"AUTHORIZATION_REQUIRED")
