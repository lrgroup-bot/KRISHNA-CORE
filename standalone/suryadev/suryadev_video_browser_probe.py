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
from suryadev_browser_engine import require_garudanetra, browser_identity

TRIAL_VIDEO = "https://www.youtube.com/watch?v=VZ5LU8vHT0s"
CHANNELS = {"chromium"}


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


def observed_expected_video(samples):
    for sample in samples:
        if not isinstance(sample,dict) or sample.get("has_video") is not True:
            continue
        try:
            p=urlsplit(str(sample.get("source_url") or ""))
            if (p.scheme=="https" and p.hostname in ("www.youtube.com","youtube.com")
                    and p.path=="/watch" and parse_qs(p.query).get("v")==["VZ5LU8vHT0s"]):
                return True
        except ValueError:
            pass
    return False


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
    return {"requested_video_page_verified":observed_expected_video(samples),
            "source_video_progress_seconds":round(max(0,advance),2),
            "source_video_position_seconds":round(max(valid),2) if valid else None,
            "content_clock_advanced_30s":advance >= 30,
            "content_clock_advanced_10s":advance >= 10,
            "media_error_codes":list(dict.fromkeys(errors)),
            "advertisement_seen":any_ad,
            "sample_count":len(samples),
            "learning_verified":False,
            "caption_coverage_verified":False,
            "rishi_exam_verified":False}


def can_approve_after_probe(assessment):
    return (assessment.get("requested_video_page_verified") is True
            and assessment.get("content_clock_advanced_30s") is True
            and not assessment.get("media_error_codes"))


def execute(root, *, url, channel="chromium", sample_seconds=2, observation_seconds=50,
            approve_after_passing=False):
    from playwright.sync_api import sync_playwright
    url=validated_video(url)
    require_garudanetra(channel)
    if not 25 <= observation_seconds <= 90:
        raise ValueError("Playback diagnostic must be 25..90 seconds")
    if not 1 <= sample_seconds <= 5:
        raise ValueError("Sampling must be 1..5 seconds")
    root=Path(root).expanduser().resolve(strict=True)
    if not (root/"suryadev.sqlite3").is_file():
        raise ValueError("Existing SURYADEV workspace is required")
    if __import__("os").getenv("SURYADEV_UBOL_EXTENSION_DIR"):
        raise ValueError("The diagnostic uses a clean GARUDANETRA profile; disable extension injection for this test")
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
                    profile,channel=channel,headless=True,
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
                "browser_identity":browser_identity(),
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
        result["new_source_approved_for_learning"] = False
        if approve_after_passing and can_approve_after_probe(result["assessment"]):
            # A separate, explicit operator opt-in can approve this exact
            # fresh URL only AFTER 30s of genuine non-ad clock advancement.
            # The original 3 failed video jobs remain completely untouched.
            from suryadev_video_review import VideoReview
            review=VideoReview(root,Path(__file__).resolve().parent)
            approval=review.approve_source(url)
            result["new_source_approved_for_learning"] = True
            result["source_approval_status"] = approval.get("status")
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
    p.add_argument("--channel",choices=sorted(CHANNELS),default="chromium")
    p.add_argument("--seconds",type=int,default=50)
    p.add_argument("--approve-after-passing",action="store_true",
                   help="Explicitly allow this one video after 30s genuine non-ad playback")
    args=p.parse_args(argv)
    try:
        path,report=execute(args.data,url=args.video,channel=args.channel,
                            observation_seconds=args.seconds,
                            approve_after_passing=args.approve_after_passing)
        print(json.dumps({"report":str(path),"assessment":report["assessment"],
                          "new_source_approved_for_learning":
                              report["new_source_approved_for_learning"],
                          "diagnostics":report["diagnostics"]},indent=2))
        return 0 if can_approve_after_probe(report["assessment"]) else 3
    except (OSError,ValueError,RuntimeError) as exc:
        print("PROBE BLOCKED: "+type(exc).__name__+": "+str(exc))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
