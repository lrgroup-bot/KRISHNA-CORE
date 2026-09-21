from __future__ import annotations

import threading
import time
import uuid


class AutonomySupervisor:
    """Resumes only explicitly opted-in, non-mutating commitments.

    This layer never edits project files, promotes candidates, sends external messages,
    or bypasses Policy/approval. It can refresh investigation, research or repository
    index evidence so KRISHNA keeps safe routine work moving while unattended.
    """

    SAFE_OPERATIONS={"investigate","research","index"}

    def __init__(self, orchestrator, poll_seconds=300):
        self.orch=orchestrator
        self.poll_seconds=max(60,int(poll_seconds))
        self._stop=threading.Event()
        self._thread=None
        self.last_run=0.0
        self.last_results=[]
        self.run_count=0

    def start(self):
        if self._thread and self._thread.is_alive():return self.status()
        self._stop.clear()
        self._thread=threading.Thread(target=self._loop,name="krishna-autonomy-supervisor",daemon=True)
        self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=2)
        return self.status()

    @staticmethod
    def _config(item):
        detail=item.get("detail") if isinstance(item.get("detail"),dict) else {}
        cfg=detail.get("autonomy") if isinstance(detail.get("autonomy"),dict) else {}
        return detail,cfg

    def eligible(self,item,now=None):
        now=float(now or time.time())
        detail,cfg=self._config(item)
        if item.get("status") in {"waiting_approval","completed","cancelled","superseded"}:return False
        if not bool(cfg.get("enabled",False)):return False
        op=str(cfg.get("operation") or "").strip().lower()
        if op not in self.SAFE_OPERATIONS:return False
        every=max(60,int(cfg.get("interval_seconds") or self.poll_seconds))
        last=float(cfg.get("last_run") or 0)
        return now-last>=every

    @staticmethod
    def _summary(op,result):
        if op=="investigate":
            return {"operation":op,"investigation_id":result.get("investigation_id"),"status":result.get("status"),
                    "hypothesis_count":len(result.get("hypotheses") or [])}
        if op=="research":
            return {"operation":op,"web_count":len(result.get("web") or []),"github_count":len(result.get("github") or []),
                    "handover":result.get("handover")}
        if op=="index":
            return {"operation":op,"file_count":result.get("file_count",0),"symbol_count":len(result.get("symbols") or [])}
        return {"operation":op}

    def _execute(self,item):
        detail,cfg=self._config(item)
        project=item.get("project") or "KRISHNA"
        op=str(cfg.get("operation") or "").strip().lower()
        goal=str(cfg.get("goal") or detail.get("goal") or item.get("title") or "").strip()
        if not goal:raise ValueError("autonomous commitment has no goal")
        if op=="investigate":
            result=self.orch.investigate(goal,project,cfg.get("components") or [])
        elif op=="research":
            result=self.orch.garuda_scout(project,goal,min(20,max(1,int(cfg.get("limit") or 10))))
        elif op=="index":
            result=self.orch.index_project(project)
        else:
            raise PermissionError("autonomy operation is not in the non-mutating allowlist")
        summary=self._summary(op,result)
        evidence_id=str(uuid.uuid4())
        self.orch.memory.remember(project,"autonomy_run",goal,{"evidence_id":evidence_id,"commitment_id":item["commitment_id"],"summary":summary})
        return evidence_id,summary

    def run_once(self,now=None):
        now=float(now or time.time())
        rows=self.orch.commitments.list(None,True,500)
        results=[]
        for item in rows:
            if not self.eligible(item,now):continue
            detail,cfg=self._config(item)
            try:
                with self.orch.governor.job(timeout=0):
                    evidence_id,summary=self._execute(item)
                cfg={**cfg,"last_run":now,"last_status":"ok","last_evidence_id":evidence_id,
                     "run_count":int(cfg.get("run_count") or 0)+1}
                detail={**detail,"autonomy":cfg,"latest_autonomy_result":summary}
                self.orch.commitments.update(item["commitment_id"],"in_progress",detail)
                results.append({"commitment_id":item["commitment_id"],"ok":True,"summary":summary,"evidence_id":evidence_id})
            except RuntimeError as exc:
                if "resource governor busy" in str(exc):
                    results.append({"commitment_id":item["commitment_id"],"ok":False,"skipped":"resource_governor_busy"})
                    continue
                cfg={**cfg,"last_run":now,"last_status":"error","last_error":f"{type(exc).__name__}: {exc}",
                     "run_count":int(cfg.get("run_count") or 0)+1}
                detail={**detail,"autonomy":cfg}
                self.orch.commitments.update(item["commitment_id"],"blocked",detail)
                results.append({"commitment_id":item["commitment_id"],"ok":False,"error":cfg["last_error"]})
            except Exception as exc:
                cfg={**cfg,"last_run":now,"last_status":"error","last_error":f"{type(exc).__name__}: {exc}",
                     "run_count":int(cfg.get("run_count") or 0)+1}
                detail={**detail,"autonomy":cfg}
                self.orch.commitments.update(item["commitment_id"],"blocked",detail)
                results.append({"commitment_id":item["commitment_id"],"ok":False,"error":cfg["last_error"]})
        self.last_run=now;self.run_count+=1;self.last_results=results[-50:]
        return {"checked":len(rows),"executed":sum(1 for x in results if x.get("ok")),"results":results,"at":now}

    def _record_loop_error(self,exc):
        row={"ok":False,"error":f"supervisor_loop: {type(exc).__name__}: {exc}","at":time.time()}
        self.last_results=(self.last_results+[row])[-50:]

    def _loop(self):
        try:self.run_once()
        except Exception as exc:self._record_loop_error(exc)
        while not self._stop.wait(self.poll_seconds):
            try:self.run_once()
            except Exception as exc:self._record_loop_error(exc)

    def status(self):
        rows=self.orch.commitments.list(None,True,500)
        eligible=[x["commitment_id"] for x in rows if self.eligible(x)]
        return {"running":bool(self._thread and self._thread.is_alive()),"poll_seconds":self.poll_seconds,
                "safe_operations":sorted(self.SAFE_OPERATIONS),"eligible":eligible,"eligible_count":len(eligible),
                "last_run":self.last_run,"run_count":self.run_count,"last_results":list(self.last_results),
                "policy":"explicit opt-in; non-mutating evidence refresh only; approvals remain required for mutation/promotion/external side effects"}
