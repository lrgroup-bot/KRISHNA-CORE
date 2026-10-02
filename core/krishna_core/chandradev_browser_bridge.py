from __future__ import annotations
from .chandradev_real_use import ChandradevRealUseExam

class ChandradevBrowserBridge:
    """Convert executed Project Perfection browser evidence into CHANDRADEV final-QC evidence."""
    def __init__(self): self.exam=ChandradevRealUseExam()
    def from_regression(self,regression):
        if not regression or not regression.get("available"):
            return {"exam":"CHANDRADEV_REAL_USE","passed":False,"reason":"browser_evidence_unavailable","steps":[],"findings":[]}
        steps=[]
        for row in regression.get("routes") or []:
            steps.append({"action":"open:"+str(row.get("route") or "/"),"passed":row.get("passed") is True,
                          "reason":row.get("error") or "; ".join(map(str,row.get("findings") or []))[:1000],
                          "evidence":{"final_url":row.get("url"),"layout":row.get("layout")}})
        for row in regression.get("edges") or []:
            steps.append({"action":"click:"+str(row.get("name") or row.get("label") or row.get("selector") or "control"),
                          "passed":row.get("passed") is True,"reason":row.get("error") or "; ".join(map(str,row.get("findings") or []))[:1000],
                          "evidence":{"source":row.get("source"),"target":row.get("target"),"final_url":row.get("final_url"),
                                      "state_match":row.get("state_match")}})
        report=self.exam.evaluate(steps);report["source"]="PROJECT_PERFECTION_BROWSER_REGRESSION"
        report["physical_camera_claim"]=False;report["replay"]=self.exam.replay(steps)
        return report
