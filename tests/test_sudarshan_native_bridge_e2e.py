import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_mrityunjaya import baseline
from tools.sudarshan_local_adapters import run_adapter

class NativeBridgeE2ETests(unittest.TestCase):
    def test_real_subprocess_bridge_and_git_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)/'repo';repo.mkdir()
            def git(*args):
                subprocess.run(['git','-C',str(repo),*args],check=True,
                               capture_output=True,text=True)
            git('init','-q')
            (repo/'app').write_text('untouched')
            git('add','app')
            git('-c','user.email=t@example.invalid','-c','user.name=T','commit','-qm','initial')
            spec=Path(temporary)/'spec.json'
            spec.write_text(json.dumps({'baseline':baseline(repo)}))
            root=Path(__file__).resolve().parents[1]
            argv=[sys.executable,'-m','tools.sudarshan_native_cli',
                  '--engine','MRITYUNJAYA','--spec',str(spec),'--approve-local-run']
            result=run_adapter('MRITYUNJAYA',argv,authorized=True,cwd=str(root))
            self.assertEqual(result.status,'passed')
            (repo/'app').write_text('changed')
            bad=run_adapter('MRITYUNJAYA',argv,authorized=True,cwd=str(root))
            self.assertEqual(bad.status,'failed')

if __name__=='__main__':unittest.main()
