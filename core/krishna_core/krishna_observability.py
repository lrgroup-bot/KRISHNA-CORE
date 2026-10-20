"""Privacy-minimizing KRISHNA observability primitives."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json,time,uuid
from threading import RLock

class KrishnaObservability:
    def __init__(self,state_root):
        self.root=Path(state_root);self.root.mkdir(parents=True,exist_ok=True)
        self.log=self.root/"traces.jsonl";self._lock=RLock();self.max_bytes=10*1024*1024

    def event(self,component,operation,status="ok",metrics=None,evidence=None,*,trace_id=None,
              span_id=None,parent_span_id=None,mission_id=None,job_id=None,duration_ms=None):
        row={"trace_id":str(trace_id or uuid.uuid4()),"span_id":str(span_id or uuid.uuid4()),
             "parent_span_id":str(parent_span_id or "") or None,"time":time.time(),
             "component":str(component),"operation":str(operation),"status":str(status),
             "metrics":dict(metrics or {}),"evidence_refs":list(evidence or []),
             "mission_id":str(mission_id or "") or None,"job_id":str(job_id or "") or None}
        if duration_ms is not None: row["duration_ms"]=max(0,int(duration_ms))
        # Raw prompts, camera frames, secrets and tool payloads are intentionally excluded.
        line=json.dumps(row,separators=(",",":"))+"\n"
        with self._lock:
            if self.log.exists() and self.log.stat().st_size+len(line.encode("utf-8"))>self.max_bytes:
                rotated=self.root/"traces.1.jsonl"
                if rotated.exists():rotated.unlink()
                self.log.replace(rotated)
            with self.log.open("a",encoding="utf-8") as f:f.write(line)
        return row

    @contextmanager
    def span(self,component,operation,*,trace_id=None,parent_span_id=None,mission_id=None,job_id=None,evidence=None):
        trace_id=str(trace_id or uuid.uuid4());span_id=str(uuid.uuid4());started=time.perf_counter()
        self.event(component,operation,"started",evidence=evidence,trace_id=trace_id,span_id=span_id,
                   parent_span_id=parent_span_id,mission_id=mission_id,job_id=job_id)
        try:
            yield {"trace_id":trace_id,"span_id":span_id}
        except Exception as exc:
            self.event(component,operation,"failed",metrics={"error_type":type(exc).__name__},
                       trace_id=trace_id,span_id=span_id,parent_span_id=parent_span_id,
                       mission_id=mission_id,job_id=job_id,
                       duration_ms=(time.perf_counter()-started)*1000)
            raise
        else:
            self.event(component,operation,"completed",trace_id=trace_id,span_id=span_id,
                       parent_span_id=parent_span_id,mission_id=mission_id,job_id=job_id,
                       duration_ms=(time.perf_counter()-started)*1000)

    def latency_summary(self,limit=5000):
        rows=[]
        if self.log.is_file():
            for line in self.log.read_text(encoding="utf-8").splitlines()[-max(1,int(limit)):]:
                try:r=json.loads(line)
                except Exception:continue
                if r.get("status")=="completed" and isinstance(r.get("duration_ms"),(int,float)):rows.append(r)
        groups={}
        for r in rows:
            key=f"{r.get('component')}:{r.get('operation')}"
            groups.setdefault(key,[]).append(float(r["duration_ms"]))
        out={}
        for key,vals in groups.items():
            vals=sorted(vals);n=len(vals)
            out[key]={"count":n,"avg_ms":round(sum(vals)/n,1),"p50_ms":round(vals[int((n-1)*.50)],1),
                      "p95_ms":round(vals[int((n-1)*.95)],1),"max_ms":round(vals[-1],1)}
        return out
