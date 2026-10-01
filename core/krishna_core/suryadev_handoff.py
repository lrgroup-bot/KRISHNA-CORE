from __future__ import annotations
import uuid,time

"""Bounded SURYADEV to CHANDRADEV escalation without blocking other lanes."""

VISUAL_REASONS=("screen_only_information","diagram_requires_visual_reasoning","physical_demonstration",
                "animation_or_motion_is_evidence","gui_state_or_interaction","transcript_insufficient",
                "ocr_or_layout_ambiguity","human_style_visual_review")

def chandradev_handoff(*,job_id,source_ref,reason,question="",timestamps=None,
                       transcript_confidence=1.0,visual_relevance=0.0):
    reason=str(reason or "").strip()
    needs_visual=reason in VISUAL_REASONS or float(visual_relevance)>=.7 or float(transcript_confidence)<.45
    if not needs_visual:
        return {"handoff":False,"continue_suryadev":True,"reason":"visual_escalation_not_justified"}
    return {
        "handoff":True,"handoff_id":"SURYA-CHANDRA-"+uuid.uuid4().hex[:16],
        "created_at":time.time(),"from":"SURYDEV","to":"CHANDRADEV",
        "job_id":str(job_id),"source_ref":str(source_ref),"reason":reason,
        "question":str(question),"timestamps":list(timestamps or [])[:50],
        "scope":"inspect only the requested visual evidence and return findings/provenance",
        "continue_suryadev":True,"blocking":False,
        "authority":"CHANDRADEV returns visual evidence; BRAHMA/Rishi verification remains authoritative",
    }

def simultaneous_lane_policy():
    return {
        "parallel":True,"single_shared_capacity_governor":True,
        "lanes":["api","web_text","document","repository","transcript","audio","video","handoff"],
        "fair_scheduling":True,"priority_by_learning_value":True,
        "reserve_headroom":True,"overload":"pause/suspend lowest-value lanes before critical work",
        "handoff_does_not_pause_unrelated_work":True,
    }
