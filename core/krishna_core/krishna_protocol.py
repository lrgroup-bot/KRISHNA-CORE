from __future__ import annotations

from dataclasses import dataclass,asdict
from datetime import datetime,timezone
import uuid

KRISHNA_PROTOCOL_VERSION="1.0"
SURFACES=("desktop","mobile","cli","glass")
KINDS=("request","response","event","error")

@dataclass(frozen=True)
class ProtocolEnvelope:
    protocol_version:str
    message_id:str
    kind:str
    surface:str
    operation:str
    payload:dict
    created_at:str

    def as_dict(self):return asdict(self)

class KrishnaProtocol:
    """Stable UI/Core contract boundary independent of model/agent frameworks."""

    VERSION=KRISHNA_PROTOCOL_VERSION

    @classmethod
    def envelope(cls,kind,operation,payload=None,surface="desktop",message_id=None):
        kind=str(kind or "").lower();surface=str(surface or "").lower();operation=str(operation or "").strip()
        if kind not in KINDS:raise ValueError("invalid KRISHNA protocol kind")
        if surface not in SURFACES:raise ValueError("invalid KRISHNA protocol surface")
        if not operation:raise ValueError("KRISHNA protocol operation is required")
        return ProtocolEnvelope(
            cls.VERSION,str(message_id or uuid.uuid4()),kind,surface,operation,dict(payload or {}),
            datetime.now(timezone.utc).isoformat(),
        ).as_dict()

    @classmethod
    def validate(cls,message):
        msg=dict(message or {})
        if str(msg.get("protocol_version") or "")!=cls.VERSION:
            raise ValueError("KRISHNA protocol version mismatch")
        if str(msg.get("kind") or "").lower() not in KINDS:raise ValueError("invalid KRISHNA protocol kind")
        if str(msg.get("surface") or "").lower() not in SURFACES:raise ValueError("invalid KRISHNA protocol surface")
        if not str(msg.get("operation") or "").strip():raise ValueError("KRISHNA protocol operation is required")
        if not isinstance(msg.get("payload"),dict):raise ValueError("KRISHNA protocol payload must be an object")
        return msg

    @classmethod
    def status(cls):
        return {
            "protocol":"KRISHNA Protocol","version":cls.VERSION,
            "surfaces":list(SURFACES),"kinds":list(KINDS),
            "boundary":"UI -> KRISHNA Protocol -> Core -> runtime/model/tool adapters",
            "ui_framework_independence":True,
        }
