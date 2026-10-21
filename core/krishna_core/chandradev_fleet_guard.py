"""CHANDRADEV independent, read-only health assessment of paired SURYADEV nodes.

Not a second scheduler and not an OS hard cap. Never assumes temperatures
or GPU telemetry absent from device hardware are known good.
"""
from __future__ import annotations
import math
import time


def inspect_fleet(snapshot, *, now=None, ceiling=85, caution=75):
    now=float(time.time() if now is None else now)
    if not math.isfinite(now) or now <= 0 or not 0 < caution < ceiling <=100:
        raise ValueError("invalid inspection parameters")
    nodes=snapshot.get("nodes") if isinstance(snapshot,dict) else None
    if not isinstance(nodes,list):
        raise ValueError("paired fleet node snapshot required")
    out=[]
    for n in nodes:
        if not isinstance(n,dict):raise ValueError("invalid node entry")
        ident=str(n.get("device_id") or "")
        if not ident:raise ValueError("node ID required")
        age=now-float(n.get("last_seen") or 0)
        stale=not 0<=age<=150
        missing=[]
        reasons=[]
        if stale:reasons.append("heartbeat_stale")
        if n.get("authenticated") is not True:reasons.append("pairing_unverified")
        if not n.get("worker_running"):reasons.append("worker_not_running")
        if not n.get("network_online"):reasons.append("network_offline")
        if n.get("last_error"):reasons.append("worker_error")
        sample_age=now-float(n.get("telemetry_sample_at") or 0)
        if not 0<=sample_age<=45:reasons.append("telemetry_stale")
        for k in ("cpu_percent","ram_percent","disk_percent"):
            v=n.get(k)
            if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=100:
                missing.append(k)
            elif v>=ceiling:
                reasons.append(k+"_critical")
            elif v>=caution:
                reasons.append(k+"_pressure")
        if missing:reasons.append("missing_metrics")
        if n.get("thermal_state") in ("hot","critical","overheating"):
            reasons.append("thermal_alert")
        elif n.get("thermal_state") in (None,"","unknown"):
            missing.append("temperature")
        gpu=n.get("gpu") or {}
        if not isinstance(gpu,dict) or not gpu.get("available"):
            missing.append("gpu_utilization")
        if stale or "pairing_unverified" in reasons or "worker_error" in reasons:
            level="offline_or_untrusted"
        elif any(x.endswith("_critical") for x in reasons) or "thermal_alert" in reasons:
            level="critical"
        elif any(x.endswith("_pressure") for x in reasons):
            level="caution"
        elif reasons:
            level="degraded"
        elif missing:
            level="partial_monitoring"
        else:
            level="healthy"
        out.append({"device_id":ident,"state":level,"reasons":sorted(set(reasons)),
                    "unmeasured":sorted(set(missing)),
                    "new_job_admission_recommended":level in ("healthy","caution","partial_monitoring")
                       and "telemetry_stale" not in reasons,
                    "heartbeat_age_seconds":round(max(0,age),2),
                    "sample_age_seconds":round(max(0,sample_age),2)})
    return {"nodes":out,"node_count":len(out),
            "alerts":sum(n["state"]!="healthy" for n in out),
            "checked_at":now,
            "policy":"read-only warning/recommendation; BRAHMA admission policy remains authoritative; no OS-level 85% guarantee"}
