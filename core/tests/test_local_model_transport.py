import json
import unittest
from unittest.mock import Mock, patch
from krishna_core.local_model_transport import request_local_json, validate_local_url, _NoRedirect


class LocalModelTransportTests(unittest.TestCase):
    def test_private_prompts_cannot_target_remote_urls_or_redirects(self):
        for url in ('https://public.example/v1','http://192.168.0.100/api/generate','http://127.0.0.1@public.example','http://127.0.0.1/?secret=x'):
            with self.subTest(url=url), self.assertRaises(PermissionError):validate_local_url(url)
        self.assertEqual(validate_local_url('http://127.0.0.1:11434/api/generate'),'http://127.0.0.1:11434/api/generate')
        with self.assertRaises(PermissionError):_NoRedirect().redirect_request(None,None,302,'',{},'https://public.example')

    def test_proxy_is_disabled_and_response_is_bounded(self):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=b'{"response":"ok"}'
        opener=Mock();opener.open.return_value=response
        with patch('krishna_core.local_model_transport.urllib.request.build_opener',return_value=opener) as build:
            self.assertEqual(request_local_json('http://127.0.0.1:11434/api/generate',{'prompt':'private'}),{'response':'ok'})
        self.assertEqual(build.call_args.args[0].proxies,{})
        self.assertEqual(response.read.call_args.args[0],2*1024*1024+1)

    def test_overflow_and_busy_fail_before_network(self):
        with patch('krishna_core.local_model_transport.urllib.request.build_opener') as network:
            with self.assertRaises(ValueError):request_local_json('http://127.0.0.1:11434/api/generate',{'prompt':'x'*300000})
            slots=Mock();slots.acquire.return_value=False
            with patch('krishna_core.local_model_transport._SLOTS',slots),self.assertRaisesRegex(RuntimeError,'busy'):
                request_local_json('http://127.0.0.1:11434/api/generate',{'prompt':'hello'})
            network.assert_not_called();slots.release.assert_not_called()
