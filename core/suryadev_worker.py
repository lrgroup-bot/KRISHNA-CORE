from __future__ import annotations

"""Portable Windows controller entrypoint for SURYDEV.

The EXE intentionally remains a small control plane. Free capture/ASR/browser/VLM
components live as sidecar tools in the external workspace so they can be upgraded
independently and selected according to the workstation hardware.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import ctypes

from krishna_core.suryadev_device_profile import SuryadevDeviceSelector
from krishna_core.suryadev_device_client import SuryadevDeviceClient


AGENT = "SURYDEV"
VERSION = "suryadev-worker-v1"
OPTIONAL_MODULES = {
    "mss": "screen capture",
    "cv2": "camera/frame processing",
    "pyaudiowpatch": "Windows system-audio loopback",
    "faster_whisper": "speech-to-text",
    "scenedetect": "scene/keyframe detection",
    "playwright": "isolated browser research",
}
OPTIONAL_TOOLS = {
    "ffmpeg": "media extraction",
    "ffprobe": "media inspection",
    "yt-dlp": "authorized media/subtitle retrieval",
}


def _windows_memory_mb():
    if os.name!="nt":return 0
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_=[
                ("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),
                ("ullTotalPhys",ctypes.c_ulonglong),("ullAvailPhys",ctypes.c_ulonglong),
                ("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),
                ("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual",ctypes.c_ulonglong),
            ]
        s=MEMORYSTATUSEX();s.dwLength=ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
            return int(s.ullTotalPhys//(1024*1024))
    except Exception:
        pass
    return 0


def _windows_power():
    if os.name!="nt":return {"battery_percent":None,"charging":False,"battery_present":False}
    try:
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_=[
                ("ACLineStatus",ctypes.c_ubyte),("BatteryFlag",ctypes.c_ubyte),
                ("BatteryLifePercent",ctypes.c_ubyte),("SystemStatusFlag",ctypes.c_ubyte),
                ("BatteryLifeTime",ctypes.c_ulong),("BatteryFullLifeTime",ctypes.c_ulong),
            ]
        s=SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
            present=not bool(s.BatteryFlag&128)
            pct=None if s.BatteryLifePercent==255 else int(s.BatteryLifePercent)
            return {"battery_percent":pct,"charging":s.ACLineStatus==1,"battery_present":present}
    except Exception:
        pass
    return {"battery_percent":None,"charging":False,"battery_present":False}


def device_profile(modules=None,tools=None):
    modules=modules or {}
    tools=tools or {}
    power=_windows_power()
    try:free_gb=round(shutil.disk_usage(Path.cwd()).free/(1024**3),2)
    except Exception:free_gb=0.0
    system=platform.system().lower()
    if system=="windows":
        device_class="laptop" if power.get("battery_present") else "desktop"
    elif system=="darwin":
        device_class="macbook" if power.get("battery_present") else "desktop"
    else:
        device_class="laptop" if power.get("battery_present") else "pc"
    memory_mb=_windows_memory_mb()
    profile={
        "platform":system or os.name,
        "platform_version":platform.release(),
        "device_class":device_class,
        "model_family":platform.machine(),
        "memory_mb":memory_mb,
        "cpu_cores":os.cpu_count() or 0,
        "free_storage_gb":free_gb,
        "battery_percent":power.get("battery_percent"),
        "charging":bool(power.get("charging")),
        "thermal_state":"unknown",
        "browser_available":bool((modules.get("playwright") or {}).get("available")),
        "video_playback":bool((tools.get("ffmpeg") or {}).get("available") or (tools.get("ffprobe") or {}).get("available")),
        "screen_understanding":bool((modules.get("mss") or {}).get("available") or (modules.get("cv2") or {}).get("available")),
        "transcript_capable":bool((modules.get("faster_whisper") or {}).get("available") or (tools.get("yt-dlp") or {}).get("available")),
        "playwright_available":bool((modules.get("playwright") or {}).get("available")),
        "yt_dlp_available":bool((tools.get("yt-dlp") or {}).get("available")),
        "network_online":True,
    }
    return SuryadevDeviceSelector.classify(profile)


def probe():
    modules = {
        name: {"available": importlib.util.find_spec(name) is not None, "purpose": purpose}
        for name, purpose in OPTIONAL_MODULES.items()
    }
    tools = {
        name: {"available": bool(shutil.which(name)), "path": shutil.which(name), "purpose": purpose}
        for name, purpose in OPTIONAL_TOOLS.items()
    }
    profile=device_profile(modules,tools)
    return {
        "agent": AGENT,
        "version": VERSION,
        "modules": modules,
        "tools": tools,
        "device_profile": profile,
        "recommended_workload": profile.get("workload"),
        "max_browser_tabs": profile.get("max_browser_tabs"),
        "capabilities": {
            "screen_capture": modules["mss"]["available"],
            "camera_frames": modules["cv2"]["available"],
            "system_audio": modules["pyaudiowpatch"]["available"],
            "speech_to_text": modules["faster_whisper"]["available"],
            "scene_detection": modules["scenedetect"]["available"],
            "browser": modules["playwright"]["available"],
            "media_extract": tools["ffmpeg"]["available"],
        },
        "policy": {
            "raw_media_stays_local": True,
            "return_distilled_findings_only": True,
            "authentication_handoff": "owner_permission_required_per_checkpoint",
            "auth_permission_scope": "one_time_job_origin_method",
            "captcha_liveness": "owner-approved_human_handoff_only",
            "learning_cost": "zero",
            "paid_learning": False,
            "paid_api": False,
            "deep_learning_required": True,
            "researchable_output_required": True,
        },
    }


def auto_enroll(root):
    capability=probe()
    client=SuryadevDeviceClient(Path(root)/"device-client")
    result=client.auto_enroll(
        capability.get("device_profile") or {},
        label=f"SURYDEV {platform.system()} learning node",
    )
    return {
        "agent":AGENT,
        "version":VERSION,
        "device_profile":capability.get("device_profile"),
        "recommended_workload":capability.get("recommended_workload"),
        "enrollment":result,
        "policy":{
            "credential_printed":False,
            "serial_collected":False,
            "mac_address_collected":False,
            "paid_learning":False,
        },
    }


def _safe_job_id(value):
    value = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "-_")
    if not value:
        raise ValueError("job_id missing or invalid")
    return value


def _run_adapter(command, job_path, workspace, timeout=3600):
    command = str(command or "").strip()
    if not command:
        return None
    argv = [command, str(job_path), str(workspace)]
    proc = subprocess.run(argv, capture_output=True, text=True, shell=False, timeout=timeout)
    return {
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-12000:],
        "stderr": (proc.stderr or "")[-12000:],
    }


def process_job(job_path, root):
    job_path = Path(job_path).resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if job.get("schema") != "krishna.suryadev.job.v1":
        raise ValueError("unsupported SURYDEV job schema")
    job_id = _safe_job_id(job.get("job_id"))
    root = Path(root).resolve()
    work = root / "jobs" / job_id
    work.mkdir(parents=True, exist_ok=True)

    capability = probe()
    adapter = str(os.getenv("SURYADEV_JOB_ADAPTER") or "").strip()
    adapter_result = _run_adapter(adapter, job_path, work) if adapter else None

    status = "COMPLETED" if adapter_result and adapter_result.get("returncode") == 0 else "ADAPTER_REQUIRED"
    report = {
        "schema": "krishna.suryadev.worker-report.v1",
        "agent": AGENT,
        "version": VERSION,
        "job_id": job_id,
        "kind": job.get("kind"),
        "project": job.get("project"),
        "target": job.get("target"),
        "status": status,
        "capability_probe": capability,
        "adapter_result": adapter_result,
        "workspace": str(work),
        "created_at": time.time(),
        "raw_media_included": False,
        "next_action": (
            "Import distilled finding packet into KRISHNA"
            if status == "COMPLETED"
            else "Install/configure free sidecar capture-analysis adapter in this external workspace"
        ),
        "authentication_checkpoint_rule": (
            "On login/password/MFA/passkey/CAPTCHA/liveness: pause, emit an owner-permission request, "
            "and continue only after a one-time scoped approval is received. Human performs the authentication step."
        ),
    }
    out = work / "worker-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def watch(inbox, root, poll=2.0):
    inbox = Path(inbox).resolve()
    inbox.mkdir(parents=True, exist_ok=True)
    seen = set()
    while True:
        for path in sorted(inbox.glob("*.json")):
            if path.name in seen:
                continue
            try:
                report = process_job(path, root)
                print(json.dumps(report, ensure_ascii=False), flush=True)
            except Exception as exc:
                print(json.dumps({
                    "agent": AGENT,
                    "status": "FAILED",
                    "file": str(path),
                    "error": f"{type(exc).__name__}: {exc}",
                }, ensure_ascii=False), flush=True)
            seen.add(path.name)
        time.sleep(max(0.5, float(poll)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="KRISHNA SURYDEV external Eye+Ear worker")
    parser.add_argument("--root", default=str(Path.cwd() / "suryadev-workspace"))
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--auto-enroll", action="store_true",
                        help="Discover private KRISHNA Core, request/verify pairing, and auto-select a horse workload")
    parser.add_argument("--job")
    parser.add_argument("--watch")
    parser.add_argument("--poll", type=float, default=2.0)
    args = parser.parse_args(argv)

    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False, indent=2))
        return 0
    if args.auto_enroll:
        print(json.dumps(auto_enroll(args.root), ensure_ascii=False, indent=2))
        return 0
    if args.job:
        print(json.dumps(process_job(args.job, args.root), ensure_ascii=False, indent=2))
        return 0
    if args.watch:
        watch(args.watch, args.root, args.poll)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
