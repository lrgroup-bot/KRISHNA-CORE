"""Privacy-minimizing KRISHNA observability primitives."""
from __future__ import annotations
from pathlib import Path
import json,time,uuid

class KrishnaObservability:
    def __init__(self,state_root):
        self.root=Path(state_root);self.root.mkdir(parents=True,exist_ok=True)
        self.log=self.root/"traces.jsonl"
    def event(self,component,operation,status="ok",metrics=None,evidence=None):
        row={"trace_id":str(uuid.uuid4()),"time":time.time(),"component":str(component),
             "operation":str(operation),"status":str(status),"metrics":dict(metrics or {}),
             "evidence_refs":list(evidence or [])}
        # Raw prompts, camera frames, secrets and tool payloads are intentionally excluded.
        with self.log.open("a",encoding="utf-8") as f:f.write(json.dumps(row,separators=(",",":"))+"\n")
        return row
