from __future__ import annotations

"""Adaptive SURYADEV worker governor for private/lightweight browser research nodes."""

TARGET_UTILIZATION=.80
SOFT_LIMIT=.80
HARD_LIMIT=.90
RECOVERY_LIMIT=.70

def machine_snapshot(*,cpu_percent,ram_percent,gpu_percent=0,vram_percent=0,
                     network_percent=0,thermal_state="normal",free_disk_gb=0):
    vals={
        "cpu":max(0,min(1,float(cpu_percent)/100)),
        "ram":max(0,min(1,float(ram_percent)/100)),
        "gpu":max(0,min(1,float(gpu_percent)/100)),
        "vram":max(0,min(1,float(vram_percent)/100)),
        "network":max(0,min(1,float(network_percent)/100)),
    }
    vals["peak"]=max(vals.values())
    vals["thermal_state"]=str(thermal_state or "unknown").lower()
    vals["free_disk_gb"]=max(0,float(free_disk_gb))
    return vals

def capacity_decision(snapshot,current_workers,*,max_workers=256):
    peak=float(snapshot.get("peak",0)); thermal=snapshot.get("thermal_state","unknown")
    current=max(0,int(current_workers)); cap=max(1,int(max_workers))
    danger=thermal in {"hot","critical","throttling"} or peak>=HARD_LIMIT
    if danger:
        target=max(1,int(current*.5)) if current else 0
        action="shed_load"
    elif peak>=SOFT_LIMIT:
        target=max(1,current-1) if current else 0
        action="backoff"
    elif peak<RECOVERY_LIMIT:
        target=min(cap,current+max(1,min(8,current//4 or 1)))
        action="expand"
    else:
        target=current;action="hold"
    return {
        "action":action,"current_workers":current,"target_workers":target,
        "target_utilization":TARGET_UTILIZATION,
        "rule":"expand gradually below 70%; hold near 70-80%; back off at 80%; shed aggressively at 90% or thermal danger",
    }

def browser_policy():
    return {
        "name":"SURYDEV Lightweight Research Browser",
        "branded_chrome_required":False,
        "engine_policy":"use project-controlled lightweight/headless engine; prefer direct HTTP/API extraction when rendering is unnecessary",
        "privacy":{
            "telemetry":"disabled_by_default","sync":"disabled","third_party_extensions":"disabled",
            "per_job_isolation":True,"nonpersistent_context_default":True,
            "credentials":"never_capture; explicit owner handoff only",
        },
        "resource_policy":{
            "images":"block unless evidence requires them","autoplay":"job-controlled",
            "ads_trackers":"block where lawful and compatible","service_workers":"block unless required",
            "javascript":"enable only when source requires rendering",
        },
    }

def recovery_policy():
    return {
        "heartbeat_seconds":15,"checkpoint_seconds":30,
        "watchdog":True,"restart_worker_on_crash":True,"restart_browser_on_hang":True,
        "resume_from_checkpoint":True,"requeue_unacknowledged_jobs":True,
        "duplicate_suppression":True,"exponential_backoff":True,
        "node_quarantine_after_repeated_failure":True,
        "never_exceed_hard_limit":HARD_LIMIT,
    }
