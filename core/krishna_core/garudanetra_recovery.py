from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path


class BrowserRecoveryAdapter:
    """Deterministic selector recovery with optional external browser-harness bridge.

    Recovery output is evidence/candidate data. It never grants new permissions and
    never promotes a learned selector to Stable by itself.
    """

    def __init__(self,harness_command=None,vision_command=None):
        self.harness_command=str(harness_command or os.getenv("KRISHNA_BROWSER_HARNESS_CMD","")).strip()
        self.vision_command=str(vision_command or os.getenv("KRISHNA_BROWSER_VISION_RECOVERY_CMD","")).strip()

    def status(self):
        return {"deterministic":True,"external_harness_configured":bool(self.harness_command),
                "vision_recovery_configured":bool(self.vision_command),
                "policy":"deterministic locator recovery first; external harness/vision output is untrusted candidate evidence"}

    def recover_locator(self,page,payload:dict):
        attempts=[]
        text=str(payload.get("text") or "").strip()
        role=str(payload.get("role") or "").strip()
        name=str(payload.get("name") or "").strip()
        label=str(payload.get("label") or "").strip()
        placeholder=str(payload.get("placeholder") or "").strip()

        candidates=[]
        if role and name:candidates.append(("role",lambda:page.get_by_role(role,name=name)))
        if label:candidates.append(("label",lambda:page.get_by_label(label)))
        if placeholder:candidates.append(("placeholder",lambda:page.get_by_placeholder(placeholder)))
        if text:candidates.append(("text",lambda:page.get_by_text(text,exact=False)))

        for kind,builder in candidates:
            try:
                loc=builder()
                count=loc.count()
                attempts.append({"strategy":kind,"count":count})
                if count>0:
                    return {"locator":loc.first,"strategy":kind,"attempts":attempts,"source":"deterministic"}
            except Exception as exc:
                attempts.append({"strategy":kind,"error":f"{type(exc).__name__}: {exc}"})

        if self.harness_command:
            external=self._external(page,payload,self.harness_command,"external_harness",include_screenshot=False)
            attempts.append({"strategy":"external_harness","result":external})
            selector=str(external.get("selector") or "").strip()
            if selector:
                try:
                    loc=page.locator(selector)
                    if loc.count()>0:
                        return {"locator":loc.first,"strategy":"external_harness","attempts":attempts,"source":"untrusted_external"}
                except Exception as exc:
                    attempts.append({"strategy":"external_harness_selector","error":f"{type(exc).__name__}: {exc}"})

        if self.vision_command:
            external=self._external(page,payload,self.vision_command,"vision_recovery",include_screenshot=True)
            attempts.append({"strategy":"vision_recovery","result":external})
            selector=str(external.get("selector") or "").strip()
            if selector:
                try:
                    loc=page.locator(selector)
                    if loc.count()>0:
                        return {"locator":loc.first,"strategy":"vision_recovery","attempts":attempts,"source":"untrusted_external_vision"}
                except Exception as exc:
                    attempts.append({"strategy":"vision_recovery_selector","error":f"{type(exc).__name__}: {exc}"})

        raise RuntimeError("selector recovery failed: "+json.dumps(attempts)[:3000])

    def _external(self,page,payload,command,kind,include_screenshot=False):
        # External recovery receives only a bounded temporary snapshot. It never gets
        # KRISHNA secrets or execution authority; its output must still resolve to a
        # real locator before Garudanetra uses it.
        safe_payload={k:v for k,v in dict(payload or {}).items() if k not in {"value","password","secret","token"}}
        snapshot={"url":page.url,"title":page.title(),"payload":safe_payload,
                  "visible_text":page.locator("body").inner_text(timeout=3000)[:12000],
                  "source":kind,"untrusted":True}
        paths=[]
        fd,tmp=tempfile.mkstemp(prefix="krishna-browser-recovery-",suffix=".json");os.close(fd);paths.append(tmp)
        if include_screenshot:
            fd,img=tempfile.mkstemp(prefix="krishna-browser-recovery-",suffix=".png");os.close(fd);paths.append(img)
            try:
                page.screenshot(path=img,full_page=False)
                snapshot["screenshot"]=img
            except Exception:
                snapshot["screenshot"]=None
        Path(tmp).write_text(json.dumps(snapshot,ensure_ascii=False),encoding="utf-8")
        try:
            args=[x.format(snapshot=tmp,screenshot=snapshot.get("screenshot") or "") for x in shlex.split(command,posix=os.name!="nt")]
            p=subprocess.run(args,capture_output=True,text=True,shell=False,timeout=30)
            if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-2000:])
            data=json.loads(p.stdout or "{}")
            return data if isinstance(data,dict) else {}
        finally:
            for path in paths:
                try:Path(path).unlink()
                except OSError:pass
