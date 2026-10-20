"""PARIKSHA: independent cognitive evaluation and adaptive capability tracking.

Scores are machine capability metrics, never human IQ claims. Test material must not be
written into learner memory before evaluation; unseen transfer is the primary improvement gate.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, math, time

ABILITIES=("reasoning","mathematics","abstraction","coding","planning","scientific_reasoning","knowledge_integration","novel_transfer","uncertainty","reality_verification","calibration")
WEIGHTS={"reasoning":.18,"mathematics":.12,"abstraction":.12,"coding":.10,"planning":.10,"scientific_reasoning":.08,"knowledge_integration":.08,"novel_transfer":.07,"uncertainty":.05,"reality_verification":.05,"calibration":.05}

@dataclass(frozen=True)
class ExamItem:
    item_id:str; ability:str; difficulty:float; prompt_hash:str; source_family:str="generated"; public:bool=False

def item_fingerprint(prompt:str)->str:
    return hashlib.sha256(str(prompt).encode("utf-8")).hexdigest()

def capability_report(scores,*,previous=None,difficulty=0.5):
    clean={k:max(0.0,min(1.0,float(scores.get(k,0)))) for k in ABILITIES}
    kcci=100.0*sum(WEIGHTS[k]*clean[k] for k in ABILITIES)
    prev=None if previous is None else float(previous)
    return {"schema":"krishna.kcci.v1","kcci":round(kcci,2),"abilities":{k:round(v*100,2) for k,v in clean.items()},
            "difficulty":round(max(0.0,min(1.0,float(difficulty))),3),"delta":None if prev is None else round(kcci-prev,2),
            "human_iq_equivalent":None,"measured_at":time.time()}

def next_difficulty(current,accuracy,target=.85,rate=.15):
    # Keep moving the frontier upward when the learner masters the present band.
    return max(0.05,min(1.0,float(current)+float(rate)*(float(accuracy)-float(target))))

def contamination_gate(*,prompt_hash,known_training_hashes=(),previous_exam_hashes=(),public=False):
    contaminated=str(prompt_hash) in set(known_training_hashes)|set(previous_exam_hashes)
    return {"allowed":not contaminated,"contaminated":contaminated,"public":bool(public),
            "reason":"seen_item" if contaminated else "unseen"}

def error_fingerprint(*,ability,failure_type,confidence,correct,transfer=False):
    return {"ability":str(ability),"failure_type":str(failure_type),"confidence":max(0.0,min(1.0,float(confidence))),
            "correct":bool(correct),"transfer":bool(transfer),"overconfident":bool(not correct and float(confidence)>=.8)}

def immune_review(claim,*,evidence_families=0,contradictions=0,stale=False,reality_checked=False):
    attacks=[]
    if evidence_families<2:attacks.append("insufficient_independent_evidence")
    if contradictions:attacks.append("unresolved_contradiction")
    if stale:attacks.append("stale_evidence")
    if not reality_checked:attacks.append("reality_not_checked")
    return {"claim":str(claim),"passed":not attacks,"attacks":attacks,
            "rule":"memory strength and model agreement never substitute for evidence"}

PROFILES={
 "KRISHNA":{"examiner":"PARIKSHA-K","isolation":"krishna-private","focus":list(ABILITIES)},
 "LR_GROUP":{"examiner":"PARIKSHA-LR","isolation":"lr-group-private","focus":["reasoning","mathematics","planning","coding","knowledge_integration","novel_transfer","uncertainty","calibration"]},
}
