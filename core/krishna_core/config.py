from dataclasses import dataclass
import json
import os
from pathlib import Path

RUNTIME_ROOT = Path(os.getenv("KRISHNA_RUNTIME_ROOT", Path(__file__).resolve().parents[2])).resolve()
_PORTS_PATH = Path(__file__).with_name("server_ports.json")
_PORTS = json.loads(_PORTS_PATH.read_text(encoding="utf-8"))
KRISHNA_CORE_PORT = int(_PORTS["krishna_core"])
KRISHNA_MOBILE_COMPANION_PORT = int(_PORTS["mobile_companion"])
KRISHNA_LAN_DISCOVERY_PORT = int(_PORTS["lan_discovery"])

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("KRISHNA_HOST", "127.0.0.1")
    port: int = int(os.getenv("KRISHNA_PORT", str(KRISHNA_CORE_PORT)))
    db_path: str = os.getenv("KRISHNA_DB", str(RUNTIME_ROOT / "krishna_core.db"))
    ollama_url: str = os.getenv("KRISHNA_OLLAMA_URL", "http://127.0.0.1:11434")
    cloud_api_url: str = os.getenv("KRISHNA_CLOUD_API_URL", "")
    cloud_api_key: str = os.getenv("KRISHNA_CLOUD_API_KEY", "")
    allow_actions: bool = os.getenv("KRISHNA_ALLOW_ACTIONS", "0") == "1"

settings = Settings()
