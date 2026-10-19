"""Real agent/action/staging/test/memory integration; model/network outputs are controlled fixtures."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from krishna_core.orchestrator import Orchestrator


class HybridRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
        (self.project/'calc.py').write_text('def add(a,b): return a-b\n')
        tests=self.project/'tests';tests.mkdir()
        (tests/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass Check(unittest.TestCase):\n def test_add(self): self.assertEqual(add(2,3),5)\n')
        self.env=patch.dict(os.environ,{'KRISHNA_BACKGROUND_SERVICES_ENABLED':'0','KRISHNA_STRICT_ZERO_CREDIT':'1'});self.env.start()
        self.orch=Orchestrator(db_path=str(self.root/'runtime.db'))
        self.orch.register_project('FIXTURE',str(self.project),privacy='local_only',allowed_actions=['hybrid.implementation.run','development.stage','development.verify'],verification_checks=['python-tests'])
        self.orch.router.available=Mock(return_value=[{'provider':'ollama','available':True,'local':True,'model':'local-fixture'}])
        self.orch.router.ask=Mock(return_value=json.dumps({'summary':'addition fix','files':[{'path':'calc.py','content':'def add(a,b): return a+b\n'}]}))
        self.orch.garuda.scout=Mock(return_value={'web':[{'url':'https://docs.python.org/3/','title':'Python docs'}],'github':[]})
        self.config=patch('krishna_core.config.settings',SimpleNamespace(allow_actions=True));self.config.start()

    def tearDown(self):
        self.config.stop();self.orch.close();self.env.stop();self.tmp.cleanup()

    def run_workflow(self, **overrides):
        payload={'task':'Fix PRIVATE-LOCAL-TASK addition defect','approve_build':True,**overrides}
        return self.orch.dispatch_action('hybrid.implementation.run',payload,project='FIXTURE',source='pc',actor='owner',approved=True)['result']

    def test_actual_local_pipeline_isolated_tests_and_candidate_learning(self):
        result=self.run_workflow()
        self.assertEqual(result['status'],'verified_candidate')
        self.assertFalse(result['production_modified'])
        self.assertFalse(result['learning']['trusted_learning'])
        self.assertIn('a-b',(self.project/'calc.py').read_text())
        self.orch.garuda.scout.assert_not_called()
        self.assertTrue(all(row['action_id'] for row in result['stage_receipts']))
        self.assertIn('rishi:gautama',{row['agent'] for row in result['stage_receipts']})
        self.assertTrue(result['tests']['passed'])
        audit=self.orch.agent_runtime.status()['execution_audit']
        developer=next(row for row in audit if row['agent_id']=='developer')
        self.assertEqual(developer['last_recorded_action']['action'],'development.verify')
        self.assertFalse(developer['full_workflow_verified'])
        receipts=self.orch.action_bus.recent(100)
        models=[row for row in receipts if row['action']=='model.complete']
        self.assertNotIn('PRIVATE-LOCAL-TASK',json.dumps(models))

    def test_only_separate_public_query_reaches_garuda_and_cloud_stays_off_for_private_project(self):
        result=self.run_workflow(approved_public_context=True,public_query='Python addition documentation',use_free_cloud=True)
        self.assertEqual(result['status'],'verified_candidate')
        self.orch.garuda.scout.assert_called_once_with('FIXTURE','Python addition documentation',5)
        self.assertFalse(result['cloud']['attempted'])
        self.assertFalse(result['review']['claim_verified'])

    def test_build_and_delegated_approval_gates(self):
        with self.assertRaises(PermissionError):
            self.orch.dispatch_action('hybrid.implementation.run',{'task':'fix'},project='FIXTURE',source='pc',approved=False)
        with self.assertRaises(PermissionError):
            self.orch.dispatch_action('hybrid.implementation.run',{'task':'fix'},project='FIXTURE',source='mobile',approved=True)
        self.orch.router.ask.assert_not_called()
        with self.assertRaises(TypeError):self.run_workflow(approve_build='true')

    def test_model_cannot_weaken_acceptance_tests(self):
        self.orch.router.ask.return_value=json.dumps({'files':[{'path':'tests/test_calc.py','content':'pass\n'}]})
        with self.assertRaises(PermissionError):self.run_workflow()
        self.assertIn('assertEqual',(self.project/'tests/test_calc.py').read_text())

    def test_one_real_mrityunjay_candidate_repair_and_retest(self):
        self.orch.router.ask.side_effect=[json.dumps({'files':[{'path':'calc.py','content':'def add(a,b): return a-b\n'}]}),json.dumps({'files':[{'path':'calc.py','content':'def add(a,b): return a+b\n'}]})]
        result=self.run_workflow()
        self.assertEqual(result['status'],'verified_candidate')
        self.assertTrue(any(row['agent']=='mrityunjay' and row['action']=='development.verify' for row in result['stage_receipts']))
        self.assertEqual(self.orch.router.ask.call_count,2)
        self.assertIn('a-b',(self.project/'calc.py').read_text())
