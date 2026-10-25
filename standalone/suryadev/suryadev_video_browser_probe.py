"""Opt-in, worker-lock-safe YouTube media playback diagnostic (no learning claim).

This opens one reviewed public URL in an isolated local Playwright profile,
records HTMLVideoElement metadata only, and never downloads video, skips ads,
copies credentials, creates source approvals, or changes the learning ledger.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

from suryadev_lock import worker_lock
from suryadev_resources import admission

TRIAL_VIDEO = "https://www.youtube.com/watch?v=VZ5LU8vHT0s"
CHANNELS = {"chrome", "msedge", "chromium"}


def validated_video(url):
    parts=urlsplit(str(url))
    if (parts.scheme != "https" or parts.hostname not in
            ("www.youtube.com", "youtube.com") or parts.path != "/watch"
            or parts.username or parts.password or parts.fragment
            or parts.port not in (None,443)):
        raise ValueError("Only exact public HTTPS YouTube watch URLs are supported")
    args=parse_qs(parts.query,strict_parsing=True)
    if set(args)!={"v"} or len(args["v"])!=1 or len(args["v"][0])!=11:
        raise ValueError("Use an exact YouTube video ID without extra query parameters")
    if url != TRIAL_VIDEO:
        raise ValueError("Only the operator-reviewed SURYADEV trial video is permitted")
    return url


def classify(samples):
    """Only non-ad content timestamps count; playback is not comprehension."""
    valid=[float(x["seconds"]) for x in samples if
           x.get("ad_showing") is False
           and x.get("has_video") is True
           and type(x.get("seconds")) in (int,float)
           and x["seconds"] >= 0]
    initial=valid[0] if valid else None
    advance=max(valid)-initial if valid else 0
    errors=[x.get("media_error_code") for x in samples if x.get("media_error_code")]
    any_ad=any(x.get("ad_showing") is True for x in samples)
    return {"source_video_progress_seconds":round(max(0,advance),2),
            "source_video_position_seconds":round(max(valid),2) if valid else None,
            "content_clock_advanced_30s":advance >= 30,
            "content_clock_advanced_10s":advance >= 10,
            "media_error_codes":list(dict.fromkeys(errors)),
            "advertisement_seen":any_ad,
            "sample_count":len(samples),
            "learning_verified":False,
            "caption_coverage_verified":False,
            "rishi_exam_verified":False}


def execute(root, *, url, channel="chrome", sample_seconds=2, observation_seconds=50):
    from playwright.sync_api import sync_playwright
    url=validated_video(url)
    if channel not in CHANNELS:
        raise ValueError("Use an installed Playwright browser channel: chrome, msedge, chromium")
    if not 25 <= observation_seconds <= 90:
        raise ValueError("Playback diagnostic must be 25..90 seconds")
    if not 1 <= sample_seconds <= 5:
        raise ValueError("Sampling must be 1..5 seconds")
    root=Path(root).expanduser().resolve(strict=True)
    if not (root/"suryadev.sqlite3").is_file():
        raise ValueError("Existing SURYADEV workspace is required")
    if (channel in ("chrome","msedge") and
        __import__("os").getenv("SURYADEV_UBOL_EXTENSION_DIR")):
        raise ValueError("Branded Chrome/Edge playback check cannot use unpacked uBO Lite")
    with worker_lock(root):
        safe,reason,telemetry=admission(root)
        if not safe:
            raise RuntimeError("85% hardware admission blocked browser probe: "+reason)
        started=time.time()
        samples=[]
        diagnostics=[]
        with tempfile.TemporaryDirectory(prefix="suryadev-video-probe-") as profile:
            with sync_playwright() as p:
                context=p.chromium.launch_persistent_context(
                    profile,channel=channel,headless=False,
                    args=["--autoplay-policy=no-user-gesture-required"],
                    viewport={"width":1280,"height":800})
                try:
                    page=context.pages[0] if context.pages else context.new_page()
                    try:
                        page.goto(url,wait_until="domcontentloaded",timeout=30000)
                    except Exception as exc:
                        diagnostics.append("navigation: "+type(exc).__name__+
                                           ": "+str(exc)[:150])
                    deadline=time.monotonic()+observation_seconds
                    last_try=0.0
                    while time.monotonic()<deadline:
                        try:
                            sample=page.evaluate("""() => {
                              const v=document.querySelector('video');
                              return {
                                seconds:v?Number(v.currentTime)||0:0,
                                duration:v&&Number.isFinite(v.duration)?Number(v.duration):null,
                                has_video:!!v,
                                paused:v?!!v.paused:true,
                                ready_state:v?v.readyState:null,
                                network_state:v?v.networkState:null,
                                media_error_code:v&&v.error?v.error.code:null,
                                ad_showing:!!document.querySelector(
                                    '.html5-video-player.ad-showing'),
                                source_url:location.href
                              };
                            }""")
                            sample["elapsed_wall_seconds"]=round(time.time()-started,2)
                            samples.append(sample)
                            if (sample["paused"] and sample["has_video"]
                                and not sample["ad_showing"]
                                and time.monotonic()-last_try>8):
                                # Normal browser play request, never seek/skip ad.
                                page.evaluate("""() => {
                                  const v=document.querySelector('video');
                                  if (v) v.play().catch(() => {});
                                }""")
                                last_try=time.monotonic()
                        except Exception as exc:
                            diagnostics.append("sample: "+type(exc).__name__+
                                               ": "+str(exc)[:150])
                        time.sleep(sample_seconds)
                finally:
                    context.close()
        result={"schema":"suryadev.video-browser-probe.v1",
                "video_url":url, "channel":channel,
                "started_at":started,"ended_at":time.time(),
                "hardware_safe_at_start":True,
                "cpu_percent_at_start":telemetry.get("cpu_percent"),
                "ram_percent_at_start":telemetry.get("ram_percent"),
                "assessment":classify(samples),
                "diagnostics":diagnostics[:15],
                "samples":samples,
                "previous_video_history_modified":False,
                "source_approval_modified":False,
                "real_lecture_comprehension_verified":False}
        folder=root/"benchmark-reports"
        folder.mkdir(exist_ok=True)
        path=folder/("video-browser-probe-"+channel+"-"+time.strftime(
                    "%Y%m%d-%H%M%S",time.localtime(started))+".json")
        if path.exists():
            raise FileExistsError("Existing probe report cannot be overwritten")
        path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",
                        encoding="utf-8")
        return path,result


def main(argv=None):
    p=argparse.ArgumentParser(description="One-video local browser codec/playback evidence probe")
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--video",required=True)
    p.add_argument("--channel",choices=sorted(CHANNELS),default="chrome")
    p.add_argument("--seconds",type=int,default=50)
    args=p.parse_args(argv)
    try:
        path,report=execute(args.data,url=args.video,channel=args.channel,
                            observation_seconds=args.seconds)
        print(json.dumps({"report":str(path),"assessment":report["assessment"],
                          "diagnostics":report["diagnostics"]},indent=2))
        return 0 if report["assessment"]["content_clock_advanced_30s"] else 3
    except (OSError,ValueError,RuntimeError) as exc:
        print("PROBE BLOCKED: "+type(exc).__name__+": "+str(exc))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
