from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import re
import time
from typing import Any, Iterable

_COLORS = {
    "black","white","gray","grey","red","blue","green","yellow","orange","purple",
    "pink","brown","beige","maroon","navy","cyan","teal","gold","silver"
}
_OBJECT_WORDS = {
    "person":"person","people":"person","man":"person","woman":"person","boy":"person","girl":"person",
    "car":"car","vehicle":"vehicle","truck":"truck","bus":"bus","bike":"bike","motorcycle":"motorcycle",
    "dog":"dog","cat":"cat","animal":"animal","box":"box","bag":"bag","backpack":"backpack",
    "excavator":"excavator","loader":"loader","machine":"machine","machinery":"machine",
}
_CLOTHING = {"shirt","tshirt","t-shirt","jacket","coat","dress","pants","trouser","trousers","jeans","shorts","helmet","cap","hat"}
_ACCESSORIES = {"backpack","bag","helmet","cap","hat","glasses"}
_SPATIAL = {"left","right","center","middle","front","back","near","beside","behind","ahead"}

@dataclass(frozen=True)
class TargetQuery:
    raw: str
    object_class: str | None
    colors: tuple[str, ...]
    clothing: tuple[str, ...]
    accessories: tuple[str, ...]
    spatial: tuple[str, ...]
    tokens: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        row=asdict(self)
        for key in ("colors","clothing","accessories","spatial","tokens"):
            row[key]=list(row[key])
        return row


class TargetDescriptionParser:
    """Parse non-identifying visual descriptions such as 'blue shirt person'."""

    @staticmethod
    def parse(command: str) -> TargetQuery:
        raw=str(command or "").strip()
        text=raw.lower().replace("_"," ")
        words=tuple(re.findall(r"[a-z0-9-]+", text))
        obj=None
        for word in words:
            if word in _OBJECT_WORDS:
                obj=_OBJECT_WORDS[word]
                break
        colors=tuple(dict.fromkeys("gray" if w=="grey" else w for w in words if w in _COLORS))
        clothing=tuple(dict.fromkeys(w for w in words if w in _CLOTHING))
        accessories=tuple(dict.fromkeys(w for w in words if w in _ACCESSORIES))
        spatial=tuple(dict.fromkeys(w for w in words if w in _SPATIAL))
        stop={"lock","track","follow","target","the","a","an","in","with","wearing","person","people","object","hawkeye","krishna"}
        tokens=tuple(dict.fromkeys(w for w in words if w not in stop))
        return TargetQuery(raw,obj,colors,clothing,accessories,spatial,tokens)


class VisualCandidateMatcher:
    """Deterministic scorer over detector/tracker evidence; semantic models can add text_score."""

    @staticmethod
    def _terms(candidate: dict[str, Any]) -> set[str]:
        values=[]
        values.append(str(candidate.get("label") or ""))
        values.extend(str(x) for x in candidate.get("labels") or [])
        attrs=candidate.get("attributes") or {}
        if isinstance(attrs,dict):
            for k,v in attrs.items():
                if isinstance(v,(list,tuple,set)): values.extend(str(x) for x in v)
                else: values.extend((str(k),str(v)))
        text=" ".join(values).lower()
        return set(re.findall(r"[a-z0-9-]+",text))

    @classmethod
    def score(cls, query: TargetQuery, candidate: dict[str, Any]) -> float:
        terms=cls._terms(candidate)
        label=str(candidate.get("class") or candidate.get("label") or "").lower()
        score=0.0
        if query.object_class:
            if query.object_class in terms or query.object_class==label: score+=0.28
            elif query.object_class=="vehicle" and label in {"car","truck","bus","bike","motorcycle"}: score+=0.22
            else: score-=0.20
        for color in query.colors:
            if color in terms: score+=0.22
        for word in query.clothing:
            if word in terms: score+=0.12
        for word in query.accessories:
            if word in terms: score+=0.10
        for word in query.spatial:
            spatial=candidate.get("spatial") or {}
            if isinstance(spatial,dict) and spatial.get(word) is True: score+=0.08
            elif word in terms: score+=0.05
        overlap=sum(1 for w in query.tokens if w in terms)
        if query.tokens: score+=min(0.20,0.04*overlap)
        score+=0.22*max(0.0,min(1.0,float(candidate.get("text_score") or 0.0)))
        score+=0.10*max(0.0,min(1.0,float(candidate.get("confidence") or 0.0)))
        return max(0.0,min(1.0,score))


