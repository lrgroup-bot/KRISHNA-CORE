"""Minimal synchronous local Ollama client. No cloud fallback."""
import json
from urllib.request import Request, urlopen
from .gateway import DEFAULT_ENDPOINT, ModelEndpoint, validate_endpoint

def generate(model: str, prompt: str, *, endpoint: ModelEndpoint = DEFAULT_ENDPOINT,
             timeout: float = 60.0) -> str:
    validate_endpoint(endpoint)
    if not model or not model.strip() or not isinstance(prompt, str):
        raise ValueError("Model and prompt are required")
    if not (0 < timeout <= 300):
        raise ValueError("Invalid timeout")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    request = Request(endpoint.url.rstrip("/") + "/api/generate", data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read(8_000_001))
    if not isinstance(data, dict) or not isinstance(data.get("response"), str):
        raise ValueError("Unexpected Ollama response")
    return data["response"]
