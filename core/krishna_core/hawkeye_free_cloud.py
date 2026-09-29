from __future__ import annotations

import base64
import json


class HawkeyeFreeCloudFabric:
    """Cloud acceleration for HAWKEYE without mobile-side model hosting.

    KRISHNA remains the authority. Mobile performs capture/OCR/tracking locally.
    Only selected, owner-approved, non-sensitive keyframes may leave the device.
    Raw images are sent only to vision-capable providers. Sanitized text summaries
    may be reviewed by configured free-only text providers.
    """

    IMAGE_TYPES={"image/jpeg","image/png","image/webp"}

    def __init__(self, openrouter_free, direct_free, gateway, gemini):
        self.openrouter_free=openrouter_free
        self.direct_free=direct_free
        self.gateway=gateway
        self.gemini=gemini

    @staticmethod
    def _metadata(meta):
        meta=dict(meta or {})
        sensitive=bool(
            meta.get("contains_credentials")
            or meta.get("credentials_detected")
            or meta.get("contains_biometrics")
            or meta.get("unknown_face")
            or meta.get("face_embedding")
            or meta.get("private_document")
            or meta.get("private_source")
            or meta.get("raw_recording")
        )
        return meta,sensitive

    @classmethod
    def _assert_keyframe_allowed(cls, meta):
        meta,sensitive=cls._metadata(meta)
        if not bool(meta.get("cloud_approved",False)):
            raise PermissionError("HAWKEYE free-cloud use requires owner-approved cloud mode")
        if not bool(meta.get("selected_keyframe",False)):
            raise PermissionError("HAWKEYE free-cloud accepts selected keyframes only")
        if sensitive:
            raise PermissionError("sensitive HAWKEYE evidence remains local")
        return meta

    @staticmethod
    def _gateway_family(row):
        text=" ".join([
            str(row.get("name") or ""),
            str(row.get("base_url") or ""),
            str(row.get("model") or ""),
        ]).lower()
        if "openrouter.ai" in text:return "openrouter"
        if "cloudflare.com/client/v4/accounts/" in text:return "cloudflare"
        if "generativelanguage.googleapis.com" in text or "gemini" in text:return "gemini"
        if "groq" in text:return "groq"
        if "mistral" in text:return "mistral"
        if "nvidia" in text or "integrate.api.nvidia.com" in text:return "nvidia"
        if "cerebras" in text:return "cerebras"
        if "dashscope" in text or "alibabacloud" in text:return "qwen-cloud"
        return "free-gateway"

    def _declared_free_text_profiles(self):
        rows=[]
        try:
            for row in self.gateway.list().get("profiles") or []:
                if not (row.get("enabled") and row.get("credential_available") and row.get("free_only")):
                    continue
                family=self._gateway_family(row)
                if family in {"openrouter","cloudflare","gemini"}:
                    continue
                item=dict(row);item["family"]=family;rows.append(item)
        except Exception:
            pass
        return rows

    @staticmethod
    def recorded_pc_finding(sensor_context):
        sensor_context=dict(sensor_context or {})
        row=sensor_context.get("free_cloud") or {}
        if not isinstance(row,dict):
            return None
        analysis=str(row.get("analysis") or "").strip()
        if (
            not bool(row.get("pc_recorded"))
            or not str(row.get("pc_observation_id") or "").strip()
            or not analysis
            or bool(sensor_context.get("force_pc_vision",False))
        ):
            return None
        return {
            "analysis":analysis[:8000],
            "provider":str(row.get("provider") or "free-cloud")[:120],
            "model":str(row.get("model") or "")[:240],
            "role":str(row.get("role") or "hawkeye_vision")[:120],
            "pc_observation_id":str(row.get("pc_observation_id") or "")[:240],
            "pc_session_id":str(row.get("pc_session_id") or "")[:240],
        }

    def status(self, refresh=False):
        declared=self._declared_free_text_profiles()
        return {
            "component":"HAWKEYE Free Cloud Fabric",
            "version":"hawkeye-free-cloud-v2-hard-zero-credit",
            "authority":"KRISHNA",
            "mobile_local_perception":True,
            "mobile_qwen":False,
            "pc_role":"credential-broker-policy-authority-heavy-escalation",
            "providers":{
                "openrouter_zero_cost":self.openrouter_free.status(refresh=refresh),
                "cloudflare_verified_free":self.direct_free.status(refresh=refresh),
                "gemini_selected_keyframe":self.gemini.status(),
                "gemini_execution":"blocked-no-zero-credit-proof",
                "declared_free_text_gateways":[
                    {"id":x.get("id"),"name":x.get("name"),"model":x.get("model"),"family":x.get("family")}
                    for x in declared
                ],
            },
            "privacy":{
                "selected_non_sensitive_keyframes_only":True,
                "credentials_local_only":True,
                "biometrics_local_only":True,
                "private_documents_local_only":True,
                "continuous_raw_camera_cloud_upload":False,
            },
            "billing":{
                "paid_fallback":False,
                "openrouter":"live zero-price preflight",
                "cloudflare":"live zero-billing account preflight",
                "declared_free_gateways":"status-only; generic gateway inference blocked without zero-credit proof",
                "credits_allowed":False,
                "promotional_or_trial_credits_allowed":False,
            },
        }

    def _text_reviews(self, prompt, primary_text, *, max_reviews=2):
        review_prompt=(
            "You are an independent HAWKEYE reviewer inside KRISHNA. "
            "Review this non-sensitive observation summary. Separate supported observations "
            "from inference, state uncertainty, and suggest the single best next observation.\n\n"
            "USER GOAL:\n"+str(prompt or "")[:3000]+"\n\n"
            "PRIMARY ANALYSIS:\n"+str(primary_text or "")[:7000]
        )
        reviews=[]
        try:
            row=self.direct_free.complete(
                review_prompt,privacy="approved_cloud",sensitive=False,max_tokens=1200
            )
            reviews.append({
                "provider":row.get("provider_id") or row.get("provider"),
                "model":row.get("model"),
                "text":row.get("text"),
                "zero_cost_verified":True,
            })
        except Exception:
            pass

        # Generic free_only gateway labels are metadata only. Reviews never consume
        # trial/promotional/provider credits under hard zero-credit mode.
        return reviews

    def analyze_image(self, data:bytes, content_type:str, prompt:str, metadata=None,
                      provider="auto", openrouter_role="hawkeye_vision",
                      preferred_model=None, include_reviews=True):
        meta=self._assert_keyframe_allowed(metadata)
        ctype=str(content_type or "").split(";",1)[0].strip().lower()
        if ctype not in self.IMAGE_TYPES:
            raise ValueError("HAWKEYE free-cloud accepts JPEG, PNG or WEBP keyframes only")
        if not data:
            raise ValueError("HAWKEYE free-cloud keyframe is empty")
        if len(data)>4*1024*1024:
            raise ValueError("HAWKEYE free-cloud keyframe exceeds 4 MB")
        prompt=str(prompt or "").strip() or (
            "Analyze this selected HAWKEYE keyframe. Distinguish OBSERVED facts from "
            "INFERRED possibilities and identify uncertainty."
        )
        provider=str(provider or "auto").strip().lower()
        attempts=[]
        result=None

        if provider in {"auto","openrouter"}:
            try:
                encoded=base64.b64encode(data).decode("ascii")
                row=self.openrouter_free.complete(
                    openrouter_role,prompt,privacy="approved_cloud",sensitive=False,
                    image_data_url=f"data:{ctype};base64,{encoded}",
                    max_tokens=1800,preferred_model=preferred_model,
                )
                result={
                    "provider":"openrouter",
                    "model":row.get("model"),
                    "analysis":row.get("text"),
                    "zero_cost_verified":True,
                    "role":row.get("role"),
                    "selected_keyframe":True,
                }
            except Exception as exc:
                attempts.append({"provider":"openrouter","error":f"{type(exc).__name__}: {exc}"})
                if provider=="openrouter":
                    raise

        if result is None and provider in {"auto","gemini"}:
            error=(
                "PermissionError: Gemini is blocked by KRISHNA hard zero-credit policy "
                "because free-tier/account billing state is not execution-time zero-credit proven"
            )
            attempts.append({"provider":"gemini","error":error})
            if provider=="gemini":
                raise PermissionError(error.split(": ",1)[1])

        if result is None:
            raise RuntimeError("no HAWKEYE free-cloud vision provider succeeded: "+json.dumps(attempts,ensure_ascii=False)[:4000])

        result["authority"]="worker-evidence-only"
        result["continuous_raw_camera_upload"]=False
        result["mobile_qwen"]=False
        result["attempts"]=attempts
        result["reviews"]=self._text_reviews(prompt,result.get("analysis") or "") if include_reviews else []
        return result
