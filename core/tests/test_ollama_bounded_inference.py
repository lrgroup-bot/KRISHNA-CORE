"""Regression tests for bounded, loopback-safe Ollama generation."""
import json
import os
import unittest
from unittest.mock import patch

from krishna_core.router import ModelRouter


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=None):
        return json.dumps({"response": "KRISHNA CHAT READY"}).encode()


class TestBoundedOllama(unittest.TestCase):
    def test_bounded_payload_and_transport(self):
        captured = {}

        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data)
            captured["timeout"] = timeout
            return _Response()

        with patch("krishna_core.local_model_transport.urllib.request.OpenerDirector.open", side_effect=fake_open):
            with patch.dict(os.environ, {
                "KRISHNA_OLLAMA_ENABLED": "1",
                "KRISHNA_OLLAMA_NUM_CTX": "999999",
                "KRISHNA_OLLAMA_NUM_PREDICT": "999999",
            }):
                result = ModelRouter()._ollama_generate("granite3.3:2b", "Reply exactly")
        self.assertEqual(result, "KRISHNA CHAT READY")
        self.assertEqual(captured["body"]["options"]["num_ctx"], 8192)
        self.assertEqual(captured["body"]["options"]["num_predict"], 2048)
        self.assertFalse(captured["body"]["stream"])
        self.assertTrue(captured["url"].endswith("/api/generate"))
        self.assertEqual(captured["timeout"], 90)

    def test_invalid_limits_use_defaults(self):
        captured = {}

        def fake_open(request, timeout):
            captured.update(json.loads(request.data))
            return _Response()

        with patch("krishna_core.local_model_transport.urllib.request.OpenerDirector.open", side_effect=fake_open):
            with patch.dict(os.environ, {
                "KRISHNA_OLLAMA_ENABLED": "1",
                "KRISHNA_OLLAMA_NUM_CTX": "invalid",
                "KRISHNA_OLLAMA_NUM_PREDICT": "-1",
            }):
                ModelRouter()._ollama_generate("granite3.3:2b", "hello")
        self.assertEqual(captured["options"]["num_ctx"], 2048)
        self.assertEqual(captured["options"]["num_predict"], 32)


if __name__ == "__main__":
    unittest.main()
