from __future__ import annotations

import base64
import json
import os
import urllib.request

from .config import settings


IMAGE_TYPES={"image/jpeg","image/png","image/webp"}


class VisionAdapter:
    """Local-first dual-profile image reasoning through Ollama multimodal chat.

    Qwen is disabled by owner policy. Images remain local and cloud fallback is
    never performed by this adapter.
    """

    DEFAULT_MODEL="gemma3:4b"
    DEFAULT_FALLBACKS=()
    DEFAULT_FAST_MODEL="gemma3:4b"
    DEFAULT_FAST_FALLBACKS=()
    DISABLED_MODEL_PREFIXES=("qwen",)

    @classmethod
    def model_allowed(cls,model):
        normalized=str(model or "").strip().lower().replace("\\","/")
        if not normalized:return False
        basename=normalized.rsplit("/",1)[-1]
        return not any(
            normalized.startswith(prefix) or basename.startswith(prefix)
            for prefix in cls.DISABLED_MODEL_PREFIXES
        )

    @classmethod
    def _primary(cls,value,default):
        model=str(value or default).strip()
        return model if cls.model_allowed(model) else default

    @classmethod
    def _fallbacks(cls,env_name,defaults,primary):
        raw=str(os.getenv(env_name,",".join(defaults)) or "")
        out=[]
        for item in [*raw.split(","),*defaults]:
            item=item.strip()
            if item and cls.model_allowed(item) and item!=primary and item not in out:out.append(item)
        return out

    def __init__(self,model=None,base_url=None,timeout=120):
        self.model=self._primary(model or os.getenv("KRISHNA_VISION_MODEL"),self.DEFAULT_MODEL)
        self.fallback_models=self._fallbacks(
            "KRISHNA_VISION_FALLBACK_MODELS",self.DEFAULT_FALLBACKS,self.model
        )
        self.fast_model=self._primary(os.getenv("KRISHNA_FAST_VISION_MODEL"),self.DEFAULT_FAST_MODEL)
        self.fast_fallback_models=self._fallbacks(
            "KRISHNA_FAST_VISION_FALLBACK_MODELS",self.DEFAULT_FAST_FALLBACKS,self.fast_model
        )
        self.base_url=(base_url or settings.ollama_url).rstrip("/")
        self.timeout=int(timeout)

    @staticmethod
    def _normalize_mode(mode):
        value=str(mode or "detailed").strip().lower()
        if value in {"fast","live","realtime","quick"}:return "fast"
        return "detailed"

    def candidates(self,mode="detailed"):
        mode=self._normalize_mode(mode)
        if mode=="fast":
            return [self.fast_model,*self.fast_fallback_models]
        return [self.model,*self.fallback_models]

    def _profile(self,mode="detailed"):
        mode=self._normalize_mode(mode)
        candidates=self.candidates(mode)
        return {
            "mode":mode,
            "primary_model":candidates[0],
            "fallback_models":candidates[1:],
        }

    def _installed_models(self):
        with urllib.request.urlopen(self.base_url+"/api/tags",timeout=3) as r:
            rows=json.loads(r.read().decode()).get("models",[])
        models=[str(x.get("name") or x.get("model") or "") for x in rows]
        return models,{x.lower() for x in models}

    def _status_for(self,mode,models,installed):
        profile=self._profile(mode)
        selected=next(
            (
                m for m in [profile["primary_model"],*profile["fallback_models"]]
                if m.lower() in installed or (m.lower()+":latest") in installed
            ),
            None,
        )
        return {
            "mode":profile["mode"],
            "model":selected or profile["primary_model"],
            "primary_model":profile["primary_model"],
            "fallback_models":list(profile["fallback_models"]),
            "selected_model":selected,
            "available":bool(selected),
            "models":models[:40],
        }

    def status(self,mode=None):
        models=[];installed=set();error=None
        try:
            models,installed=self._installed_models()
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
        detailed=self._status_for("detailed",models,installed)
        fast=self._status_for("fast",models,installed)
        active=fast if self._normalize_mode(mode)=="fast" else detailed
        return {
            "provider":"ollama",
            **active,
            "local":True,
            "error":error,
            "profiles":{
                "detailed":{k:v for k,v in detailed.items() if k!="models"},
                "fast":{k:v for k,v in fast.items() if k!="models"},
            },
        }

    def analyze_bytes(self,data:bytes,content_type:str,prompt:str,mode="detailed")->dict:
        content_type=str(content_type or "").split(";",1)[0].strip().lower()
        if content_type not in IMAGE_TYPES:raise ValueError("vision adapter accepts JPEG, PNG or WEBP only")
        if not data:raise ValueError("image attachment is empty")
        if len(data)>25*1024*1024:raise ValueError("image exceeds 25 MB")
        prompt=str(prompt or "Describe this image and extract useful evidence.").strip()
        if not prompt:raise ValueError("vision prompt is required")
        mode=self._normalize_mode(mode)
        encoded=base64.b64encode(data).decode("ascii")
        status=self.status(mode)
        ordered=[status.get("selected_model"),*self.candidates(mode)]
        candidates=[]
        for model in ordered:
            model=str(model or "").strip()
            if model and model not in candidates:candidates.append(model)
        errors={}
        for model in candidates:
            payload={
                "model":model,
                "messages":[{"role":"user","content":prompt,"images":[encoded]}],
                "stream":False,
                "options":{"temperature":0.1},
            }
            req=urllib.request.Request(
                self.base_url+"/api/chat",
                data=json.dumps(payload).encode(),
                headers={"Content-Type":"application/json"},
            )
            try:
                with urllib.request.urlopen(req,timeout=self.timeout) as r:out=json.loads(r.read().decode())
                text=str((out.get("message") or {}).get("content") or "").strip()
                if text:
                    return {
                        "provider":"ollama","model":model,
                        "vision_mode":mode,
                        "primary_model":status["primary_model"],
                        "fallback_used":model!=status["primary_model"],
                        "local":True,"analysis":text,
                    }
                errors[model]="empty response"
            except Exception as exc:
                errors[model]=f"{type(exc).__name__}: {exc}"
        raise RuntimeError(
            f"local {mode} vision models unavailable: "
            +json.dumps(errors,ensure_ascii=False)
        )
