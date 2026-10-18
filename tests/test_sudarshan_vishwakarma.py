import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_vishwakarma import propose_code


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

class VishwakarmaTests(unittest.TestCase):
    def test_proposal_archived_original_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            repo=Path(root)/'repo';repo.mkdir()
            git(repo,'init','-q')
            (repo/'source.py').write_text('x = 1\n')
            git(repo,'add','source.py')
            git(repo,'-c','user.email=t@example.invalid','-c','user.name=T','commit','-qm','initial')
            code=[sys.executable,'-c',"from pathlib import Path; Path('source.py').write_text('x = 2\\n')"]
            test=[sys.executable,'-c',"from pathlib import Path; assert Path('source.py').read_text() == 'x = 2\\n'"]
            result=propose_code(repo,code,test,Path(root)/'artifacts',authorized=True)
            self.assertEqual(result.status,'passed')
            self.assertEqual((repo/'source.py').read_text(),'x = 1\n')
            self.assertEqual(len(list((Path(root)/'artifacts').glob('*.zip'))),1)
    def test_failed_verification_cannot_change_original(self):
        with tempfile.TemporaryDirectory() as root:
            repo=Path(root)/'repo';repo.mkdir()
            git(repo,'init','-q')
            (repo/'source.txt').write_text('before')
            git(repo,'add','source.txt')
            git(repo,'-c','user.email=t@example.invalid','-c','user.name=T','commit','-qm','initial')
            code=[sys.executable,'-c',"from pathlib import Path; Path('source.txt').write_text('after')"]
            test=[sys.executable,'-c','import sys;sys.exit(2)']
            result=propose_code(repo,code,test,Path(root)/'artifacts',authorized=True)
            self.assertEqual(result.status,'failed')
            self.assertEqual((repo/'source.txt').read_text(),'before')
            self.assertFalse((Path(root)/'artifacts').exists())
    def test_refuses_unapproved_execution(self):
        with self.assertRaises(PermissionError):propose_code('.',['cmd'],['test'],'/tmp')

if __name__=='__main__':unittest.main()
