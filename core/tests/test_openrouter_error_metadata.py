import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from krishna_core.model_gateway import GatewayHTTPError, GatewayProfile, ModelGatewayRegistry, retry_after_seconds
from krishna_core.openrouter_free import OpenRouterFreeFabric


class ProviderMetadataTests(unittest.TestCase):
    def fabric(self, root):
        gateway = Mock()
        gateway.list.return_value = {'profiles':[{'id':'p','name':'OpenRouter-Free','base_url':'https://openrouter.ai/api/v1','enabled':True,'credential_available':True,'free_only':True}]}
        f = OpenRouterFreeFabric(gateway, root)
        f.rank = Mock(return_value=[{'id':'one/free'},{'id':'two/free'},{'id':'three/free'}])
        return f, gateway

    def test_gateway_exposes_only_status_and_bounded_retry_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            vault = SimpleNamespace(resolve=Mock(return_value='PRIVATE-CREDENTIAL'))
            gateway = ModelGatewayRegistry(Path(root)/'profiles.json', vault)
            gateway.profiles['p'] = GatewayProfile('p','test','https://openrouter.ai/api/v1','free','secret')
            error = urllib.error.HTTPError('https://secret.invalid',429,'PRIVATE-BODY',{'Retry-After':'120'},io.BytesIO(b'PRIVATE-BODY'))
            with patch.object(gateway,'_validate_url',side_effect=lambda x:x), patch('urllib.request.OpenerDirector.open',side_effect=error):
                with self.assertRaises(GatewayHTTPError) as caught:
                    gateway.request_json('p','/chat/completions',{},zero_credit_proof='openrouter-live-zero-price')
            self.assertEqual(caught.exception.status_code,429)
            self.assertEqual(caught.exception.retry_after_seconds,120)
            self.assertNotIn('PRIVATE',str(caught.exception))
            self.assertTrue(caught.exception.__suppress_context__)

    def test_retry_header_date_invalid_and_cap(self):
        self.assertEqual(retry_after_seconds('Mon, 19 Oct 2026 12:00:00 GMT',now=1792411140),60)
        self.assertEqual(retry_after_seconds('999999999'),86400)
        self.assertEqual(retry_after_seconds('-5'),0)
        self.assertIsNone(retry_after_seconds('private-untrusted-header'))

    def test_nonzero_or_unknown_key_spending_cap_blocks_post(self):
        for cap in (None, 1, 'NaN'):
            with self.subTest(cap=cap),tempfile.TemporaryDirectory() as root:
                gateway=ModelGatewayRegistry(Path(root)/'profiles.json',SimpleNamespace(resolve=lambda _: 'PRIVATE'))
                gateway.profiles['p']=GatewayProfile('p','test','https://openrouter.ai/api/v1','free','secret')
                response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
                response.read.return_value=json.dumps({'data':{'limit':cap}}).encode()
                with patch.object(gateway,'_validate_url',side_effect=lambda x:x),patch('urllib.request.OpenerDirector.open',return_value=response) as request:
                    with self.assertRaisesRegex(PermissionError,'spending cap'):
                        gateway.request_json('p','/chat/completions',{},zero_credit_proof='openrouter-live-zero-price')
                    self.assertEqual(request.call_count,1)
                    self.assertEqual(request.call_args.args[0].get_method(),'GET')

    def test_restart_honors_retry_after_and_exponential_cooldown(self):
        with tempfile.TemporaryDirectory() as root, patch('krishna_core.openrouter_free.time.time',return_value=1000):
            f,gateway = self.fabric(root)
            gateway.request_json.side_effect=GatewayHTTPError(429,300)
            with self.assertRaisesRegex(RuntimeError,'rate-limited'): f.complete('general','public',privacy='public')
            state=json.loads(f.failure_state_path.read_text())
            self.assertEqual(state['rate_limited_until'],1300)
            second,g2=self.fabric(root)
            with self.assertRaisesRegex(RuntimeError,'cooldown active'):second.complete('general','public',privacy='public')
            g2.request_json.assert_not_called()
            with patch('krishna_core.openrouter_free.time.time',return_value=1301):
                gateway.request_json.side_effect=GatewayHTTPError(429)
                with self.assertRaises(RuntimeError):f.complete('general','public',privacy='public')
            self.assertEqual(json.loads(f.failure_state_path.read_text())['rate_limited_until'],1421)

    def test_empty_reasoning_and_errors_never_leak_and_attempts_are_bounded(self):
        with tempfile.TemporaryDirectory() as root:
            f,gateway=self.fabric(root)
            gateway.request_json.side_effect=[{'choices':[{'message':{'content':'','reasoning':'PRIVATE-REASONING'}}]}, RuntimeError('PRIVATE-REQUEST')]
            with self.assertRaises(RuntimeError) as caught:f.complete('reasoning','public',privacy='public')
            self.assertNotIn('PRIVATE',str(caught.exception))
            self.assertIn('reasoning_only_completion',str(caught.exception))
            self.assertEqual(gateway.request_json.call_count,2)

    def test_account_errors_do_not_cascade_and_corrupt_state_fails_closed(self):
        for status in (401,402,503):
            with self.subTest(status=status),tempfile.TemporaryDirectory() as root:
                f,g=self.fabric(root);g.request_json.side_effect=GatewayHTTPError(status)
                with self.assertRaises(RuntimeError):f.complete('general','public',privacy='public')
                self.assertEqual(g.request_json.call_count,1)
        with tempfile.TemporaryDirectory() as root:
            f,g=self.fabric(root);f.failure_state_path.write_text('not json')
            with self.assertRaisesRegex(RuntimeError,'unreadable'):f.complete('general','public',privacy='public')
            g.request_json.assert_not_called()

    def test_explicit_model_is_single_attempt_and_image_role_is_enforced(self):
        with tempfile.TemporaryDirectory() as root:
            f,g=self.fabric(root);g.request_json.side_effect=GatewayHTTPError(404)
            with self.assertRaises(RuntimeError):f.complete('general','public',privacy='public',preferred_model='one/free')
            self.assertEqual(g.request_json.call_count,1)
            with self.assertRaises(ValueError):f.complete('general','public',privacy='public',image_data_url='data:image/png;base64,AA')

    def test_final_text_parts_are_parsed_without_reasoning(self):
        with tempfile.TemporaryDirectory() as root:
            f,g=self.fabric(root)
            g.request_json.return_value={'choices':[{'message':{'content':[{'type':'text','text':'public answer'}],'reasoning':'PRIVATE'}}]}
            value=f.complete('general','public',privacy='public')
            self.assertEqual(value['text'],'public answer')
            self.assertNotIn('PRIVATE',json.dumps(value))

