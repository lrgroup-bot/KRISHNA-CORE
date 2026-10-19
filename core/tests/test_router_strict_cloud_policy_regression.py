"""Ensure zero-credit routing cannot silently invoke paid cloud providers."""
import os
import unittest
from unittest.mock import patch

from krishna_core.router import ModelRouter


class TestStrictCloudPolicy(unittest.TestCase):
    def test_unverified_direct_cloud_blocked(self):
        with patch.dict(os.environ, {
            "KRISHNA_STRICT_ZERO_CREDIT": "1",
            "KRISHNA_ALLOW_PAID_CLOUD": "1",
        }):
            router = ModelRouter()
            for provider in ("openai", "anthropic", "gemini", "xai", "openrouter"):
                with self.subTest(provider=provider):
                    with self.assertRaises(PermissionError):
                        router.ask(provider, "test")

    def test_generic_gateway_blocked_even_when_present(self):
        class FakeGateway:
            def complete(self, *_args, **_kwargs):
                raise AssertionError("generic gateway must not be called")

        with patch.dict(os.environ, {"KRISHNA_STRICT_ZERO_CREDIT": "1"}):
            router = ModelRouter(gateway=FakeGateway())
            with self.assertRaises(PermissionError):
                router.ask("gateway:any", "test")

    def test_free_fabrics_fail_closed_when_unconfigured(self):
        router = ModelRouter()
        for provider in ("openrouter-free", "direct-free:cloudflare-workers-ai"):
            with self.subTest(provider=provider):
                with self.assertRaises(RuntimeError):
                    router.ask(provider, "test")


if __name__ == "__main__":
    unittest.main()
