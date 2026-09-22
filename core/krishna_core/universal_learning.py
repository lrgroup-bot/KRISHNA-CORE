from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, time, uuid


@dataclass(frozen=True)
class LearningIntent:
    intent: str
    confidence: float
    modalities: tuple[str, ...]
    deep_research: bool
    remember: bool


class UniversalLearningRuntime:
    """Natural-intent multimodal learning/escalation for KRISHNA/Hawkeye.

    No fixed wake phrase or command is required. The caller supplies the user's
    utterance plus available evidence modalities. This runtime records source
    provenance, classifies intent, routes unknowns to a Rishi domain, and keeps
    unresolved claims explicitly UNKNOWN rather than inventing an answer.
    """

    LEARN_CUES=("learn","study","remember","understand","analyse","analyze","research","check this",
                "listen to","watch this","read this","find out","what is this","what sound","what noise",
                "elaborate","explain this","master")
    DEEP_CUES=("research","master","deep","verify","cross-check","cross check","find out","elaborate")
    REMEMBER_CUES=("learn","remember","study","master")
    RISHI_ROUTES={
        "physics":"kanada","material":"kanada","rock":"kanada","mineral":"kanada","machine":"kanada",
        "engineering":"kanada","system":"kapila","cognition":"kapila","behavior":"kapila",
        "language":"patanjali","speech":"patanjali","sound":"patanjali","audio":"patanjali",
        "evidence":"yajnavalkya","epistemology":"yajnavalkya","unknown":"yajnavalkya",
        "environment":"agastya","plant":"agastya","animal":"agastya","ecology":"agastya",
    }
    SOUND_CLASSES=("speech","music","bird","animal","insect","vehicle","engine","machine","tool",
                   "alarm","impact","water","rain","thunder","wind","fire","environment","unknown")

    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir); self.root.mkdir(parents=True,exist_ok=True)
        self.ledger=self.root/"universal-learning.jsonl"
        self.unknowns=self.root/"unknown-registry.jsonl"

    def infer_intent(self,text:str,modalities=None)->dict:
        raw=str(text or "").strip(); low=raw.lower()
        modalities=tuple(sorted(set(str(x).lower() for x in (modalities or []))))
        hits=sum(1 for cue in self.LEARN_CUES if cue in low)
        intent="learn" if any(x in low for x in self.REMEMBER_CUES) else (
            "investigate" if hits or modalities else "answer")
        row=LearningIntent(intent,min(0.99,0.55+0.08*hits) if hits else 0.45,modalities,
                           any(x in low for x in self.DEEP_CUES),
                           any(x in low for x in self.REMEMBER_CUES))
        return asdict(row)

    def classify_sound_request(self,text:str,observations=None)->dict:
        low=str(text or "").lower(); candidates=[]
        for label in self.SOUND_CLASSES:
            if label!="unknown" and label in low:candidates.append(label)
        return {"modality":"audio","requested_classification":True,
                "candidate_classes":candidates or ["unknown"],
                "observations":dict(observations or {}),
                "rule":"audio evidence may identify a sound class; uncertain source/cause remains UNKNOWN"}

    def route_rishi(self,subject:str)->str:
        low=str(subject or "").lower()
        for key,rishi in self.RISHI_ROUTES.items():
            if key in low:return rishi
        return "yajnavalkya"

    def ingest(self,*,utterance:str,source_type:str,source_ref:str="",modalities=None,
               subject:str="",confidence:float=0.0,analysis:str="",evidence_state:str="UNKNOWN")->dict:
        intent=self.infer_intent(utterance,modalities)
        confidence=max(0.0,min(1.0,float(confidence)))
        state=str(evidence_state).upper()
        if state not in {"MEASURED","OBSERVED","INFERRED","PREDICTED","UNKNOWN"}:state="UNKNOWN"
        uid=str(uuid.uuid4())
        row={"learning_id":uid,"created_at":time.time(),"utterance":str(utterance),
             "intent":intent,"source_type":str(source_type),"source_ref":str(source_ref),
             "modalities":intent["modalities"],"subject":str(subject),"analysis":str(analysis),
             "confidence":confidence,"evidence_state":state,"rishi":self.route_rishi(subject),
             "escalate":confidence<0.70 or state=="UNKNOWN",
             "provenance_hash":hashlib.sha256((str(source_type)+"|"+str(source_ref)+"|"+str(subject)).encode()).hexdigest()}
        with self.ledger.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
        if row["escalate"]:
            unknown={"unknown_id":"UNKNOWN-"+uid,"learning_id":uid,"subject":str(subject) or "unresolved",
                     "rishi":row["rishi"],"status":"research_required","created_at":time.time(),
                     "research_plan":["inspect all supplied modalities","search existing Gyan-Bhandar",
                                      "create temporary specialist Shishya if needed",
                                      "cross-check independent sources","return fast provisional result",
                                      "preserve unresolved uncertainty","promote verified reusable findings"]}
            with self.unknowns.open("a",encoding="utf-8") as f:f.write(json.dumps(unknown,ensure_ascii=False)+"\n")
            row["unknown_resolution"]=unknown
        return row
