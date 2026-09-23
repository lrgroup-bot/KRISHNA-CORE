from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class AIRolePolicyStore:
    """Persistent owner-controlled mapping from KRISHNA work roles to AI providers.

    A role assignment changes routing preference only. It never overrides project
    privacy, local-only/restricted handling, verified-zero-cost policy, credential
    egress rules, or the global paid-cloud-disabled default.
    """

    MODES = {"auto", "prefer", "pin"}

    ROLE_CATALOG = {
        "general": {
            "title": "General conversation",
            "description": "Normal KRISHNA conversation, summaries and broad assistance.",
            "openrouter_role": "general",
            "auto_strategy": "local_first",
        },
        "coding": {
            "title": "Coding / implementation",
            "description": "Code generation and bounded implementation work.",
            "openrouter_role": "coding",
            "auto_strategy": "local_first",
        },
        "reasoning": {
            "title": "Deep reasoning",
            "description": "Hard multi-step analysis and independent reasoning.",
            "openrouter_role": "reasoning",
            "auto_strategy": "local_first",
        },
        "vision": {
            "title": "Vision / image understanding",
            "description": "Approved non-sensitive image understanding; private HAWKEYE evidence remains local.",
            "openrouter_role": "vision",
            "auto_strategy": "local_first",
        },
        "research": {
            "title": "Research synthesis",
            "description": "Synthesize public research gathered by KRISHNA research agents.",
            "openrouter_role": "reasoning",
            "auto_strategy": "local_first",
        },
        "medical_research": {
            "title": "Medical research",
            "description": "Public medical-literature synthesis only; personal health data remains local.",
            "openrouter_role": "medical",
            "auto_strategy": "local_first",
        },
        "implementation": {
            "title": "Implementation worker",
            "description": "Primary software-factory implementation worker.",
            "openrouter_role": "coding",
            "auto_strategy": "local_first",
        },
        "architecture_review": {
            "title": "Architecture reviewer",
            "description": "Independent architecture and system-design review.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
        "bug_test_review": {
            "title": "Bug / test reviewer",
            "description": "Regression, test and defect review.",
            "openrouter_role": "coding",
            "auto_strategy": "verified_cloud_first",
        },
        "security_review": {
            "title": "Security reviewer",
            "description": "Defensive security review under KABACH policy.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
        "rishi_research": {
            "title": "Rishi research",
            "description": "Source-grounded claim extraction and research analysis after Garuda discovery.",
            "openrouter_role": "reasoning",
            "auto_strategy": "local_first",
        },
        "rishi_counter_evidence": {
            "title": "Rishi counter-evidence",
            "description": "Independent challenge of candidate claims and source relationships.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
        "rishi_debate": {
            "title": "Rishi debate",
            "description": "Evidence-bound council debate using an independent reasoning model where privacy permits.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
        "gautama_review": {
            "title": "Gautama evidence review",
            "description": "Independent epistemic/citation sufficiency review.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
        "bharadvaja_test_plan": {
            "title": "Bharadvaja test planning",
            "description": "Falsifiable test/experiment design from evidence-backed claims.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
        "lab_hypothesis": {
            "title": "LAB hypothesis assistance",
            "description": "Generate an explicitly unverified, testable hypothesis candidate.",
            "openrouter_role": "reasoning",
            "auto_strategy": "local_first",
        },
        "lab_result_analysis": {
            "title": "LAB result analysis",
            "description": "Independent result interpretation without promoting findings to verified knowledge.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
        "vyasa_synthesis": {
            "title": "Veda Vyasa synthesis",
            "description": "Final source-grounded synthesis after challenge, debate and test planning.",
            "openrouter_role": "reasoning",
            "auto_strategy": "verified_cloud_first",
        },
    }

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data = {"schema": 2, "roles": {}}
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
            self._data = {"schema": 2, "roles": cleaned}
            self.load_error = None
        except Exception as exc:
            self._data = {"schema": 2, "roles": {}}
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
            raise ValueError("model override is supported only for local Ollama/GPT4All providers")
        return {"mode": mode, "provider": provider, "model": model}

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
        catalog = dict(self.ROLE_CATALOG[role])
        saved = dict(self._data.get("roles", {}).get(role) or {})
        return {
            "role": role,
            **catalog,
            "mode": saved.get("mode", "auto"),
            "provider": saved.get("provider"),
            "model": saved.get("model"),
        }

    def list(self):
        return [self.get(role) for role in self.ROLE_CATALOG]

    def status(self):
        return {
            "owner": "KRISHNA AI Role Policy",
            "schema": 2,
            "load_error": self.load_error,
            "modes": {
                "auto": "KRISHNA chooses under privacy/cost/capability policy.",
                "prefer": "Try the selected AI first, then safe fallback if it fails.",
                "pin": "Use only the selected AI for that role; otherwise STOP.",
            },
            "roles": self.list(),
            "research_separation": {
                "garuda": "source discovery and retrieval",
                "rishi_ai": "source-grounded interpretation/challenge",
                "lab": "bounded experiment planning/simulation/evidence",
                "brahma": "learning/QC and promotion governance",
                "gyan_bhandar": "approved knowledge storage",
            },
            "safety": {
                "privacy_override": False,
                "paid_cloud_override": False,
                "free_only_override": False,
                "secret_egress_override": False,
                "model_output_is_evidence": False,
            },
        }
