"""Provisioning must preserve data, obey headroom and avoid paid inference."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from suryadev_setup import provision, STATE
from suryadev_operator_api import handle_operator_action

class ComponentSetupTests(unittest.TestCase):
    def setUp(self):
        ocr=patch('suryadev_setup.tesseract_path',return_value='installed-tesseract')
        ocr.start()
        self.addCleanup(ocr.stop)
    def test_existing_local_model_never_downloads_or_changes_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'data'; root.mkdir()
            evidence=root/'existing.receipt'; evidence.write_bytes(b'original')
            with patch('suryadev_setup.subprocess.run') as install:
                outcome=provision(root,Path(folder),installed=lambda:True,
                                  measure=lambda _:self.fail('No hardware probe needed'))
            self.assertEqual(outcome['state'],'ready')
            install.assert_not_called()
            self.assertEqual(evidence.read_bytes(),b'original')
            self.assertFalse(outcome['learning_verified'])

    def test_high_resource_usage_defers_before_network_or_install(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'data'; root.mkdir()
            with patch('suryadev_setup._local') as network, patch('suryadev_setup.subprocess.run') as install:
                result=provision(root,folder,installed=lambda:False,
                    measure=lambda _:{'available':True,'cpu_percent':86,'ram_percent':50,
                    'ram_total_gb':16,'ram_used_gb':8,'disk_free_gb':100})
            self.assertEqual(result['state'],'deferred_hardware')
            network.assert_not_called(); install.assert_not_called()

    def test_pairing_ui_dispatches_to_pinned_credential_protocol(self):
        with patch('suryadev_pairing_bootstrap.request_pairing',return_value={'state':'owner_approval_required'}) as request:
            response=handle_operator_action('data','/api/operator/pairing/request',{
                'endpoint':'https://192.168.1.10:8767','cert_sha256':'a'*64,
                'device_id':'suryadev-test-1'})
            self.assertEqual(response['state'],'owner_approval_required')
            request.assert_called_once_with('data','https://192.168.1.10:8767','a'*64,'suryadev-test-1')

    def test_failed_runtime_verification_cannot_claim_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'data'; root.mkdir()
            with patch('suryadev_setup._local',side_effect=ValueError('bad local service')), patch('suryadev_setup.subprocess.run',side_effect=OSError('signature rejected')):
                response=provision(root,folder,installed=lambda:False,
                    measure=lambda _:{'available':True,'cpu_percent':10,'ram_percent':25,
                    'ram_total_gb':16,'ram_used_gb':4,'disk_free_gb':100})
            self.assertIn(response['state'],('blocked','needs_local_runtime'))
            self.assertFalse(response['learning_verified'])

if __name__=='__main__': unittest.main()
