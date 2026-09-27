from __future__ import annotations

"""Non-secret capability profiling and automatic SURYDEV horse workload selection."""

import math


class SuryadevDeviceSelector:
    VERSION="suryadev-device-selector-v1"
    WORKLOADS={"media_learning","web_research","hybrid","standby"}

    @staticmethod
    def _num(value,default=0.0):
        try:return float(value)
        except (TypeError,ValueError):return float(default)

    @classmethod
    def normalize(cls,profile):
        p=dict(profile or {})
        device_class=str(p.get("device_class") or "unknown").strip().lower()
        platform=str(p.get("platform") or "unknown").strip().lower()
        memory_mb=max(0,int(cls._num(p.get("memory_mb"))))
        cpu_cores=max(0,int(cls._num(p.get("cpu_cores"))))
        free_storage_gb=max(0.0,cls._num(p.get("free_storage_gb")))
        battery=cls._num(p.get("battery_percent"),-1)
        thermal=str(p.get("thermal_state") or "unknown").strip().lower()
        return {
            "schema":"krishna.suryadev.device-profile.v1",
            "platform":platform,
            "platform_version":str(p.get("platform_version") or "")[:120],
            "device_class":device_class,
            "model_family":str(p.get("model_family") or "")[:160],
            "memory_mb":memory_mb,
            "cpu_cores":cpu_cores,
            "free_storage_gb":round(free_storage_gb,2),
            "battery_percent":battery if 0<=battery<=100 else None,
            "charging":bool(p.get("charging",False)),
            "thermal_state":thermal,
            "browser_available":bool(p.get("browser_available",False)),
            "video_playback":bool(p.get("video_playback",False)),
            "screen_understanding":bool(p.get("screen_understanding",False)),
            "transcript_capable":bool(p.get("transcript_capable",False)),
            "playwright_available":bool(p.get("playwright_available",False)),
            "yt_dlp_available":bool(p.get("yt_dlp_available",False)),
            "network_online":bool(p.get("network_online",True)),
            "privacy":{
                "serial_collected":False,
                "mac_address_collected":False,
                "credential_collected":False,
            },
        }

    @classmethod
    def classify(cls,profile):
        p=cls.normalize(profile)
        reasons=[]
        if not p["network_online"]:
            return {**p,"workload":"standby","score":0,"reasons":["network offline"],"max_browser_tabs":0}
        thermal=p["thermal_state"]
        battery=p["battery_percent"]
        constrained=thermal in {"serious","critical"} or (battery is not None and battery<=15 and not p["charging"])
        if constrained:
            return {**p,"workload":"standby","score":0,"reasons":["device health requires standby"],"max_browser_tabs":0}

        media_score=0
        research_score=0
        if p["video_playback"]:media_score+=3
        if p["screen_understanding"]:media_score+=2
        if p["transcript_capable"]:media_score+=2
        if p["browser_available"]:media_score+=1
        if p["device_class"] in {"ipad","tablet","mobile","phone"}:media_score+=2

        if p["browser_available"]:research_score+=2
        if p["playwright_available"]:research_score+=4
        if p["yt_dlp_available"]:research_score+=1
        if p["memory_mb"]>=8192:research_score+=3
        elif p["memory_mb"]>=4096:research_score+=1
        if p["cpu_cores"]>=4:research_score+=2
        if p["free_storage_gb"]>=10:research_score+=1
        if p["device_class"] in {"laptop","desktop","pc","macbook"}:research_score+=2

        max_tabs=0
        if research_score>=5:
            # Conservative RAM-aware tab budget.  Browser pages are not assumed cheap.
            max_tabs=min(10,max(2,int(p["memory_mb"]//1536))) if p["memory_mb"] else 2

        if media_score>=5 and research_score>=7 and p["memory_mb"]>=8192:
            workload="hybrid";reasons.append("strong media and browser-research capability")
        elif research_score>=7:
            workload="web_research";reasons.append("browser/RAM/CPU profile suits parallel research")
        elif media_score>=4:
            workload="media_learning";reasons.append("device suits low-load screen/video learning")
        elif research_score>=4:
            workload="web_research";reasons.append("limited but usable research capability")
        else:
            workload="standby";reasons.append("insufficient verified capability")

        return {
            **p,
            "workload":workload,
            "score":{"media":media_score,"research":research_score},
            "max_browser_tabs":max_tabs,
            "youtube_lanes":1 if workload in {"media_learning","hybrid"} else 0,
            "policy":{
                "paid_learning":False,
                "paid_api":False,
                "paid_search":False,
                "raw_media_upload":False,
                "deep_learning_required":True,
                "researchable_output_required":True,
                "lab_handoff_requires_rishi_question":True,
                "free_only":"local tools + public web + approved zero-cost providers only",
            },
            "reasons":reasons,
        }

    @classmethod
    def choose_horse(cls,profiles,bindings,device_profile):
        classified=cls.classify(device_profile)
        bindings=dict(bindings or {})
        preferred={
            "ipad":"gayatri","tablet":"gayatri",
            "macbook":"brihati",
            "mobile":"jagati","phone":"jagati",
        }.get(classified["device_class"])
        if preferred and not bindings.get(preferred):
            return preferred,classified
        for row in profiles:
            hid=str(row.get("id") or "")
            if hid and not bindings.get(hid):
                return hid,classified
        return None,classified
