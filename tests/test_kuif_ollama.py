import json
import pytest
from kuif.ollama import generate

class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size): return json.dumps({"response": "hello"}).encode()

def test_generate_mocked(monkeypatch):
    monkeypatch.setattr("kuif.ollama.urlopen", lambda request, timeout: FakeResponse())
    assert generate("qwen3.5:4b", "hi") == "hello"

def test_missing_model():
    with pytest.raises(ValueError):
        generate("", "hi")
