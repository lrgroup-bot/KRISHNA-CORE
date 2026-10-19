import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from krishna_core.openrouter_free import OpenRouterFreeFabric


class FreeModelDiversityTests(unittest.TestCase):
    def test_diverse_top_three_and_live_status_count(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = Mock()
            gateway.list.return_value = {"profiles": [{
                "id": "profile", "name": "OpenRouter-Free",
                "base_url": "https://openrouter.ai/api/v1",
                "enabled": True, "credential_available": True,
                "free_only": True, "created_at": 1,
            }]}
            models = []
            for name in ("nvidia/a:free", "nvidia/b:free", "google/c:free", "cohere/d:free"):
                models.append({
                    "id": name, "name": name, "context_length": 8192,
                    "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                    "pricing": {"prompt": "0", "completion": "0", "request": "0"},
                })
            gateway.request_json.return_value = {"data": models}
            fabric = OpenRouterFreeFabric(gateway, Path(directory))
            status = fabric.status(refresh=True)
            self.assertIsNone(status["catalog"]["error"])
            self.assertEqual(status["catalog"]["model_count"], 4)
            top = fabric.rank("general", limit=3)
            self.assertEqual(len({row["id"].split("/")[0] for row in top}), 3)

    def test_http_429_stops_fallback_and_cools_down(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = Mock()
            gateway.list.return_value = {"profiles": [{
                "id": "profile", "name": "OpenRouter-Free",
                "base_url": "https://openrouter.ai/api/v1",
                "enabled": True, "credential_available": True,
                "free_only": True, "created_at": 1,
            }]}
            fabric = OpenRouterFreeFabric(gateway, Path(directory))
            models = [
                {"id": "nvidia/a:free", "pricing": {"prompt": "0", "completion": "0"}},
                {"id": "google/b:free", "pricing": {"prompt": "0", "completion": "0"}},
            ]
            fabric.rank = Mock(return_value=models)
            gateway.request_json.side_effect = RuntimeError(
                "model gateway request failed without fallback: HTTPError: HTTP Error 429: Too Many Requests"
            )
            with self.assertRaisesRegex(RuntimeError, "rate-limited"):
                fabric.complete("general", "public test", privacy="public")
            self.assertEqual(gateway.request_json.call_count, 1)
            with self.assertRaisesRegex(RuntimeError, "cooldown active"):
                fabric.complete("general", "public test", privacy="public")
            self.assertEqual(gateway.request_json.call_count, 1)

    def test_nonzero_pricing_remains_blocked(self):
        self.assertFalse(OpenRouterFreeFabric._pricing_zero(
            {"prompt": "0", "completion": "0.00001", "request": "0"}))


if __name__ == "__main__":
    unittest.main()
