import subprocess
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_mrityunjaya import baseline, verify_baseline

class RecoveryTests(unittest.TestCase):
    def test_unchanged_repository_passes_modified_repository_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'repo';p.mkdir()
            def git(*args):subprocess.run(['git','-C',str(p),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            git('init','-q')
            (p/'file').write_text('original')
            git('add','file')
            git('-c','user.email=test@example.invalid','-c','user.name=T','commit','-qm','initial')
            snap=baseline(p)
            self.assertEqual(verify_baseline(snap,authorized=True).status,'passed')
            (p/'file').write_text('modified')
            self.assertEqual(verify_baseline(snap,authorized=True).status,'failed')
    def test_requires_approval(self):
        with self.assertRaises(PermissionError):verify_baseline({})

if __name__=='__main__':unittest.main()