class HawkeyeTargetLock:
    """Session-local visual lock. No real-world identity is created or persisted."""

    STATES={"SEARCHING","AMBIGUOUS","LOCKED","OCCLUDED","REACQUIRED","TARGET_LOST","UNLOCKED"}

    def __init__(self, *, acquire_threshold: float=.55, ambiguity_margin: float=.07,
                 reid_threshold: float=.78, max_missing_frames: int=20):
        self.acquire_threshold=float(acquire_threshold)
        self.ambiguity_margin=float(ambiguity_margin)
        self.reid_threshold=float(reid_threshold)
        self.max_missing_frames=max(1,int(max_missing_frames))
        self.reset()

    def reset(self):
        self.query: TargetQuery | None=None
        self.track_id: Any=None
        self.lock_key: str | None=None
        self.state="UNLOCKED"
        self.missing_frames=0
        self.last_bbox=None
        self.last_seen_at=None
        self.last_score=0.0
        return self.status()

    def acquire(self, command: str, candidates: Iterable[dict[str, Any]]) -> dict[str, Any]:
        self.query=TargetDescriptionParser.parse(command)
        ranked=[]
        for candidate in candidates or []:
            row=dict(candidate)
            score=VisualCandidateMatcher.score(self.query,row)
            row["match_score"]=round(score,4)
            ranked.append(row)
        ranked.sort(key=lambda x:x["match_score"],reverse=True)
        if not ranked or ranked[0]["match_score"]<self.acquire_threshold:
            self.state="SEARCHING";self.track_id=None;self.lock_key=None
            return {**self.status(),"candidates":ranked[:5],"reason":"no_confident_visual_match"}
        if len(ranked)>1 and ranked[0]["match_score"]-ranked[1]["match_score"]<self.ambiguity_margin:
            self.state="AMBIGUOUS";self.track_id=None;self.lock_key=None
            return {**self.status(),"candidates":ranked[:5],"reason":"multiple_similar_candidates"}
        best=ranked[0]
        self.track_id=best.get("tracking_id")
        self.lock_key=f"track:{self.track_id}" if self.track_id is not None else str(best.get("candidate_id") or "visual")
        self.last_bbox=best.get("bbox")
        self.last_seen_at=time.time()
        self.last_score=float(best["match_score"])
        self.missing_frames=0
        self.state="LOCKED"
        return {**self.status(),"candidate":best,"candidates":ranked[:5]}

    def update(self, candidates: Iterable[dict[str, Any]]) -> dict[str, Any]:
        rows=[dict(x) for x in (candidates or [])]
        if self.state in {"UNLOCKED","SEARCHING","AMBIGUOUS","TARGET_LOST"} or self.query is None:
            return {**self.status(),"reason":"no_active_lock"}
        exact=next((x for x in rows if self.track_id is not None and x.get("tracking_id")==self.track_id),None)
        if exact is not None:
            self.last_bbox=exact.get("bbox",self.last_bbox);self.last_seen_at=time.time();self.missing_frames=0
            self.last_score=max(self.last_score,float(exact.get("confidence") or 0.0))
            self.state="LOCKED"
            return {**self.status(),"candidate":exact}
        eligible=[]
        for x in rows:
            sim=float(x.get("reid_similarity") or 0.0)
            qscore=VisualCandidateMatcher.score(self.query,x)
            if sim>=self.reid_threshold and qscore>=max(.35,self.acquire_threshold-.15):
                eligible.append((.7*sim+.3*qscore,x))
        eligible.sort(key=lambda pair:pair[0],reverse=True)
        if eligible and (len(eligible)==1 or eligible[0][0]-eligible[1][0]>=self.ambiguity_margin):
            _,best=eligible[0]
            old=self.track_id;self.track_id=best.get("tracking_id",self.track_id)
            self.lock_key=f"track:{self.track_id}" if self.track_id is not None else self.lock_key
            self.last_bbox=best.get("bbox",self.last_bbox);self.last_seen_at=time.time();self.missing_frames=0
            self.state="REACQUIRED"
            return {**self.status(),"candidate":best,"previous_tracking_id":old}
        self.missing_frames+=1
        self.state="OCCLUDED" if self.missing_frames<=self.max_missing_frames else "TARGET_LOST"
        if self.state=="TARGET_LOST": self.track_id=None
        return {**self.status(),"reason":"target_not_confidently_visible"}

    def status(self) -> dict[str, Any]:
        return {
            "schema":"hawkeye.vtal.v1",
            "state":self.state,
            "query":self.query.as_dict() if self.query else None,
            "tracking_id":self.track_id,
            "lock_key":self.lock_key,
            "missing_frames":self.missing_frames,
            "last_bbox":self.last_bbox,
            "last_seen_at":self.last_seen_at,
            "match_score":round(float(self.last_score),4),
            "identity_scope":"session-local visual track only",
            "biometric_identity_persisted":False,
            "action_scope":"camera observation and framing only",
        }


class HawkeyeTargetBackendPlan:
    """Backend preference contract; loading/installing heavy models is a separate capability decision."""

    @staticmethod
    def plan(query: TargetQuery | str, *, edge_available=False, reid_available=False,
             grounding_available=False) -> dict[str, Any]:
        q=TargetDescriptionParser.parse(query) if isinstance(query,str) else query
        requires_open_vocab=bool(q.colors or q.clothing or q.accessories or len(q.tokens)>1)
        if grounding_available and requires_open_vocab:
            acquire="grounding_dino"
        else:
            acquire="mobile_detector_plus_attribute_evidence"
        track="bot_sort_reid" if reid_available else "native_tracking_id"
        reflex="esp_who_bytetrack" if edge_available else "mobile_motion_detection"
        return {
            "acquisition":acquire,
            "tracking":track,
            "edge_reflex":reflex,
            "reacquisition":"appearance_reid_then_visual_description",
            "fail_closed_on_ambiguity":True,
            "persistent_identity":False,
        }
