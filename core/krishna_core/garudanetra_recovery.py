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

    def __init__(self,harness_command=None):
        self.harness_command=str(harness_command or os.getenv("KRISHNA_BROWSER_HARNESS_CMD","")).strip()

    def status(self):
        return {"deterministic":True,"external_harness_configured":bool(self.harness_command),
                "policy":"deterministic locator recovery first; external harness output is untrusted candidate evidence"}

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
            external=self._external(page,payload)
            attempts.append({"strategy":"external_harness","result":external})
            selector=str(external.get("selector") or "").strip()
            if selector:
                try:
                    loc=page.locator(selector)
                    if loc.count()>0:
                        return {"locator":loc.first,"strategy":"external_harness","attempts":attempts,"source":"untrusted_external"}
                except Exception as exc:
                    attempts.append({"strategy":"external_harness_selector","error":f"{type(exc).__name__}: {exc}"})

        raise RuntimeError("selector recovery failed: "+json.dumps(attempts)[:3000])

    def _external(self,page,payload):
        # The optional harness receives a temporary JSON snapshot path and must return
        # JSON on stdout. It never receives credentials directly from KRISHNA.
        snapshot={"url":page.url,"title":page.title(),"payload":payload,
                  "visible_text":page.locator("body").inner_text(timeout=3000)[:12000]}
        fd,tmp=tempfile.mkstemp(prefix="krishna-browser-recovery-",suffix=".json")
        os.close(fd);Path(tmp).write_text(json.dumps(snapshot,ensure_ascii=False),encoding="utf-8")
        try:
            args=[x.format(snapshot=tmp) for x in shlex.split(self.harness_command,posix=os.name!="nt")]
            p=subprocess.run(args,capture_output=True,text=True,shell=False,timeout=30)
            if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-2000:])
            data=json.loads(p.stdout or "{}")
            return data if isinstance(data,dict) else {}
        finally:
            try:Path(tmp).unlink()
            except OSError:pass
