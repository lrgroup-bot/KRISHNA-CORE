from __future__ import annotations
import uuid, time

"""Evidence-earned BRAHMAGYAN Research Fellowship and scientific career ladder."""

RANKS=("applicant","intern_shishya","research_shishya","doctor_research_fellow",
       "junior_scientist","scientist","senior_scientist","principal_scientist")
RANK_INDEX={x:i for i,x in enumerate(RANKS)}
PROMOTION_DIMENSIONS=("evidence_quality","replication","reasoning","correction_behavior",
                      "safety_reliability","collaboration","resource_efficiency")
PERMANENCE_SIGNALS=("persistent_workload","specialty_depth","knowledge_continuity",
                    "validated_output","low_duplication","resource_value")

def new_fellow(parent_rishi,specialty,name=None):
    return {
        "fellow_id":str(uuid.uuid4()),"name":str(name or specialty).strip(),
        "parent_rishi":str(parent_rishi).strip().lower(),"specialty":str(specialty).strip(),
        "rank":"applicant","permanent":False,"probation":True,"created_at":time.time(),
        "research_cv":{"missions":0,"sources_examined":0,"reproductions":0,"hypotheses":0,
                       "supported":0,"rejected":0,"unresolved":0,"corrections_accepted":0,
                       "validated_discoveries":0,"dangerous_misses":0},
        "authority":"research only; rank never overrides evidence/QC",
    }

def promotion_review(fellow,target_rank,scores,*, thesis_defended=False,
                     independent_replications=0,dangerous_misses=0):
    current=RANK_INDEX[fellow["rank"]]; target=RANK_INDEX[str(target_rank)]
    if target!=current+1:return {"approved":False,"reason":"promotion_must_be_one_rank_at_a_time"}
    vals={k:max(0.0,min(1.0,float(scores.get(k,0)))) for k in PROMOTION_DIMENSIONS}
    threshold=.65 if target<=2 else .75 if target<=4 else .82
    blockers=[]
    if min(vals.values())<threshold:blockers.append("dimension_below_threshold")
    if target>=3 and not thesis_defended:blockers.append("independent_thesis_defense_required")
    if target>=4 and int(independent_replications)<3:blockers.append("replication_record_insufficient")
    if int(dangerous_misses)>0:blockers.append("unresolved_dangerous_miss")
    return {
        "approved":not blockers,"from":fellow["rank"],"to":target_rank,"scores":vals,
        "threshold":threshold,"blockers":blockers,
        "examiners":["parent_rishi","gautama","bharadvaja","cross_domain_rishi","brahma"],
        "policy":"promotion is evidence/examination based, never tenure or self-certification",
    }

def permanence_review(*, workload_ratio,specialty_depth,knowledge_continuity,
                      validated_output,duplicate_ratio,resource_value):
    score=(.22*workload_ratio+.20*specialty_depth+.18*knowledge_continuity+
           .18*validated_output+.12*(1-max(0,min(1,duplicate_ratio)))+.10*resource_value)
    return {
        "recommended":score>=.72,"score":round(score,4),"probation_required":True,
        "brahma_review_required":True,"ai_hr_review_required":True,
        "policy":"temporary-first; permanence is earned only by sustained specialist value",
    }

def research_cv_score(cv):
    cv=dict(cv or {})
    good=(cv.get("reproductions",0)*2+cv.get("validated_discoveries",0)*5+
          cv.get("corrections_accepted",0)+cv.get("supported",0)+cv.get("rejected",0)*.25)
    bad=cv.get("dangerous_misses",0)*20
    return max(0.0,round(float(good)-float(bad),2))
