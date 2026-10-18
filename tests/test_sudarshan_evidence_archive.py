import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_evidence_archive import archive, verify, load

class ArtifactTests(unittest.TestCase):
    def test_round_trip_and_project_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"evidence"
            source=b'{"report":{"results":[1,2,3]}}'
            evidence_id=archive(root.resolve(),"alpha","REA",source)
            self.assertTrue(verify(root.resolve(),"alpha","REA",evidence_id))
            self.assertEqual(load(root.resolve(),"alpha","REA",evidence_id),
                             {"report":{"results":[1,2,3]}})
            self.assertFalse(verify(root.resolve(),"beta","REA",evidence_id))
            self.assertFalse(verify(root.resolve(),"alpha","MiroFish",evidence_id))
            self.assertEqual(archive(root.resolve(),"alpha","REA",source),evidence_id)

    def test_tampered_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve()
            evidence_id=archive(root,"p","MiroFish",b'{"observation":true}')
            matches=list(root.rglob("*.json"))
            self.assertEqual(len(matches),1)
            matches[0].write_text('{"observation":false}')
            self.assertFalse(verify(root,"p","MiroFish",evidence_id))
            with self.assertRaises(ValueError):
                load(root,"p","MiroFish",evidence_id)
            with self.assertRaises(RuntimeError):
                archive(root,"p","MiroFish",b'{"observation":true}')

    def test_no_traversal_or_nonjson_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve()
            with self.assertRaises(ValueError):
                archive(root,"p","REA",b'not-json')
            with self.assertRaises(ValueError):
                archive(root,"p","REA",b'[]')
            with self.assertRaises(ValueError):
                archive(root,"p","unknown",b'{"ok":true}')
            with self.assertRaises(ValueError):
                verify(root,"p","REA","sha256:../outside")
            with self.assertRaises(ValueError):
                archive(Path("relative"),"p","REA",b'{"ok":true}')

if __name__=="__main__":
    unittest.main()
