import tempfile, unittest
from pathlib import Path
from krishna_core.node_bootstrap import portable_manifest, delta, sync_files, TrustedNodeBootstrap, NodeManifest

class TestNodeBootstrap(unittest.TestCase):
 def test_delta_and_verified_copy(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   Path(a,"gyan").mkdir(); Path(a,"gyan/x.txt").write_text("learned",encoding="utf-8")
   s=portable_manifest(a); t=portable_manifest(b); self.assertEqual(delta(s,t),["gyan/x.txt"])
   sync_files(a,b,delta(s,t)); self.assertEqual(portable_manifest(a).files,portable_manifest(b).files)
 def test_requires_trust(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   self.assertEqual(TrustedNodeBootstrap().plan(portable_manifest(a),portable_manifest(b))["status"],"AUTHORIZATION_REQUIRED")
 def test_manifest_excludes_secret_like_files(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,"safe.txt").write_text("ok",encoding="utf-8")
   Path(d,".env").write_text("TOKEN=secret",encoding="utf-8")
   Path(d,"owner.key").write_text("secret",encoding="utf-8")
   files=portable_manifest(d).files
   self.assertIn("safe.txt",files); self.assertNotIn(".env",files); self.assertNotIn("owner.key",files)
 def test_sync_rejects_path_traversal(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   with self.assertRaises(ValueError):sync_files(a,b,["../escape.txt"])
   plan=TrustedNodeBootstrap().plan(NodeManifest("a","a","1",{"../escape.txt":"x"}),NodeManifest("b","b","1",{}),trusted=True)
   self.assertEqual(plan["status"],"BLOCKED_UNSAFE_MANIFEST")
 def test_manifest_does_not_follow_file_symlink(self):
  with tempfile.TemporaryDirectory() as root,tempfile.TemporaryDirectory() as outside:
   secret=Path(outside,"secret.txt");secret.write_text("private",encoding="utf-8")
   link=Path(root,"linked.txt")
   try:link.symlink_to(secret)
   except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
   self.assertNotIn("linked.txt",portable_manifest(root).files)
