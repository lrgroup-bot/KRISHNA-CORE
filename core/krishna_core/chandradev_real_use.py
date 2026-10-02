from __future__ import annotations
from datetime import datetime,timezone

class ChandradevRealUseExam:
    """Final human-like UI exam contract over an already-authorized browser runner."""
    DEFAULT_ACTIONS=("open","click_primary_navigation","scroll","form_valid","form_invalid","back","refresh","dialog_open_close","mobile_view")
    def plan(self,base_url,actions=None):
        return {"base_url":str(base_url),"actions":list(actions or self.DEFAULT_ACTIONS),"visual_after_each_action":True,
                "capture_failures":True,"retain_structured_evidence":True,"temporary_media_policy":"delete_after_evidence_extraction"}
    def evaluate(self,steps):
        rows=list(steps or []);failed=[x for x in rows if x.get("passed") is not True]
        suggestions=[]
        for x in failed:
            suggestions.append({"finding_id":"UX-CHANDRA-"+str(len(suggestions)+1).zfill(3),
              "action":x.get("action"),"reason":x.get("reason") or x.get("error") or "real-use step failed",
              "evidence":x.get("evidence"),"route":"SUDARSHAN_REPAIR"})
        return {"exam":"CHANDRADEV_REAL_USE","passed":bool(rows) and not failed,"steps":rows,"findings":suggestions,
                "examined_at":datetime.now(timezone.utc).isoformat()}
    def replay(self,steps):
        return [{"order":i+1,"action":x.get("action"),"passed":x.get("passed") is True,"evidence":x.get("evidence")} for i,x in enumerate(steps or [])]
