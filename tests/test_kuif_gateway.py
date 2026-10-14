import pytest
from kuif.gateway import DEFAULT_ENDPOINT, ModelEndpoint, validate_endpoint

def test_default_endpoint():
    validate_endpoint(DEFAULT_ENDPOINT)

@pytest.mark.parametrize("url", [
    "https://example.com:11434", "http://192.168.1.10:11434",
    "http://localhost:8000", "http://user:pass@localhost:11434",
    "http://localhost:abc", "http://localhost:11434/evil",
    "http://localhost:11434/?redirect=1",
])
def test_reject_unsafe_endpoint(url):
    with pytest.raises(ValueError):
        validate_endpoint(ModelEndpoint("unsafe", url))

def test_cloud_disabled():
    with pytest.raises(ValueError):
        validate_endpoint(ModelEndpoint("cloud", "http://localhost:11434", "cloud"))
