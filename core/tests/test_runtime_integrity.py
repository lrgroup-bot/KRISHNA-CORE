import hashlib, json, tempfile, unittest
from pathlib import Path
from krishna_core.runtime_integrity import RuntimeIntegrity

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class RuntimeIntegrityTests(unittest.TestCase):
    def test_missing_manifest_is_unverified(self):
        with tempfile.TemporaryDirectory() as td:
            r=RuntimeIntegrity(td,Path(td)/"source")
            s=r.status()
            self.assertEqual(s["status"],"UNVERIFIED")
            self.assertFalse(s["synced"])

    def test_manifest_hashes_are_verified(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"src"; runtime=root/"runtime"
            (runtime/"core/krishna_core").mkdir(parents=True)
            p=runtime/"core/krishna_core/server.py"; p.write_text("ok",encoding="utf-8")
            (runtime/"state/deployment").mkdir(parents=True)
            (runtime/"state/deployment/DEPLOYED_COMMIT.json").write_text(json.dumps({
                "commit":"abc","branch":"test","files":{"core/krishna_core/server.py":sha(p)}
            }),encoding="utf-8")
            s=RuntimeIntegrity(runtime,src).status()
            self.assertEqual(s["status"],"SYNCED")
            p.write_text("changed",encoding="utf-8")
            s=RuntimeIntegrity(runtime,src).status()
            self.assertEqual(s["status"],"DRIFT")
            self.assertIn("core/krishna_core/server.py",s["mismatches"])

if __name__=="__main__": unittest.main()
