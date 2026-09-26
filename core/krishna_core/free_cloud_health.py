from __future__ import annotations

import os
import time
from urllib.parse import urlparse


class FreeCloudHealthGovernor:
    """Fail-closed health and billing-safety view over KRISHNA cloud profiles.

    This component never starts a background worker and never performs inference.
    A refresh uses metadata/catalog endpoints only. Provider connectivity and
    credential health are kept separate from billing safety.
    """

    VERSION = "free-cloud-health-v1"
    CACHE_SECONDS = 300

    def __init__(self, gateway, openrouter_free=None, direct_free=None):
        self.gateway = gateway
        self.openrouter_free = openrouter_free
        self.direct_free = direct_free
        self._cache = None

    @staticmethod
    def _family(row):
        base = str(row.get("base_url") or "").lower()
        name = str(row.get("name") or "").lower()
        if "openrouter.ai" in base:
            return "kimi-openrouter" if "kimi" in name else "openrouter"
        if "cloudflare.com/client/v4/accounts/" in base:
            return "cloudflare"
        if "generativelanguage.googleapis.com" in base or "gemini" in name:
            return "gemini"
        if "api.groq.com" in base or "groq" in name:
            return "groq"
        if "api.cerebras.ai" in base or "cerebras" in name:
            return "cerebras"
        if "router.huggingface.co" in base or "huggingface" in name:
            return "huggingface"
        if "api.mistral.ai" in base or "mistral" in name:
            return "mistral"
        if "integrate.api.nvidia.com" in base or "nvidia" in name:
            return "nvidia"
        return (urlparse(base).hostname or "unknown").lower()

    @staticmethod
    def _metadata_path(family):
        # These configured profiles are OpenAI-compatible. GET /models is a
        # metadata-only authentication/connectivity probe and does not generate
        # tokens. Provider-specific adapters remain authoritative for inference.
        if family in {"gemini", "groq", "cerebras", "huggingface", "mistral"}:
            return "/models"
        return None

    @staticmethod
    def _trusted_owner_declared():
        raw = str(os.getenv("KRISHNA_TRUST_DECLARED_FREE_PROVIDERS") or "")
        return {x.strip().lower() for x in raw.split(",") if x.strip()}

    def _openrouter_status(self, refresh):
        if not self.openrouter_free:
            return {"configured": False, "error": "OpenRouter zero-cost fabric not bound"}
        try:
            return self.openrouter_free.status(refresh=refresh)
        except Exception as exc:
            return {"configured": False, "error": f"{type(exc).__name__}: {exc}"}

    def _cloudflare_status(self, refresh):
        if not self.direct_free:
            return {"configured": False, "error": "verified direct-free fabric not bound"}
        try:
            return self.direct_free.status(refresh=refresh)
        except Exception as exc:
            return {"configured": False, "error": f"{type(exc).__name__}: {exc}"}

    def _kimi_zero_cost(self, model, refresh):
        if not self.openrouter_free:
            return False, "OpenRouter zero-cost fabric not bound"
        try:
            row = self.openrouter_free._find_catalog_row(str(model), refresh=refresh)
            if not row:
                return False, "configured Kimi model not present in OpenRouter live catalog"
            if self.openrouter_free._expired(row):
                return False, "configured Kimi model is expired"
            if not self.openrouter_free._pricing_zero(row.get("pricing")):
                return False, "configured Kimi model is not live-zero-price"
            return True, None
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    def _probe_generic(self, row, family):
        path = self._metadata_path(family)
        if not path:
            return {"checked": False, "healthy": False, "error": "no metadata-only probe configured"}
        try:
            data = self.gateway.request_json(row["id"], path, method="GET", timeout=15)
            models = list((data or {}).get("data") or [])
            wanted = str(row.get("model") or "")
            ids = {str(x.get("id") or x.get("name") or "") for x in models if isinstance(x, dict)}
            return {
                "checked": True,
                "healthy": True,
                "model_visible": (wanted in ids) if ids and wanted else None,
                "model_count": len(models),
                "error": None,
            }
        except Exception as exc:
            return {
                "checked": True,
                "healthy": False,
                "model_visible": None,
                "model_count": None,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _classify(self, row, family, refresh, openrouter_status, cloudflare_status):
        credential = bool(row.get("credential_available"))
        declared = bool(row.get("free_only"))
        connectivity = {"checked": False, "healthy": credential, "error": None}
        billing = "unverified"
        unattended = False
        reason = "billing safety cannot be proven from this provider profile"

        if family == "openrouter":
            catalog = dict(openrouter_status.get("catalog") or {})
            healthy = bool(openrouter_status.get("configured")) and not bool(catalog.get("error"))
            if refresh:
                healthy = healthy and bool(catalog.get("fetched_at"))
            connectivity = {"checked": bool(refresh), "healthy": healthy, "error": catalog.get("error")}
            billing = "verified-live-zero-price-catalog"
            unattended = bool(healthy and declared)
            reason = "OpenRouter inference requires live zero-price model preflight and blocks non-zero provider cost"
        elif family == "cloudflare":
            healthy = bool(cloudflare_status.get("configured"))
            error = cloudflare_status.get("verification_error") or cloudflare_status.get("error")
            verified_now = bool(cloudflare_status.get("automatic_zero_cost_eligible"))
            connectivity = {"checked": bool(refresh), "healthy": healthy and not bool(error), "error": error}
            billing = "verified-account-zero-billing-preflight"
            # The direct-free completion path itself always re-runs the billing
            # subscription guard before inference. A configured profile is safe
            # to attempt unattended even when status() has no cached proof yet.
            unattended = bool(connectivity["healthy"] and declared)
            reason = (
                "Cloudflare direct-free execution rechecks Billing Read/subscription state before inference"
                + ("; current status has a cached/live proof" if verified_now else "; proof is obtained at execution time")
            )
        elif family == "kimi-openrouter":
            ok, error = self._kimi_zero_cost(row.get("model"), refresh=refresh)
            connectivity = {"checked": bool(refresh), "healthy": bool(ok and credential), "error": error}
            billing = "delegate-to-openrouter-zero-cost-fabric"
            unattended = False
            reason = (
                "Keep this duplicate gateway profile out of generic unattended routing; "
                "use the OpenRouter zero-cost fabric, which rechecks the exact model price before inference"
            )
        else:
            if refresh and credential:
                connectivity = self._probe_generic(row, family)
            elif not credential:
                connectivity = {"checked": False, "healthy": False, "error": "encrypted credential reference unavailable"}

            if family == "huggingface":
                billing = "credit-limited-not-zero-cost-guaranteed"
                unattended = False
                reason = "Hugging Face routed inference uses monthly credits and may support paid continuation; keep manual/fail-closed"
            elif family == "nvidia":
                billing = "development-tier-not-production-zero-cost-guaranteed"
                unattended = False
                reason = "NVIDIA is optional and not required by KRISHNA's current local/free fabric"
            else:
                billing = "owner-declared-free-tier"
                trusted = family in self._trusted_owner_declared()
                unattended = bool(declared and credential and connectivity.get("healthy") and trusted)
                reason = (
                    "healthy credential plus owner-declared free tier; unattended use requires explicit "
                    "KRISHNA_TRUST_DECLARED_FREE_PROVIDERS opt-in because account billing tier is not machine-proven"
                )

        return {
            "profile_id": row.get("id"),
            "name": row.get("name"),
            "family": family,
            "model": row.get("model"),
            "base_url": row.get("base_url"),
            "enabled": bool(row.get("enabled")),
            "credential_available": credential,
            "free_only_declared": declared,
            "connectivity": connectivity,
            "billing_safety": billing,
            "unattended_allowed": bool(unattended and row.get("enabled")),
            "reason": reason,
        }

    def status(self, refresh=False, max_age=None):
        max_age = self.CACHE_SECONDS if max_age is None else max(0, int(max_age))
        now = time.time()
        if (
            not refresh and self._cache
            and now - float(self._cache.get("checked_at") or 0) <= max_age
        ):
            return dict(self._cache)

        profiles = list((self.gateway.list() or {}).get("profiles") or [])
        openrouter_status = self._openrouter_status(bool(refresh))
        cloudflare_status = self._cloudflare_status(bool(refresh))
        rows = []
        for row in profiles:
            family = self._family(row)
            rows.append(self._classify(row, family, bool(refresh), openrouter_status, cloudflare_status))

        unattended = [x for x in rows if x["unattended_allowed"]]
        manual = [x for x in rows if x["enabled"] and not x["unattended_allowed"]]
        result = {
            "component": "KRISHNA Free Cloud Health Governor",
            "version": self.VERSION,
            "checked_at": now,
            "network_refresh": bool(refresh),
            "background_workers": 0,
            "automatic_paid_fallback": False,
            "profiles": rows,
            "summary": {
                "configured": len(rows),
                "credential_available": sum(1 for x in rows if x["credential_available"]),
                "unattended_allowed": len(unattended),
                "manual_or_blocked": len(manual),
            },
            "automatic_route": [x["name"] for x in unattended],
            "manual_or_blocked": [x["name"] for x in manual],
            "nvidia": {
                "needed": False,
                "configured": any(x["family"] == "nvidia" for x in rows),
                "policy": "optional-disabled-unless-a-unique-capability-is-required",
            },
            "policy": {
                "health_is_not_billing_proof": True,
                "free_only_flag_is_not_billing_proof": True,
                "verified_zero_cost_first": True,
                "private_or_sensitive_data": "local-only",
                "generic_provider_probe": "metadata-only /models; no inference tokens",
                "owner_declared_opt_in_env": "KRISHNA_TRUST_DECLARED_FREE_PROVIDERS",
            },
        }
        self._cache = result
        return dict(result)
