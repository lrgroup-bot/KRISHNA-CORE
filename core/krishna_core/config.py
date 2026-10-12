from dataclasses import dataclass
import os
from pathlib import Path

RUNTIME_ROOT = Path(os.getenv("KRISHNA_RUNTIME_ROOT", Path(__file__).resolve().parents[2])).resolve()


def _env_enabled(name: str, default: str = "1") -> bool:
    return str(os.getenv(name, default)).strip().lower() not in {"0", "false", "no", "off"}


# KRISHNA can run its full background fabric without being allowed to touch the
# machine-wide/shared Ollama service.  When disabled, use an intentionally
# unsupported URL scheme.  Legacy callers then fail immediately inside urllib
# without opening any socket, so status paths cannot spend seconds probing a
# closed port and KRISHNA can never reach the shared 127.0.0.1:11434 service.
_OLLAMA_ENABLED = _env_enabled("KRISHNA_OLLAMA_ENABLED", "1")
_OLLAMA_URL = (
    os.getenv("KRISHNA_OLLAMA_URL", "http://127.0.0.1:11434")
    if _OLLAMA_ENABLED
    else "disabled://krishna-ollama"
)


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("KRISHNA_HOST", "127.0.0.1")
    port: int = int(os.getenv("KRISHNA_PORT", "8766"))
    db_path: str = os.getenv("KRISHNA_DB", str(RUNTIME_ROOT / "krishna_core.db"))
    ollama_enabled: bool = _OLLAMA_ENABLED
    ollama_url: str = _OLLAMA_URL
    cloud_api_url: str = os.getenv("KRISHNA_CLOUD_API_URL", "")
    cloud_api_key: str = os.getenv("KRISHNA_CLOUD_API_KEY", "")
    allow_actions: bool = os.getenv("KRISHNA_ALLOW_ACTIONS", "0") == "1"

settings = Settings()
