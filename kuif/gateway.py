"""Minimal model endpoint selector; does not execute untrusted URLs."""
from dataclasses import dataclass
from urllib.parse import urlsplit

@dataclass(frozen=True)
class ModelEndpoint:
    name: str
    url: str
    kind: str = "local"

def validate_endpoint(endpoint: ModelEndpoint) -> None:
    parsed = urlsplit(endpoint.url)
    if endpoint.kind != "local":
        raise ValueError("Cloud endpoints are disabled by default")
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Only loopback HTTP endpoints are permitted")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Credentials and fragments are not permitted")
    if parsed.port != 11434:
        raise ValueError("Unexpected model server port")

DEFAULT_ENDPOINT = ModelEndpoint("ollama", "http://127.0.0.1:11434")
validate_endpoint(DEFAULT_ENDPOINT)
