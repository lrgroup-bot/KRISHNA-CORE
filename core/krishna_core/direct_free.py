from __future__ import annotations

import json
import re
import time


class VerifiedFreePolicyError(PermissionError):
    pass


class VerifiedDirectFreeFabric:
    """Native direct-provider adapters that can prove zero-billing eligibility.

    A provider is eligible for KRISHNA automatic routing only when the adapter can
    verify, immediately before inference, that the configured account cannot roll
    into paid usage. A human-applied free_only label is never sufficient.

    Cloudflare Workers AI is the first supported direct provider because Workers
    Free has a hard daily allocation, paid-only models fail on Free, and an API
    token with Billing Read can list account subscriptions so KRISHNA can refuse
    inference when a Workers paid subscription is active.
    """

    PROVIDER = "cloudflare-workers-ai"
    PROVIDER_ID = "direct-free:cloudflare-workers-ai"
    CLOUDFLARE_ROOT = "https://api.cloudflare.com/client/v4/accounts/"
    FREE_NEURONS_PER_DAY = 10_000
    CACHE_SECONDS = 60

    PAID_ONLY_MODELS = {
        "@cf/moonshotai/kimi-k2.6",
        "@cf/moonshotai/kimi-k2.7-code",
        "@cf/zai-org/glm-5.2",
        "@cf/zai-org/glm-5.3",
        "@cf/zai-org/glm-5.3-flash",
        "@cf/deepseek-ai/deepseek-v4-flash-0731",
        "@cf/deepseek-ai/deepseek-v4-pro-0813",
    }

    SECRET_PATTERNS = (
        re.compile(r"(?i)\b(password|passwd|pwd|api[_ -]?key|secret|token|authorization)\s*[:=]\s*\S+"),
        re.compile(r"(?i)\bbearer\s+[a-z0-9._~+\-/]+=*"),
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
        re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    )

    def __init__(self, gateway):
        self.gateway = gateway
        self._verification_cache = {}

    @classmethod
    def _cloudflare_account_id(cls, base_url):
        base = str(base_url or "").rstrip("/")
        if not base.startswith(cls.CLOUDFLARE_ROOT):
            return None
        suffix = base[len(cls.CLOUDFLARE_ROOT):]
        if not suffix or "/" in suffix or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", suffix):
            return None
        return suffix

    def _candidate_profiles(self):
        try:
            rows = list((self.gateway.list() or {}).get("profiles") or [])
        except Exception:
            return []
        out = []
        for row in rows:
            if not (
                row.get("enabled")
                and row.get("credential_available")
                and row.get("free_only")
                and self._cloudflare_account_id(row.get("base_url"))
            ):
                continue
            model = str(row.get("model") or "").strip()
            if not model.startswith("@cf/"):
                continue
            out.append(dict(row))
        out.sort(key=lambda x: -float(x.get("created_at") or 0))
        return out

    def configured(self):
        return bool(self._candidate_profiles())

    @staticmethod
    def _active_subscription(row):
        return str(row.get("state") or "").strip().lower() not in {
            "cancelled", "canceled", "failed", "expired",
        }

    @classmethod
    def _workers_subscription(cls, row):
        plan = dict(row.get("rate_plan") or {})
        text = " ".join([
            str(row.get("id") or ""),
            str(plan.get("id") or ""),
            str(plan.get("public_name") or ""),
            str(plan.get("scope") or ""),
            " ".join(str(x) for x in (plan.get("sets") or [])),
        ]).lower()
        return "worker" in text

    @classmethod
    def _workers_paid(cls, row):
        if not cls._active_subscription(row) or not cls._workers_subscription(row):
            return False
        plan = dict(row.get("rate_plan") or {})
        plan_id = str(plan.get("id") or "").strip().lower()
        try:
            price = float(row.get("price") or 0)
        except (TypeError, ValueError):
            price = 0.0
        return price > 0 or plan_id not in {"free", "partners_free"}

    @classmethod
    def _assert_payload_allowed(cls, privacy, text="", sensitive=False):
        privacy = str(privacy or "local_only").strip().lower()
        if privacy in {"local_only", "restricted"}:
            raise PermissionError("project privacy blocks direct cloud inference")
        if sensitive:
            raise PermissionError("sensitive payloads are local-only")
        probe = str(text or "")
        if any(pattern.search(probe) for pattern in cls.SECRET_PATTERNS):
            raise PermissionError("possible credential/secret detected; cloud inference blocked")
        return privacy

    def _verify_profile(self, row, *, refresh=True):
        profile_id = str(row.get("id") or "")
        model = str(row.get("model") or "").strip()
        now = time.time()
        cached = self._verification_cache.get(profile_id)
        if (
            not refresh and cached
            and now - float(cached.get("verified_at") or 0) <= self.CACHE_SECONDS
            and cached.get("model") == model
        ):
            return dict(cached)

        if model in self.PAID_ONLY_MODELS:
            raise VerifiedFreePolicyError(
                f"Cloudflare model {model} is documented as requiring Workers Paid/prepaid billing"
            )
        if not model.startswith("@cf/"):
            raise VerifiedFreePolicyError("only @cf/* Workers AI models are eligible")

        subscriptions = self.gateway.request_json(
            profile_id, "/subscriptions", method="GET", timeout=20
        )
        if not isinstance(subscriptions, dict) or subscriptions.get("success") is not True:
            raise VerifiedFreePolicyError("Cloudflare subscription verification did not return success=true")
        rows = subscriptions.get("result")
        if not isinstance(rows, list):
            raise VerifiedFreePolicyError("Cloudflare subscription verification returned an invalid result")

        workers = [dict(x) for x in rows if isinstance(x, dict) and self._workers_subscription(x)]
        paid = [x for x in workers if self._workers_paid(x)]
        if paid:
            raise VerifiedFreePolicyError(
                "Cloudflare Workers paid subscription detected; automatic zero-cost routing is disabled"
            )

        proof = {
            "provider": self.PROVIDER,
            "profile_id": profile_id,
            "model": model,
            "verified_at": now,
            "account_id": self._cloudflare_account_id(row.get("base_url")),
            "workers_subscriptions_seen": len(workers),
            "paid_workers_subscriptions_seen": 0,
            "free_allocation_neurons_per_day": self.FREE_NEURONS_PER_DAY,
            "billing_guard": "Billing Read subscription preflight + @cf-only + paid-model denylist",
        }
        self._verification_cache[profile_id] = dict(proof)
        return proof

    def verify(self, *, refresh=True):
        candidates = self._candidate_profiles()
        if not candidates:
            raise RuntimeError(
                "no Cloudflare Workers AI free-only profile is configured; use an account-root "
                "base URL and an API token with Workers AI + Billing Read permissions"
            )
        errors = []
        for row in candidates:
            try:
                proof = self._verify_profile(row, refresh=refresh)
                return row, proof
            except Exception as exc:
                errors.append({
                    "profile_id": row.get("id"),
                    "model": row.get("model"),
                    "error": f"{type(exc).__name__}: {exc}",
                })
        raise VerifiedFreePolicyError(
            "no Cloudflare profile passed zero-billing verification: "
            + json.dumps(errors, ensure_ascii=False)[:4000]
        )

    def complete(self, prompt, *, privacy="approved_cloud", sensitive=False, max_tokens=2048):
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("prompt is required")
        self._assert_payload_allowed(privacy, prompt, sensitive=sensitive)

        row, proof = self.verify(refresh=True)
        payload = {
            "model": row["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a bounded worker model for KRISHNA. Do not claim actions "
                        "or verification you did not perform."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max(1, min(int(max_tokens), 8192)),
            "temperature": 0.2,
            "options": {"rejectIfBusy": True},
        }
        data = self.gateway.request_json(
            row["id"], "/ai/v1/chat/completions", payload=payload, method="POST", timeout=120
        )
        choices = (data or {}).get("choices") or []
        text = str((((choices or [{}])[0].get("message") or {}).get("content") or ""))
        if not text.strip():
            raise RuntimeError("Cloudflare Workers AI returned an empty completion")
        return {
            "provider": self.PROVIDER,
            "provider_id": self.PROVIDER_ID,
            "profile_id": row["id"],
            "model": row["model"],
            "text": text,
            "privacy": str(privacy),
            "free_only": True,
            "zero_cost_verified": True,
            "zero_cost_proof": proof,
            "paid_fallback": False,
        }

    def status(self, refresh=False):
        candidates = self._candidate_profiles()
        result = {
            "provider": self.PROVIDER,
            "provider_id": self.PROVIDER_ID,
            "configured": bool(candidates),
            "automatic_zero_cost_eligible": False,
            "free_allocation_neurons_per_day": self.FREE_NEURONS_PER_DAY,
            "paid_fallback": "disabled",
            "privacy": "approved/public non-sensitive work only",
            "requirements": [
                "Cloudflare account-root gateway profile",
                "free_only=true",
                "@cf/* Workers AI model",
                "API token with Workers AI access and Billing Read",
                "no active Workers paid subscription",
            ],
            "profiles": [
                {
                    "id": x.get("id"),
                    "name": x.get("name"),
                    "model": x.get("model"),
                    "account_id": self._cloudflare_account_id(x.get("base_url")),
                }
                for x in candidates
            ],
        }
        if refresh and candidates:
            try:
                _, proof = self.verify(refresh=True)
                result["automatic_zero_cost_eligible"] = True
                result["verification"] = proof
            except Exception as exc:
                result["verification_error"] = f"{type(exc).__name__}: {exc}"
        elif candidates:
            valid = []
            now = time.time()
            for row in candidates:
                cached = self._verification_cache.get(str(row.get("id") or ""))
                if cached and now - float(cached.get("verified_at") or 0) <= self.CACHE_SECONDS:
                    valid.append(cached)
            if valid:
                result["automatic_zero_cost_eligible"] = True
                result["verification"] = dict(valid[0])
        return result
