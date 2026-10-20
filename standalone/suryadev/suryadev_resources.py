"""SURYADEV resource telemetry and conservative worker admission.

Optional psutil: pip install psutil. No metrics are fabricated if unavailable.
85% is a ceiling for admission, not a utilization target.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import time
from pathlib import Path

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
            "network_interface_speed_mbps": None, "internet_speed_mbps": None,
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
