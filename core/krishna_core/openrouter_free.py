from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


class ZeroCostPolicyError(PermissionError):
    pass


class OpenRouterFreeFabric:
    """Single-key, zero-cost-only OpenRouter adapter for KRISHNA.

    One encrypted OpenRouter gateway profile is reused for catalog discovery,
    role-specific text/vision inference and zero-priced image generation.
    The adapter never exposes the API key and refuses local_only/restricted data.
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    IMAGE_MODEL = "inclusionai/ming-image-0.1-design"
    CACHE_SECONDS = 300
    MAX_IMAGE_BYTES = 32 * 1024 * 1024

    ROLE_HINTS = {
        "coding": (
            ("nex", 18), ("kimi", 16), ("north", 14), ("code", 12),
            ("laguna", 12), ("deepseek", 10), ("qwen", 8),
        ),
        "reasoning": (
            ("nemotron", 18), ("deepseek", 15), ("kimi", 13),
            ("qwen", 10), ("ling", 7),
        ),
        "vision": (
            ("ling-3.0-flash-vl", 30), ("vision", 18), ("inkling", 15),
            ("gemma", 10), ("omni", 10),
        ),
        "medical": (
            ("ling-3.0-flash-sante", 40), ("sante", 35),
            ("medical", 20), ("health", 15),
        ),
        "general": (
            ("kimi", 14), ("ling", 12), ("nemotron", 10),
            ("deepseek", 8), ("qwen", 8),
        ),
    }

    SECRET_PATTERNS = (
        re.compile(r"(?i)\b(password|passwd|pwd|api[_ -]?key|secret|token|authorization)\s*[:=]\s*\S+"),
        re.compile(r"(?i)\bbearer\s+[a-z0-9._~+\-/]+=*"),
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
        re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    )

    def __init__(self, gateway, state_root: str | Path):
        self.gateway = gateway
        self.state_root = Path(state_root)
        self.cache_path = self.state_root / "catalog.json"
        self.image_dir = self.state_root / "images"
        self._cache = None

    @staticmethod
    def _decimal(value):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    @classmethod
    def _pricing_zero(cls, pricing, *, vision=False, image_output=False):
        pricing = dict(pricing or {})
        required = ("prompt", "completion")
        if image_output:
            # Image models may report token-style or generation-specific pricing.
            # Missing/opaque pricing is never interpreted as free.
            required = ()
        for key in required:
            value = cls._decimal(pricing.get(key))
            if value is None or value != 0:
                return False

        relevant = {
            "prompt", "completion", "request", "internal_reasoning",
            "image", "images", "output_image", "audio", "video",
        }
        if not vision and not image_output:
            relevant.discard("image")
        numeric_seen=0
        for key, raw in pricing.items():
            if key not in relevant:
                continue
            value = cls._decimal(raw)
            if value is None:
                continue
            numeric_seen+=1
            if value != 0:
                return False
        if image_output and numeric_seen==0:
            return False
        return True

    @staticmethod
    def _expiration_timestamp(value):
        if value in (None, "", 0):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        try:
            return float(text)
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    @classmethod
    def _expired(cls, row):
        ts = cls._expiration_timestamp(row.get("expiration_date"))
        return bool(ts is not None and ts <= time.time())

    @classmethod
    def _expires_soon(cls, row, days=7):
        ts = cls._expiration_timestamp(row.get("expiration_date"))
        return bool(ts is not None and ts <= time.time() + days * 86400)

    def _profiles(self):
        rows = []
        try:
            rows = list((self.gateway.list() or {}).get("profiles") or [])
        except Exception:
            return []
        out = []
        for row in rows:
            base = str(row.get("base_url") or "").rstrip("/").lower()
            if (
                row.get("enabled")
                and row.get("credential_available")
                and row.get("free_only")
                and base == self.BASE_URL.lower()
            ):
                out.append(dict(row))
        out.sort(key=lambda x: (
            0 if str(x.get("name") or "").lower() == "openrouter-free" else 1,
            -float(x.get("created_at") or 0),
        ))
        return out

    def profile(self):
        rows = self._profiles()
        return rows[0] if rows else None

    def configured(self):
        return self.profile() is not None

    def _assert_cloud_allowed(self, privacy, text="", sensitive=False):
        privacy = str(privacy or "local_only").strip().lower()
        if privacy in {"local_only", "restricted"}:
            raise PermissionError("project privacy blocks OpenRouter cloud inference")
        if sensitive:
            raise PermissionError("sensitive payloads are local-only")
        probe = str(text or "")
        if any(pattern.search(probe) for pattern in self.SECRET_PATTERNS):
            raise PermissionError("possible credential/secret detected; cloud inference blocked")
        return privacy

    def _read_cache(self):
        if self._cache:
            return self._cache
        if not self.cache_path.exists():
            return None
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8-sig"))
            if isinstance(raw, dict) and isinstance(raw.get("models"), list):
                self._cache = raw
                return raw
        except Exception:
            return None
        return None

    def _write_cache(self, rows):
        self.state_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": 1,
            "fetched_at": time.time(),
            "source": self.BASE_URL + "/models",
            "models": rows,
        }
        fd, tmp = tempfile.mkstemp(prefix="openrouter-catalog-", suffix=".json", dir=str(self.state_root))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, self.cache_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self._cache = payload
        return payload

    def catalog(self, refresh=False, max_age=None):
        profile = self.profile()
        if not profile:
            raise RuntimeError("OpenRouter-Free gateway profile is not configured")
        max_age = self.CACHE_SECONDS if max_age is None else max(0, int(max_age))
        cached = self._read_cache()
        if not refresh and cached and time.time() - float(cached.get("fetched_at") or 0) <= max_age:
            return cached
        data = self.gateway.request_json(profile["id"], "/models", method="GET", timeout=30)
        rows = list((data or {}).get("data") or [])
        return self._write_cache(rows)

    def _free_rows(self, *, role="general", refresh=False):
        rows = list(self.catalog(refresh=refresh).get("models") or [])
        role = str(role or "general").strip().lower()
        out = []
        for row in rows:
            if self._expired(row):
                continue
            architecture = dict(row.get("architecture") or {})
            inputs = set(architecture.get("input_modalities") or [])
            outputs = set(architecture.get("output_modalities") or [])
            vision = role == "vision"
            if vision and "image" not in inputs:
                continue
            if outputs and "text" not in outputs:
                continue
            if not self._pricing_zero(row.get("pricing"), vision=vision):
                continue
            out.append(dict(row))
        return out

    def rank(self, role="general", limit=8, refresh=False):
        role = str(role or "general").strip().lower()
        hints = self.ROLE_HINTS.get(role, self.ROLE_HINTS["general"])
        rows = self._free_rows(role=role, refresh=refresh)

        def score(row):
            hay = (str(row.get("id") or "") + " " + str(row.get("name") or "")).lower()
            value = 0
            for term, weight in hints:
                if term in hay:
                    value += weight
            if str(row.get("id") or "").endswith(":free"):
                value += 8
            if str(row.get("id") or "") == "openrouter/free":
                value += 2
            params = set(row.get("supported_parameters") or [])
            if role in {"coding", "reasoning"} and "tools" in params:
                value += 4
            context = int(row.get("context_length") or 0)
            value += min(8, context // 131072)
            if self._expires_soon(row):
                value -= 30
            return value

        rows.sort(key=lambda row: (-score(row), -int(row.get("context_length") or 0), str(row.get("id") or "")))
        result = []
        for row in rows[:max(1, int(limit))]:
            architecture = dict(row.get("architecture") or {})
            result.append({
                "id": row.get("id"),
                "name": row.get("name"),
                "context_length": row.get("context_length"),
                "input_modalities": architecture.get("input_modalities") or [],
                "output_modalities": architecture.get("output_modalities") or [],
                "supported_parameters": row.get("supported_parameters") or [],
                "expiration_date": row.get("expiration_date"),
                "expires_soon": self._expires_soon(row),
                "pricing": row.get("pricing") or {},
                "score": score(row),
            })
        return result

    def role_plan(self, refresh=False):
        plan = {}
        for role in ("coding", "reasoning", "vision", "medical", "general"):
            rows = self.rank(role, 3, refresh=refresh)
            plan[role] = rows
        return plan

    @staticmethod
    def _usage_cost(data):
        usage = dict((data or {}).get("usage") or {})
        value = usage.get("cost")
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def complete(self, role, prompt, *, privacy="approved_cloud", sensitive=False,
                 image_data_url=None, max_tokens=2048):
        self._assert_cloud_allowed(privacy, prompt, sensitive=sensitive)
        role = str(role or "general").strip().lower()
        candidates = self.rank(role, 8, refresh=True)
        if not candidates:
            raise ZeroCostPolicyError(f"no live zero-cost OpenRouter model is eligible for role: {role}")
        profile = self.profile()
        errors = []
        for model in candidates:
            content = str(prompt)
            if image_data_url:
                if not str(image_data_url).startswith("data:image/"):
                    raise ValueError("vision input must be a local data:image URL; remote image URLs are not accepted")
                content = [
                    {"type": "text", "text": str(prompt)},
                    {"type": "image_url", "image_url": {"url": str(image_data_url)}},
                ]
            payload = {
                "model": model["id"],
                "messages": [
                    {"role": "system", "content": "You are a bounded worker model for KRISHNA. Do not claim actions or verification you did not perform."},
                    {"role": "user", "content": content},
                ],
                "max_tokens": max(1, min(int(max_tokens), 8192)),
                "temperature": 0.2,
                "provider": {"allow_fallbacks": False},
            }
            try:
                data = self.gateway.request_json(profile["id"], "/chat/completions", payload=payload, method="POST", timeout=120)
                cost = self._usage_cost(data)
                if cost is not None and cost != 0:
                    raise ZeroCostPolicyError(f"provider reported non-zero cost for supposedly free model {model['id']}: {cost}")
                text = str((((data or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or "")
                if not text.strip():
                    raise RuntimeError("empty completion")
                return {
                    "provider": "openrouter",
                    "profile_id": profile["id"],
                    "role": role,
                    "model": model["id"],
                    "text": text,
                    "preflight_zero_cost": True,
                    "provider_reported_cost": None if cost is None else str(cost),
                    "privacy": str(privacy),
                }
            except ZeroCostPolicyError:
                raise
            except Exception as exc:
                errors.append({"model": model["id"], "error": f"{type(exc).__name__}: {exc}"})
                continue
        raise RuntimeError("all eligible zero-cost OpenRouter models failed: " + json.dumps(errors, ensure_ascii=False)[:6000])

    def _find_catalog_row(self, model_id, refresh=True):
        for row in self.catalog(refresh=refresh).get("models") or []:
            if str(row.get("id") or "") == str(model_id):
                return dict(row)
        return None

    def image_models(self, refresh=False):
        profile = self.profile()
        if not profile:
            return []
        data = self.gateway.request_json(profile["id"], "/images/models", method="GET", timeout=30) if refresh else None
        if data is None:
            # Do not spend a request merely for status. The canonical Ming target is
            # advertised only when the general catalog already confirms zero cost.
            row = self._find_catalog_row(self.IMAGE_MODEL, refresh=False) if self._read_cache() else None
            return [] if not row else [{"id": self.IMAGE_MODEL, "cached": True}]
        return list((data or {}).get("data") or [])

    def generate_image(self, prompt, *, privacy="approved_cloud", sensitive=False,
                       model=None, output_format="png"):
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ValueError("image prompt is required")
        self._assert_cloud_allowed(privacy, prompt, sensitive=sensitive)
        model = str(model or self.IMAGE_MODEL).strip()
        row = self._find_catalog_row(model, refresh=True)
        if not row:
            raise RuntimeError("requested OpenRouter image model is not present in the live catalog")
        architecture = dict(row.get("architecture") or {})
        if "image" not in set(architecture.get("output_modalities") or []):
            raise RuntimeError("requested model is not an image-output model")
        if not self._pricing_zero(row.get("pricing"), image_output=True):
            raise ZeroCostPolicyError("image generation blocked because the live model catalog is not zero-cost")

        image_rows = self.image_models(refresh=True)
        capability = next((x for x in image_rows if str(x.get("id") or "") == model), None)
        if not capability:
            raise RuntimeError("requested zero-cost image model is unavailable from OpenRouter Images API")
        formats = (((capability.get("supported_parameters") or {}).get("output_format") or {}).get("values") or [])
        output_format = str(output_format or "png").strip().lower()
        if formats and output_format not in formats:
            raise ValueError("unsupported output format for selected image model")

        profile = self.profile()
        payload = {"model": model, "prompt": prompt}
        if output_format:
            payload["output_format"] = output_format
        data = self.gateway.request_json(profile["id"], "/images", payload=payload, method="POST", timeout=180)
        cost = self._usage_cost(data)
        if cost is not None and cost != 0:
            raise ZeroCostPolicyError(f"provider reported non-zero image cost after zero-cost preflight: {cost}")
        first = ((data or {}).get("data") or [{}])[0]
        encoded = str(first.get("b64_json") or "")
        if not encoded:
            raise RuntimeError("OpenRouter image response did not contain b64_json")
        raw = base64.b64decode(encoded, validate=True)
        if not raw or len(raw) > self.MAX_IMAGE_BYTES:
            raise RuntimeError("generated image payload is empty or exceeds KRISHNA's bounded media limit")

        media_type = str(first.get("media_type") or "")
        extension = {"image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}.get(media_type, output_format)
        if extension not in {"png", "jpg", "jpeg", "webp", "svg"}:
            extension = "bin"
        self.image_dir.mkdir(parents=True, exist_ok=True)
        image_id = str(uuid.uuid4())
        target = self.image_dir / f"{image_id}.{extension}"
        fd, tmp = tempfile.mkstemp(prefix="openrouter-image-", suffix=".tmp", dir=str(self.image_dir))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return {
            "provider": "openrouter",
            "profile_id": profile["id"],
            "model": model,
            "image_id": image_id,
            "path": str(target),
            "bytes": len(raw),
            "media_type": media_type or ("image/jpeg" if extension in {"jpg", "jpeg"} else f"image/{extension}"),
            "output_format": output_format,
            "preflight_zero_cost": True,
            "provider_reported_cost": None if cost is None else str(cost),
            "privacy": str(privacy),
            "policy": "prompt-only image generation; no reference image or explicit dimensions are sent",
        }

    def image_path(self, image_id):
        token = str(image_id or "").strip()
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", token):
            raise KeyError("image not found")
        matches = list(self.image_dir.glob(token + ".*")) if self.image_dir.exists() else []
        if len(matches) != 1 or not matches[0].is_file():
            raise KeyError("image not found")
        return matches[0]

    def status(self, refresh=False):
        profile = self.profile()
        cached = self._read_cache()
        catalog_error = None
        plan = {}
        if refresh and profile:
            try:
                self.catalog(refresh=True)
                plan = self.role_plan(refresh=False)
            except Exception as exc:
                catalog_error = f"{type(exc).__name__}: {exc}"
        elif cached:
            try:
                plan = self.role_plan(refresh=False)
            except Exception as exc:
                catalog_error = f"{type(exc).__name__}: {exc}"
        return {
            "component": "KRISHNA OpenRouter Zero-Cost Fabric",
            "version": "openrouter-zero-cost-v1",
            "configured": bool(profile),
            "profile": None if not profile else {
                "id": profile.get("id"),
                "name": profile.get("name"),
                "base_url": profile.get("base_url"),
                "credential_backend": profile.get("credential_backend"),
            },
            "catalog": {
                "cached": bool(cached),
                "fetched_at": None if not cached else cached.get("fetched_at"),
                "model_count": 0 if not cached else len(cached.get("models") or []),
                "error": catalog_error,
            },
            "role_plan": plan,
            "image_model": self.IMAGE_MODEL,
            "paid_cloud_default": "disabled",
            "privacy": {
                "allowed": ["approved_cloud", "public"],
                "blocked": ["local_only", "restricted", "sensitive"],
                "credential_like_payloads": "blocked before cloud egress",
            },
            "zero_cost_policy": {
                "live_catalog_preflight_required": True,
                "nonzero_catalog_price": "blocked",
                "provider_reported_nonzero_cost": "policy violation",
                "paid_fallback": False,
                "stale_catalog_execution": False,
            },
        }
