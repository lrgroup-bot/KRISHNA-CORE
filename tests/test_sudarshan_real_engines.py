import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tools.sudarshan_rea_client import analyze_javascript
from tools.sudarshan_mirofish_client import inspect_completed_simulation

class FakeReply:
    def __init__(self,data):self.stream=io.BytesIO(json.dumps(data).encode())
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.stream.read(n)
    def geturl(self):return 'http://127.0.0.1:5001/api/simulation/sim_1'

class EngineTests(unittest.TestCase):
    def test_rea_requires_authorization(self):
        with self.assertRaises(PermissionError):analyze_javascript('.',root='.',rea_executable='/missing')
    def test_rea_collects_real_command_output(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root);binary=p/'rea';binary.write_text('placeholder')
            with patch('tools.sudarshan_rea_client.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{"modules":["a"]}')):
                result=analyze_javascript(p,root=p,rea_executable=binary,authorized=True)
            self.assertEqual(result.status,'passed')
            self.assertTrue(result.evidence_id.startswith('sha256:'))
    def test_mirofish_must_be_local(self):
        with self.assertRaises(PermissionError):
            inspect_completed_simulation('sim_1','p',authorized=True,base_url='https://remote.example')
    def test_completed_simulation_evidence(self):
        sim={'success':True,'data':{'simulation_id':'sim_1','project_id':'p','status':'completed'}}
        rep={'success':True,'data':{'report_id':'report_1','simulation_id':'sim_1','status':'completed'}}
        def transport(url,timeout):return FakeReply(rep if '/report/' in url else sim)
        result=inspect_completed_simulation('sim_1','p',authorized=True,transport=transport)
        self.assertEqual(result.status,'passed')
        self.assertIn('hypothesis',result.summary)
    def test_real_engine_adapters_persist_replayable_raw_json(self):
        from tools.sudarshan_evidence_archive import verify, load
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            binary=p/'rea';binary.write_text('fixture')
            archive_root=(p/'records').resolve()
            with patch('tools.sudarshan_rea_client.subprocess.run',
                       return_value=SimpleNamespace(returncode=0,stdout='{"modules":["a"]}')):
                result=analyze_javascript(p,root=p,rea_executable=binary,
                      authorized=True,project_id='project-a',
                      evidence_root=archive_root)
            self.assertEqual(result.status,'passed')
            self.assertTrue(verify(archive_root,'project-a','REA',result.evidence_id))
            self.assertEqual(load(archive_root,'project-a','REA',result.evidence_id),
                             {'modules':['a']})
            sim={'success':True,'data':{'simulation_id':'sim_1','project_id':'project-a','status':'completed'}}
            rep={'success':True,'data':{'report_id':'report_1','simulation_id':'sim_1','status':'completed'}}
            fn=lambda url,timeout: FakeReply(rep if '/report/' in url else sim)
            out=inspect_completed_simulation('sim_1','project-a',authorized=True,
                                              transport=fn,evidence_root=archive_root)
            self.assertEqual(out.status,'passed')
            self.assertTrue(verify(archive_root,'project-a','MiroFish',out.evidence_id))
            self.assertEqual(load(archive_root,'project-a','MiroFish',out.evidence_id)
                             ['simulation']['simulation_id'],'sim_1')

    def test_scope_mismatch_fails_closed(self):
        sim={'success':True,'data':{'simulation_id':'sim_1','project_id':'other','status':'completed'}}
        with self.assertRaises(PermissionError):
            inspect_completed_simulation('sim_1','p',authorized=True,transport=lambda url,timeout:FakeReply(sim))

if __name__=='__main__':unittest.main()
