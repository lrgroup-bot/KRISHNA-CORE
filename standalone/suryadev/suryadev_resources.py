"""SURYADEV resource telemetry and conservative worker admission.

Optional psutil: pip install psutil. No metrics are fabricated if unavailable.
85% is a ceiling for admission, not a utilization target.
"""
from __future__ import annotations
import json
import os
import platform
from functools import lru_cache
import shutil
import subprocess
import time
from pathlib import Path

@lru_cache(maxsize=1)
def hardware_identity():
    """Best-effort static inventory, sampled once and never mistaken for utilization."""
    identity={"cpu_name":platform.processor()[:120] or "unknown",
              "gpu_name":"unavailable","gpu_inventory_verified":False,
              "platform":platform.platform()[:120],
              "logical_cpus":os.cpu_count() or 1}
    if os.name=="nt":
        command=(
            "$cpu=Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name;"
            "$g=Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name;"
            "@{cpu_name=$cpu;gpu_names=@($g)} | ConvertTo-Json -Compress"
        )
        try:
            process=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                                   "-Command",command],capture_output=True,
                                  text=True,timeout=5,check=True)
            payload=json.loads(process.stdout)
            names=payload.get("gpu_names") or []
            if isinstance(names,str):names=[names]
            if isinstance(names,list) and names:
                identity["gpu_name"]=", ".join(str(x)[:100] for x in names[:4])
                identity["gpu_inventory_verified"]=True
            if payload.get("cpu_name"):
                identity["cpu_name"]=str(payload["cpu_name"])[:120]
        except (OSError,ValueError,subprocess.SubprocessError):
            pass
    return identity


def network_interfaces(psutil_module):
    """Inspect physical/link telemetry without a paid speed test or remote probe.

    Interface UP and negotiated Mbps are not proof of Internet availability.
    Loopback and virtual-only links are not counted as public connectivity.
    """
    try:
        stats = psutil_module.net_if_stats()
    except (OSError, AttributeError, RuntimeError):
        return {"interface_up": None, "link_speed_mbps": None,
                "internet_reachable": None, "reachability": "unverified"}
    candidates = []
    for name, device in stats.items():
        lname = name.casefold()
        if any(bit in lname for bit in ("loopback", "lo0", "veth", "docker", "tun", "tap")) or lname == "lo":
            continue
        if bool(device.isup):
            speed = getattr(device, "speed", None)
            candidates.append(float(speed) if isinstance(speed, (int,float)) and speed > 0 else None)
    return {"interface_up": bool(candidates),
            "link_speed_mbps": max((v for v in candidates if v is not None), default=None),
            "internet_reachable": None,
            "reachability": "unverified_until_authenticated_core_or_approved_source_response",
            "note": "Interface state and link rate are not measured internet download speed"}


def snapshot(data_dir, sample_seconds=0.2):
    try:
        import psutil
    except ImportError:
        return {"available": False, "reason": "Install optional psutil for CPU, RAM, disk and network monitoring",
                "gpu": {"available": False, "reason": "GPU monitoring requires a supported vendor utility"}}
    cpu = psutil.cpu_percent(interval=max(0.1, min(float(sample_seconds), 1.0)))
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path(data_dir).resolve().anchor))
    net = psutil.net_io_counters()
    network = network_interfaces(psutil)
    gpu = {"available": False, "reason": "No supported NVIDIA telemetry"}
    if shutil.which("nvidia-smi"):
        try:
            p = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
                                "--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=3,check=True)
            vals = [float(x.strip()) for x in p.stdout.strip().splitlines()[0].split(",")]
            gpu = {"available": True, "usage_percent": vals[0], "vram_used_mb": vals[1],
                   "vram_total_mb": vals[2], "vram_percent": round(100*vals[1]/vals[2],1) if vals[2] else None}
        except (OSError, ValueError, subprocess.SubprocessError, IndexError):
            pass
    return {"available": True, "cpu_percent": cpu, "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used/1024**3,2), "ram_total_gb": round(mem.total/1024**3,2),
            "disk_percent": disk.percent, "disk_free_gb": round(disk.free/1024**3,2),
            "network_bytes_sent_total": net.bytes_sent, "network_bytes_received_total": net.bytes_recv,
            "network_interface_speed_mbps": network["link_speed_mbps"],
            "network_interface_up": network["interface_up"],
            "internet_reachable": network["internet_reachable"],
            "internet_reachability": network["reachability"],
            "internet_speed_mbps": None,
            "gpu": gpu, "sample_time": time.time()}

def admission(data_dir, ceiling=85):
    s = snapshot(data_dir)
    if not s.get("available"):
        return False, "telemetry unavailable", s
    for key in ("cpu_percent", "ram_percent", "disk_percent"):
        if s[key] >= ceiling:
            return False, key + " reached ceiling", s
    gpu = s["gpu"]
    if gpu.get("available") and (gpu["usage_percent"] >= ceiling or
                                 (gpu.get("vram_percent") or 0) >= ceiling):
        return False, "GPU reached ceiling", s
    if s["disk_free_gb"] < 2:
        return False, "low storage", s
    return True, "within admission limits", s

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--data",required=True)
    a=p.parse_args()
    print(json.dumps(snapshot(a.data),indent=2))
