"""Bounded live YouTube speed sweep; source-clock evidence, not learning/mastery.

Run only with the normal SURYADEV worker/dashboard stopped. Uses the same OS
worker lock and 85% admission guard, a disposable local Chromium/Chrome
profile and one previously reviewed public test video. Does not download
media, seek, skip ads, retry prior lessons or create learning tasks.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import tempfile
import time

from suryadev_lock import worker_lock
from suryadev_resources import admission
from suryadev_video_browser_probe import (
    CHANNELS, TRIAL_VIDEO, observed_expected_video, validated_video,
)

RATES = (1.0, 1.5, 2.0, 3.0)


def speed_results(samples, *, rates=RATES):
    """Score only consecutive, non-ad, unpaused samples on the exact source."""
    results = []
    for rate in rates:
        matching = [
            x for x in samples
            if x.get("phase_rate") == rate and x.get("ad_showing") is False
            and x.get("paused") is False and x.get("has_video") is True
            and x.get("requested_video_page") is True
            and type(x.get("seconds")) in (int, float)
            and type(x.get("monotonic")) in (int, float)
            and type(x.get("playback_rate")) in (int, float)
            and math.isfinite(x["seconds"]) and math.isfinite(x["monotonic"])
        ]
        segments = []
        for previous, current in zip(matching, matching[1:]):
            wall = current["monotonic"] - previous["monotonic"]
            advance = current["seconds"] - previous["seconds"]
            if not (0.5 <= wall <= 5 and -0.1 <= advance <= 15):
                continue
            if abs(previous["playback_rate"]-rate) > .08 or abs(current["playback_rate"]-rate) > .08:
                continue
            segments.append((wall, max(0, advance)))
        measured_wall = sum(pair[0] for pair in segments)
        media_advance = sum(pair[1] for pair in segments)
        effective_rate = media_advance / measured_wall if measured_wall else 0.0
        observed_rate = (statistics.median(x["playback_rate"] for x in matching)
                         if matching else None)
        # Media time must actually advance near requested speed, not merely
        # report that the DOM property was set.
        passed = (measured_wall >= 6.0
                  and media_advance >= 6.0*rate*.68
                  and .68*rate <= effective_rate <= 1.35*rate
                  and observed_rate is not None
                  and abs(observed_rate-rate) <= .08)
        results.append({
            "requested_speed_x":rate,
            "actual_reported_playback_rate_x":round(observed_rate,3)
                if observed_rate is not None else None,
            "valid_content_wall_seconds":round(measured_wall,2),
            "source_video_advanced_seconds":round(media_advance,2),
            "effective_measured_speed_x":round(effective_rate,3),
            "pass":bool(passed),
            "sample_count":len(matching),
            "note":"Playback rate and source progression only; captions/audio mastery unverified",
        })
    return results


def classify_sweep(samples, *, rates=RATES):
    per_rate = speed_results(samples,rates=rates)
    errors = list(dict.fromkeys(x["media_error_code"] for x in samples
            if type(x.get("media_error_code")) is int and x["media_error_code"]>0))
    result={
        "requested_video_page_verified":observed_expected_video(samples),
        "advertisements_seen":sum(x.get("ad_showing") is True for x in samples),
        "browser_media_error_codes":errors,
        "speeds":per_rate,
        "all_speeds_verified":(
            observed_expected_video(samples)
            and not errors
            and all(x["pass"] for x in per_rate)),
        "learning_verified":False,
        "full_caption_or_audio_coverage_verified":False,
        "rishi_exam_verified":False,
    }
    return result


def run(root, *, url=TRIAL_VIDEO, channel="chrome",
        per_speed_seconds=16, sample_seconds=2, total_seconds=115):
    validated_video(url)
    if channel not in CHANNELS:
        raise ValueError("Choose a supported local channel: chrome, msedge, chromium")
    if not 12 <= per_speed_seconds <= 30:
        raise ValueError("per-speed seconds must be 12..30")
    if not 1 <= sample_seconds <= 3:
        raise ValueError("sample seconds must be 1..3")
    if not 65 <= total_seconds <= 180 or total_seconds < 4*per_speed_seconds+10:
        raise ValueError("total seconds must cover all four stages plus startup")
    root=Path(root).expanduser().resolve(strict=True)
    if not (root/"suryadev.sqlite3").is_file():
        raise ValueError("Existing SURYADEV evidence workspace is required")
    with worker_lock(root):
        safe,reason,telemetry=admission(root)
        if not safe:
            raise RuntimeError("85% hardware guard blocked speed test: "+reason)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Install free Playwright Python library; no browser download automatic") from exc
        started=time.time()
        started_mono=time.monotonic()
        diagnostics=[]
        samples=[]
        phase_index=0
        phase_started=None
        previous_play_requested=0.0
        aborted_reason=""
        try:
            with tempfile.TemporaryDirectory(prefix="suryadev-speed-check-") as profile:
                with sync_playwright() as playwright:
                    ctx=playwright.chromium.launch_persistent_context(
                        profile,channel=channel,headless=False,
                        args=["--autoplay-policy=no-user-gesture-required"],
                        viewport={"width":1280,"height":800})
                    try:
                        page=ctx.pages[0] if ctx.pages else ctx.new_page()
                        page.goto(url,wait_until="domcontentloaded",timeout=30000)
                        deadline=time.monotonic()+total_seconds
                        while time.monotonic()<deadline and phase_index<len(RATES):
                            now=time.monotonic()
                            try:
                                state=page.evaluate("""() => {
                                  const v=document.querySelector('video');
                                  const q=v && v.getVideoPlaybackQuality ?
                                    v.getVideoPlaybackQuality() : null;
                                  return { source_url:location.href,has_video:!!v,
                                    seconds:v?Number(v.currentTime)||0:0,
                                    playback_rate:v?Number(v.playbackRate)||0:0,
                                    paused:v?!!v.paused:true,
                                    ended:v?!!v.ended:false,
                                    ready_state:v?v.readyState:null,
                                    network_state:v?v.networkState:null,
                                    media_error_code:v&&v.error?v.error.code:null,
                                    dropped_frames:q?q.droppedVideoFrames:null,
                                    total_frames:q?q.totalVideoFrames:null,
                                    ad_showing:!!document.querySelector(
                                      '.html5-video-player.ad-showing') };
                                }""")
                                state["requested_video_page"]=observed_expected_video([state])
                                state["monotonic"]=now
                                state["elapsed_wall_seconds"]=round(now-started_mono,2)
                                state["phase_rate"]=RATES[phase_index]
                                samples.append(state)
                                if state.get("media_error_code"):
                                    aborted_reason="HTML media error "+str(state["media_error_code"])
                                    break
                                if not state["requested_video_page"]:
                                    time.sleep(sample_seconds)
                                    continue
                                if state["ad_showing"] or not state["has_video"]:
                                    # Do not change provider advertisements or
                                    # count advertisement clocks as video content.
                                    time.sleep(sample_seconds)
                                    continue
                                if phase_started is None:
                                    safe,reason,_=admission(root)
                                    if not safe:
                                        aborted_reason="Hardware guard: "+reason
                                        break
                                    phase_started=time.monotonic()
                                    page.evaluate("(rate)=>{ const v=document.querySelector('video'); if(v) v.playbackRate=rate; }",
                                                  RATES[phase_index])
                                if state.get("paused") and now-previous_play_requested>=8:
                                    page.evaluate("""() => {
                                        const v=document.querySelector('video');
                                        if(v) v.play().catch(()=>{});
                                    }""")
                                    previous_play_requested=now
                                if time.monotonic()-phase_started>=per_speed_seconds:
                                    phase_index+=1
                                    phase_started=None
                            except Exception as exc:
                                diagnostics.append(type(exc).__name__+": "+str(exc)[:160])
                                if len(diagnostics)>=5:
                                    aborted_reason="Repeated browser evaluation errors"
                                    break
                            time.sleep(sample_seconds)
                    finally:
                        ctx.close()
        except Exception as exc:
            aborted_reason=aborted_reason or (type(exc).__name__+": "+str(exc)[:180])
        verdict=classify_sweep(samples)
        if aborted_reason:
            verdict["all_speeds_verified"]=False
        verdict["aborted_reason"]=aborted_reason
        report={
            "schema":"suryadev.video-speed-sweep.v1",
            "video_url":url,"browser_channel":channel,
            "started_at":started,"finished_at":time.time(),
            "cpu_percent_at_start":telemetry.get("cpu_percent"),
            "ram_percent_at_start":telemetry.get("ram_percent"),
            "evidence_only":True,"source_approvals_modified":False,
            "history_modified":False,"speed_results":verdict,
            "diagnostics":diagnostics,"samples":samples,
        }
        out=root/"benchmark-reports"
        out.mkdir(exist_ok=True)
        dest=out/("video-speed-sweep-"+channel+"-"+time.strftime(
            "%Y%m%d-%H%M%S",time.localtime(started))+".json")
        if dest.exists():
            raise FileExistsError("Do not overwrite an existing speed audit report")
        dest.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",
                        encoding="utf-8")
        return dest,report


def main(argv=None):
    p=argparse.ArgumentParser(description="One public video: 1x, 1.5x, 2x, 3x actual playback test")
    p.add_argument("--data",required=True,type=Path)
    p.add_argument("--video",default=TRIAL_VIDEO)
    p.add_argument("--channel",choices=sorted(CHANNELS),default="chrome")
    p.add_argument("--per-speed-seconds",type=int,default=16)
    p.add_argument("--seconds",type=int,default=115)
    args=p.parse_args(argv)
    try:
        path,report=run(args.data,url=args.video,channel=args.channel,
                        per_speed_seconds=args.per_speed_seconds,
                        total_seconds=args.seconds)
    except (ValueError,OSError,RuntimeError) as exc:
        print("SPEED TEST BLOCKED: "+type(exc).__name__+": "+str(exc))
        return 2
    result=report["speed_results"]
    print(json.dumps({"report":str(path),
                      "all_speeds_verified":result["all_speeds_verified"],
                      "aborted_reason":result["aborted_reason"],
                      "speeds":result["speeds"],
                      "media_errors":result["browser_media_error_codes"]},
                     indent=2))
    return 0 if result["all_speeds_verified"] else 3


if __name__=="__main__":
    raise SystemExit(main())
