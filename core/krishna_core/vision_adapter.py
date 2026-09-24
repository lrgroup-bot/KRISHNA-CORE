from __future__ import annotations

import base64
import json
import os
import urllib.request

from .config import settings


IMAGE_TYPES={"image/jpeg","image/png","image/webp"}


class VisionAdapter:
    """Local-first image reasoning through Ollama multimodal chat.

    Images remain local. The adapter accepts only bounded image attachments and
    never sends them to cloud providers.
    """

    DEFAULT_MODEL="qwen3.5:4b"
    DEFAULT_FALLBACKS=("qwen2.5vl:7b",)

    def __init__(self,model=None,base_url=None,timeout=120):
        self.model=model or os.getenv("KRISHNA_VISION_MODEL",self.DEFAULT_MODEL)
        raw=str(os.getenv("KRISHNA_VISION_FALLBACK_MODELS",",".join(self.DEFAULT_FALLBACKS)) or "")
        self.fallback_models=[]
        for item in raw.split(","):
            item=item.strip()
            if item and item!=self.model and item not in self.fallback_models:self.fallback_models.append(item)
        self.base_url=(base_url or settings.ollama_url).rstrip("/")
        self.timeout=int(timeout)

    def candidates(self):
        return [self.model,*self.fallback_models]

    def status(self):
        available=False;models=[];error=None;selected=None
        try:
            with urllib.request.urlopen(self.base_url+"/api/tags",timeout=3) as r:
                rows=json.loads(r.read().decode()).get("models",[])
            models=[str(x.get("name") or x.get("model") or "") for x in rows]
            installed={x.lower() for x in models}
            selected=next((m for m in self.candidates() if m.lower() in installed or (m.lower()+":latest") in installed),None)
            available=bool(selected)
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
        return {
            "provider":"ollama","model":selected or self.model,"primary_model":self.model,
            "fallback_models":list(self.fallback_models),"selected_model":selected,
            "local":True,"available":available,"models":models[:40],"error":error,
        }

    def analyze_bytes(self,data:bytes,content_type:str,prompt:str)->dict:
        content_type=str(content_type or "").split(";",1)[0].strip().lower()
        if content_type not in IMAGE_TYPES:raise ValueError("vision adapter accepts JPEG, PNG or WEBP only")
        if not data:raise ValueError("image attachment is empty")
        if len(data)>25*1024*1024:raise ValueError("image exceeds 25 MB")
        prompt=str(prompt or "Describe this image and extract useful evidence.").strip()
        if not prompt:raise ValueError("vision prompt is required")
        encoded=base64.b64encode(data).decode("ascii")
        status=self.status()
        ordered=[status.get("selected_model"),*self.candidates()]
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
            req=urllib.request.Request(self.base_url+"/api/chat",data=json.dumps(payload).encode(),
                                       headers={"Content-Type":"application/json"})
            try:
                with urllib.request.urlopen(req,timeout=self.timeout) as r:out=json.loads(r.read().decode())
                text=str((out.get("message") or {}).get("content") or "").strip()
                if text:
                    return {
                        "provider":"ollama","model":model,"primary_model":self.model,
                        "fallback_used":model!=self.model,"local":True,"analysis":text,
                    }
                errors[model]="empty response"
            except Exception as exc:
                errors[model]=f"{type(exc).__name__}: {exc}"
        raise RuntimeError("local vision models unavailable: "+json.dumps(errors,ensure_ascii=False))
