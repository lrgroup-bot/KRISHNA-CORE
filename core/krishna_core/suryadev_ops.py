from __future__ import annotations
import json,time
from pathlib import Path

"""Durable BRAHMA-readable SURYADEV operational telemetry."""

class SuryadevOpsLog:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.events=self.root/"suryadev-ops.jsonl"
        self.status=self.root/"suryadev-status.json"

    def emit(self,event,**fields):
        row={"ts":time.time(),"agent":"SURYDEV","event":str(event),**fields}
        with self.events.open("a",encoding="utf-8") as h:
            h.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
        return row

    def write_status(self,**status):
        row={"schema":"krishna.suryadev.status.v1","ts":time.time(),"agent":"SURYDEV",**status}
        tmp=self.status.with_suffix(".tmp")
        tmp.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding="utf-8")
        tmp.replace(self.status)
        return row

    def brahma_status(self):
        if not self.status.is_file():
            return {"agent":"SURYDEV","state":"unknown","reason":"no_status_yet"}
        return json.loads(self.status.read_text(encoding="utf-8"))
