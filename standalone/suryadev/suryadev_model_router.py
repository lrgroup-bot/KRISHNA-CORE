"""Resource-aware local SURYADEV model selection; no cloud or downloads.

'auto' chooses installed qwen3.5:2b only with *fresh* safe telemetry
and a fast local-only Ollama API response. Otherwise it uses collector mode.
No heavy model is selected by automatic policy. Decisions are explainable and
made per worker start; per-task dynamic switching needs its own validation.
"""
from __future__ import annotations

import json
import math
import urllib.request
from urllib.error import URLError

SMALL_MODEL = "qwen3.5:2b"
LOCAL_TAGS = "http://127.0.0.1:11434/api/tags"
MAX_REPLY = 128 * 1024


def installed_small_model(*, opener=None):
    """Probe only an existing loopback Ollama service; never download weights."""
    from urllib.request import ProxyHandler, build_opener
    client = opener if opener is not None else build_opener(ProxyHandler({}))
    try:
        response = client.open(urllib.request.Request(
            LOCAL_TAGS, method="GET", headers={"Accept":"application/json"}),
            timeout=1.0)
        with response:
            raw = response.read(MAX_REPLY + 1)
        if len(raw) > MAX_REPLY:
            return False
        parsed = json.loads(raw)
        models = parsed.get("models") if isinstance(parsed, dict) else None
        return isinstance(models, list) and any(
            isinstance(item, dict) and item.get("name") == SMALL_MODEL
            for item in models)
    except (OSError, ValueError, RuntimeError, URLError):
        return False


def decide_model(report, *, installed=False):
    """Fail closed to evidence collector; never invent measured headroom."""
    if not isinstance(report, dict) or not report.get("available"):
        return {"model":"collector", "reason":"hardware_telemetry_unavailable",
                "auto":True}
    required=("cpu_percent","ram_percent","ram_total_gb","ram_used_gb","disk_free_gb")
    measurements = {}
    for name in required:
        value=report.get(name)
        if type(value) not in (int,float) or not math.isfinite(value) or value < 0:
            return {"model":"collector", "reason":"hardware_measurement_missing",
                    "auto":True}
        measurements[name]=float(value)
    cpu,ram,total,used,free_disk=[measurements[name] for name in required]
    free=total-used
    if cpu >= 65 or ram >= 65 or total < 8 or free < 3.5 or free_disk < 4:
        return {"model":"collector", "reason":"insufficient_model_headroom",
                "auto":True}
    if report.get("temperature_max_c") is not None:
        try:
            if float(report["temperature_max_c"]) >= 80:
                return {"model":"collector","reason":"thermal_caution",
                        "auto":True}
        except (ValueError,TypeError):
            return {"model":"collector","reason":"thermal_unknown","auto":True}
    if report.get("battery_plugged") is False:
        battery=report.get("battery_percent")
        if type(battery) not in (int,float) or not math.isfinite(battery) or battery < 50:
            return {"model":"collector","reason":"battery_caution","auto":True}
    gpu=report.get("gpu") or {}
    if not isinstance(gpu,dict):
        return {"model":"collector","reason":"gpu_telemetry_invalid","auto":True}
    if gpu.get("available"):
        for metric in ("usage_percent","vram_percent"):
            value=gpu.get(metric)
            if value is not None and (
                type(value) not in (int,float) or not math.isfinite(value) or value >= 75):
                return {"model":"collector","reason":"gpu_caution","auto":True}
    if not installed:
        return {"model":"collector","reason":"small_model_not_installed",
                "auto":True}
    return {"model":SMALL_MODEL, "reason":"installed_small_model_and_measured_headroom",
            "auto":True}


def resolve_model(requested, data_root, *, measurement=None, probe=installed_small_model):
    if requested != "auto":
        return {"model":requested,"reason":"explicit_operator_selection","auto":False}
    if measurement is None:
        from suryadev_resources import snapshot
        measurement=snapshot(data_root)
    # Avoid a 1s Ollama probe unless hardware admission already looks safe.
    preliminary=decide_model(measurement,installed=False)
    if preliminary["reason"] != "small_model_not_installed":
        return preliminary
    return decide_model(measurement,installed=bool(probe()))
