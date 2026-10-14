"""CHANDRADEV physical watchdog policy.

A local, privacy-bounded CCTV-style observer for KRISHNA's own physical system.
Raw media is temporary evidence; durable knowledge is distilled metadata/findings.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib,time

@dataclass(frozen=True)
class PhysicalEvent:
    kind:str
    confidence:float
    source:str="usb_uvc_webcam"
    detail:str=""

WATCHDOG_POLICY={
 "role":"KRISHNA_PHYSICAL_WATCHDOG",
 "continuous_observation":True,
 "event_triggered_heavy_vision":True,
 "raw_media_is_temporary":True,
 "raw_media_to_gyan":False,
 "delete_after_verified_distillation":True,
 "incident_hold_supported":True,
 "visual_retest_after_error_fix":True,
 "suryadev_unresolved_escalates_to_chandradev":True,
 "timestamp_required":True,
 "sha256_required":True,
 "camera_health_required":True,
 "owner_private_space_default":"never_upload",
}

def should_escalate(*,suryadev_resolved:bool,physical_visibility_needed:bool,visual_uncertainty:float=0.0):
    return bool((not suryadev_resolved and physical_visibility_needed) or float(visual_uncertainty)>=0.5)

def evidence_window(*,event_at:float|None=None,pre_seconds:int=15,post_seconds:int=30):
    t=float(event_at if event_at is not None else time.time())
    pre=max(0,min(int(pre_seconds),120));post=max(0,min(int(post_seconds),300))
    return {"start":t-pre,"event":t,"end":t+post,"pre_seconds":pre,"post_seconds":post}

def visual_repair_verdict(*,before_issues,after_issues,deterministic_tests_passed:bool):
    before=list(before_issues or []);after=list(after_issues or [])
    if not deterministic_tests_passed:return {"state":"BLOCKED","reason":"deterministic_tests_failed"}
    if after:return {"state":"RETEST_REQUIRED","reason":"visual_issue_remains","remaining":after}
    return {"state":"PASSED","reason":"deterministic_and_visual_retest_passed","resolved_count":len(before)}

def camera_health(*,frame_age_seconds:float,blur_score:float,expected_view:bool,connected:bool=True):
    reasons=[]
    if not connected:reasons.append("camera_disconnected")
    if float(frame_age_seconds)>10:reasons.append("stale_frame")
    if float(blur_score)<0.2:reasons.append("image_too_blurry")
    if not expected_view:reasons.append("camera_misaligned_or_view_lost")
    return {"healthy":not reasons,"reasons":reasons,"claim_observation":not reasons}

def media_disposition(*,distilled:bool,distillation_verified:bool,incident_hold:bool=False,legal_or_owner_hold:bool=False):
    if incident_hold or legal_or_owner_hold:return {"delete_raw":False,"reason":"evidence_hold"}
    if distilled and distillation_verified:return {"delete_raw":True,"reason":"verified_learning_distilled"}
    return {"delete_raw":False,"reason":"awaiting_verified_distillation"}

def media_fingerprint(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()
