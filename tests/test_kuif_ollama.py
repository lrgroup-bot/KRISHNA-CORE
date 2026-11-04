import json
import unittest
from unittest.mock import patch

from kuif.ollama import generate


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return json.dumps({"response": "hello"}).encode()


class KuifOllamaTests(unittest.TestCase):
    def test_generate_mocked(self):
        with patch("kuif.ollama.urlopen", lambda request, timeout: FakeResponse()):
            self.assertEqual(generate("qwen3.5:4b", "hi"), "hello")

    def test_missing_model(self):
        with self.assertRaises(ValueError):
            generate("", "hi")


if __name__ == "__main__":
    unittest.main()
