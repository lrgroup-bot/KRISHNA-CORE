from __future__ import annotations
from pathlib import Path
import hashlib,json,time,uuid

def _clamp(v):
    try:return max(0.0,min(1.0,float(v)))
    except Exception:return 0.0
def _safe(v):
    return "".join(ch for ch in str(v or "") if ch.isalnum() or ch in "-_")[:160] or "unknown"

class HawkeyeOwnerDiscussion:
    """Opportunity inbox: Hawkeye may propose capabilities, but owner-gated actions wait for approval."""
    OWNER_GATED={"new_sensor","new_model_install","external_service","physical_movement","persistent_memory",
                 "high_compute","new_device","commercial_license","cross_session_person_identity"}
    def __init__(self,state_dir):
        self.root=Path(state_dir);self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"owner-opportunities.json"
    def _load(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {"items":[]}
    def _save(self,d):
        tmp=self.path.with_suffix(".tmp");tmp.write_text(json.dumps(d,indent=2,sort_keys=True),encoding="utf-8");tmp.replace(self.path)
    def propose(self,title,reason,options,*,category="capability",privacy="local",compute="low",cost="₹0",evidence_refs=None):
        d=self._load();sig=hashlib.sha256((str(category)+"|"+str(title)+"|"+str(reason)).encode()).hexdigest()[:16]
        for x in d["items"]:
            if x.get("signature")==sig and x.get("status")=="PENDING":return x
        gated=category in self.OWNER_GATED or cost!="₹0"
        row={"proposal_id":"HOP-"+uuid.uuid4().hex[:12],"signature":sig,"title":str(title)[:240],
             "reason":str(reason)[:1200],"options":[str(x)[:300] for x in (options or [])[:8]],
             "category":category,"privacy":privacy,"compute":compute,"cost":cost,
             "evidence_refs":[str(x)[:240] for x in (evidence_refs or [])[:16]],
             "status":"PENDING" if gated else "INFORM","owner_approval_required":gated,
             "created_at":time.time()}
        d["items"]=(d["items"]+[row])[-200:];self._save(d);return row
    def decide(self,proposal_id,approved):
        d=self._load()
        for x in d["items"]:
            if x["proposal_id"]==proposal_id:
                x["status"]="APPROVED" if approved else "DECLINED";x["decided_at"]=time.time();self._save(d);return x
        raise KeyError(proposal_id)
    def pending(self):return [x for x in self._load()["items"] if x["status"]=="PENDING"]

class HawkeyeActiveInvestigator:
    """Turns missing evidence into bounded acquisition suggestions."""
    @staticmethod
    def recommend(context):
        c=dict(context or {});out=[]
        if _clamp(c.get("quality",1))<.45:out.append({"action":"improve_image","suggestion":"I can refocus, zoom, adjust exposure and use multi-frame capture.","auto_safe":True})
        if c.get("tiny_text"):out.append({"action":"macro_ocr","suggestion":"I can crop/zoom the marking and retry industrial OCR.","auto_safe":True})
        if c.get("reflection"):out.append({"action":"change_angle","suggestion":"A different viewing angle may reduce reflection.","auto_safe":False})
        if c.get("occluded"):out.append({"action":"new_viewpoint","suggestion":"Another viewpoint may reveal the hidden area.","auto_safe":False})
        if c.get("depth_uncertain"):out.append({"action":"parallax","suggestion":"A small sideways viewpoint change can improve geometry evidence.","auto_safe":False})
        if c.get("previous_episode"):out.append({"action":"compare_previous","suggestion":"I can align this observation with the previous visit and check for changes.","auto_safe":True})
        if c.get("needs_3d"):out.append({"action":"3d_capture","suggestion":"I can prepare a multi-view 3D capture workflow.","auto_safe":False})
        return {"schema":"hawkeye.active-investigator.v1","recommendations":out,
                "automatic":[x for x in out if x["auto_safe"]],"discussion":[x for x in out if not x["auto_safe"]]}

class HawkeyeSpatialEpisodeMemory:
    """Object/place episodic metadata. Person identity is deliberately excluded."""
    def __init__(self,state_dir):
        self.root=Path(state_dir);self.root.mkdir(parents=True,exist_ok=True)
    def record(self,place_id,*,objects=None,observations=None,sensor_pose=None,evidence_refs=None):
        place=_safe(place_id);p=self.root/f"{place}.json";d=json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"place_id":place,"episodes":[]}
        episode={"episode_id":"HEP-"+uuid.uuid4().hex[:12],"at":time.time(),
                 "objects":[dict(x) for x in (objects or [])[:200] if str((x or {}).get("kind","")).lower() not in {"person_identity","face_identity"}],
                 "observations":[dict(x) for x in (observations or [])[:200]],"sensor_pose":dict(sensor_pose or {}),
                 "evidence_refs":[str(x)[:240] for x in (evidence_refs or [])[:32]]}
        d["episodes"]=(d["episodes"]+[episode])[-100:];p.write_text(json.dumps(d,indent=2,sort_keys=True),encoding="utf-8");return episode
    def history(self,place_id): 
        p=self.root/f"{_safe(place_id)}.json";return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"place_id":_safe(place_id),"episodes":[]}

class HawkeyeMultiSensorFusion:
    """Evidence-quality fusion; never upgrades inferred evidence into measurement."""
    WEIGHT={"camera":.8,"depth":.9,"imu":.85,"gnss":.8,"rtk":1.0,"audio":.7,"thermal":.8}
    @classmethod
    def fuse(cls,evidence):
        rows=[dict(x) for x in (evidence or [])]
        num=den=0.0;used=[]
        for r in rows:
            src=str(r.get("source") or "").lower();w=cls.WEIGHT.get(src,.5)*_clamp(r.get("quality",.5))
            num+=w*_clamp(r.get("confidence",.5));den+=w
            used.append({"source":src,"weight":round(w,4),"state":str(r.get("state") or "OBSERVED")})
        return {"schema":"hawkeye.sensor-fusion.v1","confidence":round(num/den,4) if den else 0.0,
                "sources":used,"evidence_state":"FUSED","measured_claim":False}
