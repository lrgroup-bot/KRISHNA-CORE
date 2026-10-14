"""Brain-inspired associative cognition primitives.

This layer proposes associations and replay candidates only. It has no authority to mark
knowledge verified; Gyan-Bhandar/BRAHMA/knowledge-law gates remain authoritative.
"""
from __future__ import annotations
import math,time

def association_strength(*,semantic,temporal,context,causal,goal):
    vals=[semantic,temporal,context,causal,goal]
    vals=[max(0.0,min(1.0,float(x))) for x in vals]
    return .30*vals[0]+.20*vals[1]+.20*vals[2]+.15*vals[3]+.15*vals[4]

def branch_decision(similarity,*,attach=.72,new=.30,salience=.5):
    s=max(0.0,min(1.0,float(similarity)));m=max(0.0,min(1.0,float(salience)))
    if s>=attach:return "attach"
    if s>new:return "cross_link"
    return "new_branch" if m>=.5 else "episodic_only"

def prediction_error(predicted,observed):
    if isinstance(predicted,(int,float)) and isinstance(observed,(int,float)):
        scale=max(1.0,abs(float(predicted)),abs(float(observed)))
        return min(1.0,abs(float(observed)-float(predicted))/scale)
    return 0.0 if predicted==observed else 1.0

def replay_score(*,novelty,usefulness,surprise,contradiction,uncertainty,prediction_error_value):
    v=[max(0.0,min(1.0,float(x))) for x in (novelty,usefulness,surprise,contradiction,uncertainty,prediction_error_value)]
    return round(.15*v[0]+.20*v[1]+.15*v[2]+.15*v[3]+.15*v[4]+.20*v[5],6)

def idea_score(*,novelty,utility,plausibility,cross_domain_distance,evidence_potential):
    vals=[max(0.0,min(1.0,float(x))) for x in (novelty,utility,plausibility,cross_domain_distance,evidence_potential)]
    # Geometric mean prevents one excellent dimension from hiding a zero-evidence idea.
    return round(math.prod(vals)**(1/len(vals)),6)

def plasticity_delta(*,pre,post,eligibility,modulator,learning_rate=.05):
    return float(learning_rate)*float(pre)*float(post)*float(eligibility)*max(-1.0,min(1.0,float(modulator)))

def cognitive_candidate(kind,payload,score,parents=()):
    return {"kind":str(kind),"payload":payload,"score":max(0.0,min(1.0,float(score))),
            "parents":[str(x) for x in parents],"status":"candidate","verified":False,
            "promotion_authority":"BRAHMA+Gyan-Bhandar knowledge-law gate","created_at":time.time()}
