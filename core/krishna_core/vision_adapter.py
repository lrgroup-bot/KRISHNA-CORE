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

    def __init__(self,model=None,base_url=None,timeout=120):
        self.model=model or os.getenv("KRISHNA_VISION_MODEL","qwen2.5vl:7b")
        self.base_url=(base_url or settings.ollama_url).rstrip("/")
        self.timeout=int(timeout)

    def status(self):
        available=False;models=[];error=None
        try:
            with urllib.request.urlopen(self.base_url+"/api/tags",timeout=3) as r:
                rows=json.loads(r.read().decode()).get("models",[])
            models=[str(x.get("name") or x.get("model") or "") for x in rows]
            target=self.model.split(":",1)[0].lower()
            available=any(str(x).lower()==self.model.lower() or str(x).lower().startswith(target+":") for x in models)
        except Exception as exc:
            error=f"{type(exc).__name__}: {exc}"
        return {"provider":"ollama","model":self.model,"local":True,"available":available,"models":models[:40],"error":error}

    def analyze_bytes(self,data:bytes,content_type:str,prompt:str)->dict:
        content_type=str(content_type or "").split(";",1)[0].strip().lower()
        if content_type not in IMAGE_TYPES:raise ValueError("vision adapter accepts JPEG, PNG or WEBP only")
        if not data:raise ValueError("image attachment is empty")
        if len(data)>25*1024*1024:raise ValueError("image exceeds 25 MB")
        prompt=str(prompt or "Describe this image and extract useful evidence.").strip()
        if not prompt:raise ValueError("vision prompt is required")
        payload={
            "model":self.model,
            "messages":[{"role":"user","content":prompt,"images":[base64.b64encode(data).decode("ascii")]}],
            "stream":False,
            "options":{"temperature":0.1},
        }
        req=urllib.request.Request(self.base_url+"/api/chat",data=json.dumps(payload).encode(),
                                   headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r:out=json.loads(r.read().decode())
        except Exception as exc:
            raise RuntimeError(f"local vision model unavailable: {type(exc).__name__}: {exc}") from exc
        text=str((out.get("message") or {}).get("content") or "").strip()
        if not text:raise RuntimeError("local vision model returned no text")
        return {"provider":"ollama","model":self.model,"local":True,"analysis":text}
