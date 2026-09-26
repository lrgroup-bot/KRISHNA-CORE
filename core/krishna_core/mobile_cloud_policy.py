from __future__ import annotations

import re


class MobileCloudPolicy:
    """Conservative mobile-direct cloud classifier.

    This does not grant cloud access. It only says whether a request is eligible
    to use an already owner-approved short-lived free-cloud session.
    """

    SENSITIVE=re.compile(
        r"(?i)(password|passwd|\bpwd\b|api[ _-]?key|secret|token|authorization|"
        r"aadhaar|aadhar|pan card|bank account|credit card|debit card|otp|pin\b|"
        r"medical record|diagnosis|prescription|private document|biometric|face embedding)"
    )
    PC_ACTION=re.compile(
        r"(?i)\b(implement|install|delete|remove|modify|edit|fix|repair|audit|deploy|"
        r"restart|run|execute|commit|merge|push|pull|github|repository|repo|file|folder|"
        r"email|gmail|calendar|slack|whatsapp|payment|pay|buy|purchase|spend|transfer|"
        r"krishna project|kuber|manibhadra|narad|sudarshan|mrityunjay)\b"
    )
    STATEFUL=re.compile(r"(?i)\b(gita|geeta|shloka|verse|my project|my file|my chat|remember|last time)\b")

    @classmethod
    def classify(cls,text,*,attachments=0):
        value=str(text or "").strip()
        if not value:
            return {"eligible":False,"reason":"empty"}
        if attachments:
            return {"eligible":False,"reason":"attachments_require_private_core"}
        if len(value)>5000:
            return {"eligible":False,"reason":"long_request_requires_private_core"}
        if cls.SENSITIVE.search(value):
            return {"eligible":False,"reason":"sensitive"}
        if cls.PC_ACTION.search(value):
            return {"eligible":False,"reason":"action_or_project_control"}
        if cls.STATEFUL.search(value):
            return {"eligible":False,"reason":"krishna_state_required"}
        return {"eligible":True,"reason":"general_non_sensitive_conversation"}
