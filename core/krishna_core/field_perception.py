from __future__ import annotations

from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class PerceptionCapability:
    id: str
    mode: str
    outputs: tuple[str, ...]
    limits: tuple[str, ...] = ()

    def as_dict(self):
        row=asdict(self)
        row["outputs"]=list(self.outputs)
        row["limits"]=list(self.limits)
        return row


class FieldPerceptionPolicy:
    """Privacy-bounded capability contract for live BHOOMIPUTRA perception."""

    CAPABILITIES=(
        PerceptionCapability(
            "structure-detail","building_structure",
            (
                "visible structural system and components",
                "floors/openings/facade/roof/access details",
                "apparent material class",
                "visible cracks/spalling/corrosion/deformation/dampness",
                "approximate geometry only when scale/depth evidence exists",
                "next viewpoint/scan recommendation",
            ),
            (
                "no certified load capacity from camera alone",
                "no hidden reinforcement/foundation claims without supporting evidence",
            ),
        ),
        PerceptionCapability(
            "people-scene","people",
            (
                "person count",
                "visible clothing/PPE",
                "pose/activity description",
                "face present/not-present",
                "local match to explicitly enrolled and consented identity profiles",
            ),
            (
                "do not identify unknown people",
                "do not infer sensitive traits",
                "face matching stays local and enrollment-scoped",
            ),
        ),
        PerceptionCapability(
            "ocr-assets","ocr",
            (
                "signage",
                "equipment labels",
                "serial/model numbers",
                "asset tags",
                "vehicle registration/plate text when requested",
                "dashboard/warning text",
            ),
            ("authentication secrets are always redacted",),
        ),
        PerceptionCapability(
            "vehicle-inspection","vehicle",
            (
                "vehicle category and visible make/model cues",
                "registration/asset marking when requested",
                "visible body/tyre/light/glass damage",
                "dashboard warning indicators",
                "leaks/smoke/obvious loose or damaged parts",
            ),
            (
                "camera observation alone is not a definitive mechanical diagnosis",
                "OBD/CAN/J1939 or measurement evidence is required for hidden faults",
            ),
        ),
        PerceptionCapability(
            "electronics-inspection","electronics",
            (
                "PCB/components/connectors/cables",
                "part labels and orientation",
                "visible burns/corrosion/broken traces/damaged connectors",
                "likely functional blocks and signal/power-flow explanation",
            ),
            (
                "do not claim hidden electrical values without measurements",
                "live voltage/current/fault confirmation requires instruments or device telemetry",
            ),
        ),
        PerceptionCapability(
            "terrain-site","terrain",
            (
                "rock/soil exposure",
                "slopes/cuts/drainage",
                "access roads and obstacles",
                "excavation/machinery activity",
                "survey gaps and next capture position",
            ),
            ("no mineral grade or reserve quantity from imagery alone",),
        ),
        PerceptionCapability(
            "hazard-watch","hazards",
            (
                "visible fire/smoke",
                "exposed wires",
                "obstacles/open edges",
                "fluid leaks",
                "missing visible PPE",
                "unstable-looking surface indicators",
            ),
            ("visual warning is not a certified safety inspection",),
        ),
        PerceptionCapability(
            "temporal-change","temporal",
            (
                "object entered/left scene",
                "movement/state change",
                "before/after visible differences",
                "repeat-observation consistency",
            ),
        ),
        PerceptionCapability(
            "sensitive-input-guard","sensitive_input",
            (
                "detect login/authentication surface",
                "detect that username/password/PIN/token entry is occurring",
                "warn about shoulder-surfing or camera exposure",
                "record redacted security event metadata only",
            ),
            (
                "never reconstruct, reveal, transcribe, store, sync or learn password/PIN/token/OTP values",
                "never use OCR to recover masked or partially hidden credentials",
            ),
        ),
    )

    @classmethod
    def catalog(cls):
        return [x.as_dict() for x in cls.CAPABILITIES]

    @classmethod
    def prompt_rules(cls):
        return (
            "Live-camera privacy/security rules: "
            "You may detect faces and describe visible non-sensitive scene facts. "
            "Identity matching is permitted only against explicitly enrolled, consented local profiles; "
            "otherwise report identity as UNKNOWN. Do not infer sensitive traits from a face. "
            "You may read ordinary visible text, signs, model numbers, asset tags and requested vehicle plates. "
            "If a login/authentication surface is visible, report only that credential entry is occurring and "
            "security risks such as shoulder-surfing. NEVER transcribe, reconstruct, reveal, retain, repeat, "
            "sync or learn passwords, PINs, OTPs, API keys, session tokens or other authentication secrets, "
            "even if characters are visible in the camera frame. Redact them as [SECRET REDACTED]."
        )

    @classmethod
    def redact_sensitive_text(cls,text):
        value=str(text or "")
        patterns=(
            r"(?i)\b(password|passwd|pwd)\s*[:=]\s*[^\s,;]+",
            r"(?i)\b(pin|otp)\s*[:=]\s*[A-Za-z0-9._-]+",
            r"(?i)\b(api[_ -]?key|access[_ -]?token|session[_ -]?token|bearer)\s*[:= ]\s*[A-Za-z0-9._~+\-/=]{4,}",
            r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._~+\-/=]{4,}",
        )
        for pattern in patterns:
            value=re.sub(
                pattern,
                lambda m: (m.group(1)+": [SECRET REDACTED]") if m.lastindex else "[SECRET REDACTED]",
                value,
            )
        return value

    @classmethod
    def redact_sensitive_value(cls,value,key=""):
        """Recursively redact secret-bearing metadata before it reaches ledgers."""
        raw_key=str(key or "").strip().lower()
        compact="".join(ch for ch in raw_key if ch.isalnum())
        sensitive={
            "password","passwd","pwd","pin","otp","secret","token","apikey",
            "accesstoken","refreshtoken","sessiontoken","authorization","credential","credentials",
        }
        if compact in sensitive or compact.endswith(("password","secret","token","apikey","credential","credentials")):
            return "[SECRET REDACTED]"
        if isinstance(value,dict):
            return {str(k):cls.redact_sensitive_value(v,k) for k,v in value.items()}
        if isinstance(value,(list,tuple,set)):
            return [cls.redact_sensitive_value(v,key) for v in value]
        if isinstance(value,str):
            return cls.redact_sensitive_text(value)
        return value

    @classmethod
    def status(cls):
        return {
            "owner":"KRISHNA HAWKEYE/BHOOMIPUTRA",
            "policy":"local-first privacy-bounded perception",
            "capabilities":cls.catalog(),
            "face_recognition":{
                "supported_scope":"explicitly enrolled + consented local profiles only",
                "unknown_person_identity":"UNKNOWN",
                "cloud_biometrics":False,
                "identity_adapter_state":"adapter_required",
            },
            "sensitive_input_guard":{
                "detect_login_surface":True,
                "detect_secret_entry_event":True,
                "return_secret_value":False,
                "store_secret_value":False,
                "sync_secret_value":False,
                "learning_secret_value":False,
                "redaction":"[SECRET REDACTED]",
            },
        }
