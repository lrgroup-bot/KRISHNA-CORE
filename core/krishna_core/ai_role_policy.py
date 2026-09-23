from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class AIRolePolicyStore:
    """Persistent owner-controlled mapping from KRISHNA work roles to AI providers.

    The role policy decides preference only. It never overrides privacy, free-only,
    credential, or paid-cloud controls enforced by ModelRouter/provider adapters.
    """

    MODES = {"auto", "prefer", "pin"}

    ROLE_CATALOG = {
        "general": {
            "title": "General conversation",
            "description": "Normal KRISHNA conversation, summaries and broad assistance.",
            "openrouter_role": "general",
        },
        "coding": {
            "title": "Coding / implementation",
            "description": "Write or modify code inside bounded candidate/shadow workflows.",
            "openrouter_role": "coding",
        },
        "reasoning": {
            "title": "Deep reasoning",
            "description": "Hard multi-step analysis and independent reasoning.",
            "openrouter_role": "reasoning",
        },
        "vision": {
            "title": "Vision / image understanding",
            "description": "Approved non-sensitive image understanding. Private HAWKEYE evidence remains local.",
            "openrouter_role": "vision",
        },
        "research": {
            "title": "Research synthesis",
            "description": "Synthesize public research gathered by Garuda/Garudanetra/Rishis.",
            "openrouter_role": "reasoning",
        },
        "medical_research": {
            "title": "Medical research",
            "description": "Public medical-literature synthesis only; personal health data remains local.",
            "openrouter_role": "medical",
        },
        "implementation": {
            "title": "Implementation worker",
            "description": "Primary implementation worker used by software-factory coding plans.",
            "openrouter_role": "coding",
        },
        "architecture_review": {
            "title": "Architecture reviewer",
            "description": "Independent architecture and system-design review.",
            "openrouter_role": "reasoning",
        },
        "bug_test_review": {
            "title": "Bug / test reviewer",
            "description": "Regression, test and defect review.",
            "openrouter_role": "coding",
        },
        "security_review": {
            "title": "Security reviewer",
            "description": "Defensive security review under KABACH policy.",
            "openrouter_role": "reasoning",
        },
    }

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data = {"schema": 1, "roles": {}}
        self.load_error = None
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
            roles = raw.get("roles") if isinstance(raw, dict) else None
            if not isinstance(roles, dict):
                raise ValueError("roles must be an object")
            cleaned = {}
            for role, value in roles.items():
                if role not in self.ROLE_CATALOG or not isinstance(value, dict):
                    continue
                cleaned[role] = self._validate_assignment(
                    role,
                    value.get("mode", "auto"),
                    value.get("provider"),
                    value.get("model"),
                )
            self._data = {"schema": 1, "roles": cleaned}
            self.load_error = None
        except Exception as exc:
            self._data = {"schema": 1, "roles": {}}
            self.load_error = f"{type(exc).__name__}: {exc}"

    def _save(self):
        if self.load_error:
            raise RuntimeError(
                "AI role policy file is unreadable; refusing to overwrite it: " + self.load_error
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="ai-role-policy-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @classmethod
    def _validate_assignment(cls, role, mode, provider=None, model=None):
        role = str(role or "").strip().lower()
        if role not in cls.ROLE_CATALOG:
            raise KeyError(f"unknown AI role: {role}")
        mode = str(mode or "auto").strip().lower()
        if mode not in cls.MODES:
            raise ValueError("mode must be one of: auto, prefer, pin")
        provider = str(provider or "").strip() or None
        model = str(model or "").strip() or None
        if mode == "auto":
            provider = None
            model = None
        elif not provider:
            raise ValueError("provider is required for prefer/pin mode")
        if model and provider not in {"ollama", "gpt4all"}:
            raise ValueError("model override is currently supported only for local Ollama/GPT4All providers")
        return {
            "mode": mode,
            "provider": provider,
            "model": model,
        }

    def set(self, role, mode="auto", provider=None, model=None):
        assignment = self._validate_assignment(role, mode, provider, model)
        role = str(role).strip().lower()
        if assignment["mode"] == "auto":
            self._data["roles"].pop(role, None)
        else:
            self._data["roles"][role] = assignment
        self._save()
        return self.get(role)

    def reset(self, role):
        return self.set(role, "auto")

    def get(self, role):
        role = str(role or "general").strip().lower()
        if role not in self.ROLE_CATALOG:
            role = "general"
        saved = dict(self._data.get("roles", {}).get(role) or {})
        assignment = {
            "role": role,
            **self.ROLE_CATALOG[role],
            "mode": saved.get("mode", "auto"),
            "provider": saved.get("provider"),
            "model": saved.get("model"),
        }
        return assignment

    def list(self):
        return [self.get(role) for role in self.ROLE_CATALOG]

    def status(self):
        return {
            "owner": "KRISHNA AI Role Policy",
            "schema": 1,
            "load_error": self.load_error,
            "modes": {
                "auto": "KRISHNA chooses under privacy/cost/capability policy.",
                "prefer": "Try the selected AI first, then safe fallback if it fails.",
                "pin": "Use only the selected AI for that role; otherwise STOP.",
            },
            "roles": self.list(),
            "safety": {
                "privacy_override": False,
                "paid_cloud_override": False,
                "free_only_override": False,
                "secret_egress_override": False,
            },
        }
