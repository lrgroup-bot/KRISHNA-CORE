from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import urllib.error
import urllib.request

from .config import settings


_IMAGE_TYPES={"image/jpeg","image/png","image/webp"}


class GeminiHawkeyeBridge:
    """PC-owned Gemini bridge for HAWKEYE selected evidence.

    The permanent credential never leaves the KRISHNA PC. Mobile requests are
    accepted only for explicitly approved, bounded, non-sensitive keyframes.
    Live API clients receive only short-lived Gemini ephemeral tokens.
    """

    API_ROOT="https://generativelanguage.googleapis.com"
    DEFAULT_MODEL="gemini-3.8-flash"
    DEFAULT_LIVE_MODEL="gemini-3.8-live"

    def __init__(self,gateway=None,timeout=90):
        self.gateway=gateway
        self.timeout=max(5,int(timeout))

    def _gateway_profile(self):
        if self.gateway is None:
            return None
        rows=list(getattr(self.gateway,"profiles",{}).values())
        rows=[x for x in rows if getattr(x,"enabled",False)]
        for row in sorted(rows,key=lambda x:getattr(x,"created_at",0),reverse=True):
            text=(" ".join([
                str(getattr(row,"name","")),
                str(getattr(row,"base_url","")),
                str(getattr(row,"model","")),
            ])).lower()
            if "gemini" in text or "generativelanguage.googleapis.com" in text:
                return row
        return None

    def _credential(self):
        row=self._gateway_profile()
        if row is not None:
            key=self.gateway.vault.resolve(row.secret_id)
            return {
                "key":key,
                "model":str(row.model or self.DEFAULT_MODEL),
                "source":"model_gateway",
                "profile_id":str(row.id),
                "free_only":bool(getattr(row,"free_only",False)),
            }
        key=(
            os.getenv("KRISHNA_GEMINI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        if key:
            return {
                "key":key,
                "model":os.getenv("KRISHNA_GEMINI_MODEL",self.DEFAULT_MODEL).strip() or self.DEFAULT_MODEL,
                "source":"environment",
                "profile_id":None,
                "free_only":str(os.getenv("KRISHNA_GEMINI_FREE_ONLY","0")).strip().lower() in {"1","true","yes","on"},
            }
        cloud_url=str(getattr(settings,"cloud_api_url","") or "").lower()
        cloud_key=str(getattr(settings,"cloud_api_key","") or "").strip()
        if cloud_key and ("gemini" in cloud_url or "generativelanguage.googleapis.com" in cloud_url):
            return {
                "key":cloud_key,
                "model":os.getenv("KRISHNA_GEMINI_MODEL",self.DEFAULT_MODEL).strip() or self.DEFAULT_MODEL,
                "source":"krishna-cloud-config",
                "profile_id":None,
                "free_only":str(os.getenv("KRISHNA_GEMINI_FREE_ONLY","0")).strip().lower() in {"1","true","yes","on"},
            }
        return None

    @staticmethod
    def _safe_metadata(meta):
        meta=dict(meta or {})
        flags={
            "contains_credentials":bool(meta.get("contains_credentials") or meta.get("credentials_detected")),
            "contains_biometrics":bool(meta.get("contains_biometrics") or meta.get("unknown_face") or meta.get("face_embedding")),
            "private_document":bool(meta.get("private_document") or meta.get("private_source")),
            "raw_recording":bool(meta.get("raw_recording")),
        }
        return meta,flags

    @classmethod
    def _assert_cloud_allowed(cls,meta):
        meta,flags=cls._safe_metadata(meta)
        if not bool(meta.get("cloud_approved",False)):
            raise PermissionError("Gemini cloud use requires explicit owner approval for this request")
        if not bool(meta.get("selected_keyframe",False)):
            raise PermissionError("Gemini receives selected HAWKEYE keyframes only")
        if any(flags.values()):
            blocked=", ".join(k for k,v in flags.items() if v)
            raise PermissionError("Gemini cloud upload blocked for sensitive evidence: "+blocked)
        return meta

    @staticmethod
    def _request(url,key,payload,timeout):
        body=json.dumps(payload,separators=(",",":")).encode("utf-8")
        req=urllib.request.Request(
            url,data=body,method="POST",
            headers={
                "Content-Type":"application/json",
                "Accept":"application/json",
                "x-goog-api-key":key,
            },
        )
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                raw=response.read()
        except urllib.error.HTTPError as exc:
            detail=exc.read().decode("utf-8","replace")[:2000]
            raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"Gemini request failed: {type(exc).__name__}: {exc}") from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("Gemini returned invalid JSON") from exc

    def status(self):
        cfg=self._credential()
        return {
            "provider":"google-gemini",
            "configured":cfg is not None,
            "credential_location":"KRISHNA_PC_ONLY",
            "mobile_permanent_key":False,
            "selected_keyframes_only":True,
            "live_auth":"ephemeral-token",
            "model":None if cfg is None else cfg["model"],
            "credential_source":None if cfg is None else cfg["source"],
            "profile_id":None if cfg is None else cfg["profile_id"],
            "free_only_declared":False if cfg is None else bool(cfg.get("free_only",False)),
            "hard_zero_credit":True,
            "inference_allowed":False,
            "blocked_reason":"Gemini account billing/free-tier state is not machine-proven zero-credit by KRISHNA",
        }

    def analyze_image(self,data:bytes,content_type:str,prompt:str,metadata=None):
        raise PermissionError(
            "Gemini inference is blocked by KRISHNA hard zero-credit policy until an execution-time "
            "zero-price/zero-billing proof is available"
        )
        cfg=self._credential()
        if cfg is None:
            raise RuntimeError("Gemini is not configured on KRISHNA PC")
        meta=self._assert_cloud_allowed(metadata)
        ctype=str(content_type or "").split(";",1)[0].strip().lower()
        if ctype not in _IMAGE_TYPES:
            raise ValueError("Gemini HAWKEYE accepts JPEG, PNG or WEBP keyframes only")
        if not data:
            raise ValueError("Gemini HAWKEYE keyframe is empty")
        if len(data)>4*1024*1024:
            raise ValueError("Gemini HAWKEYE selected keyframe exceeds 4 MB")
        prompt=str(prompt or "").strip() or (
            "Analyze this selected HAWKEYE camera keyframe. Return only supported observations, "
            "clearly distinguish observed facts from inference, and identify uncertainty."
        )
        model=str(meta.get("model") or cfg["model"] or self.DEFAULT_MODEL).strip()
        payload={
            "contents":[{
                "role":"user",
                "parts":[
                    {"inline_data":{"mime_type":ctype,"data":base64.b64encode(data).decode("ascii")}},
                    {"text":prompt},
                ],
            }],
            "generationConfig":{
                "temperature":0.1,
                "responseMimeType":"text/plain",
            },
        }
        out=self._request(
            f"{self.API_ROOT}/v1beta/models/{model}:generateContent",
            cfg["key"],payload,self.timeout,
        )
        chunks=[]
        for candidate in out.get("candidates") or []:
            for part in ((candidate.get("content") or {}).get("parts") or []):
                value=part.get("text")
                if value:
                    chunks.append(str(value))
        text="\n".join(chunks).strip()
        if not text:
            raise RuntimeError("Gemini returned no text analysis")
        return {
            "provider":"google-gemini",
            "model":model,
            "analysis":text,
            "local":False,
            "cloud":True,
            "selected_keyframe":True,
            "selected_keyframe_cloud_upload":True,
            "continuous_raw_camera_upload":False,
            "credential_location":"KRISHNA_PC_ONLY",
            "evidence_state":"OBSERVED",
        }

    def mint_live_token(self,metadata=None):
        raise PermissionError(
            "Gemini Live is blocked by KRISHNA hard zero-credit policy until an execution-time "
            "zero-price/zero-billing proof is available"
        )
        cfg=self._credential()
        if cfg is None:
            raise RuntimeError("Gemini is not configured on KRISHNA PC")
        meta=dict(metadata or {})
        if not bool(meta.get("cloud_approved",False)) or not bool(meta.get("user_explicit",False)):
            raise PermissionError("Gemini Live token requires an explicit owner action")
        if bool(meta.get("contains_credentials") or meta.get("contains_biometrics") or meta.get("private_document")):
            raise PermissionError("Gemini Live is blocked for sensitive evidence")
        now=_dt.datetime.now(tz=_dt.timezone.utc)
        expire=now+_dt.timedelta(minutes=30)
        new_session_expire=now+_dt.timedelta(minutes=1)
        model=str(meta.get("live_model") or os.getenv("KRISHNA_GEMINI_LIVE_MODEL",self.DEFAULT_LIVE_MODEL)).strip()
        payload={
            "uses":1,
            "expireTime":expire.isoformat().replace("+00:00","Z"),
            "newSessionExpireTime":new_session_expire.isoformat().replace("+00:00","Z"),
            "liveConnectConstraints":{
                "model":"models/"+model,
                "config":{
                    "sessionResumption":{},
                    "responseModalities":["AUDIO"],
                    "outputAudioTranscription":{},
                },
            },
        }
        out=self._request(f"{self.API_ROOT}/v1beta/auth_tokens",cfg["key"],payload,self.timeout)
        token=str(out.get("name") or "").strip()
        if not token:
            raise RuntimeError("Gemini did not return an ephemeral Live token")
        return {
            "provider":"google-gemini",
            "live_model":model,
            "token":token,
            "uses":1,
            "new_session_expires_at":payload["newSessionExpireTime"],
            "expires_at":payload["expireTime"],
            "permanent_key_exposed":False,
        }
