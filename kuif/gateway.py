"""Validated local Ollama endpoint configuration (not an inference client)."""
from dataclasses import dataclass
from urllib.parse import urlsplit

@dataclass(frozen=True)
class ModelEndpoint:
    name: str
    url: str
    kind: str = "local"

def validate_endpoint(endpoint: ModelEndpoint) -> None:
    if endpoint.kind != "local":
        raise ValueError("Cloud endpoints are disabled by default")
    try:
        parsed = urlsplit(endpoint.url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Malformed model endpoint") from exc
    if (parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
            or port != 11434
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment):
        raise ValueError("Only the local Ollama origin is permitted")

DEFAULT_ENDPOINT = ModelEndpoint("ollama", "http://127.0.0.1:11434")
validate_endpoint(DEFAULT_ENDPOINT)
