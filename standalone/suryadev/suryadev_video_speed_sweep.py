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
from suryadev_browser_engine import require_garudanetra, browser_identity
from suryadev_video_browser_probe import (
    CHANNELS, TRIAL_VIDEO, observed_expected_video, validated_video,
)

RATES = (1.0, 1.5, 2.0, 3.0)


def detect_media_unload(samples):
    """Find first loss of a previously ready/advancing source, without guessing why.

    A browser accepting the requested playbackRate on an empty media element
    is not evidence of high-speed playback. The player may have navigated,
    reloaded, replaced its HTMLVideoElement or unloaded its media source.
    """
    last_ready = None
    for sample in samples:
        if not isinstance(sample, dict) or sample.get("ad_showing") is True:
            continue
        if not sample.get("requested_video_page"):
            continue
        sec = sample.get("seconds")
        ready = sample.get("ready_state")
        network = sample.get("network_state")
        if (type(sec) in (int,float) and math.isfinite(sec) and sec >= 0
                and type(ready) is int and type(network) is int):
            if (last_ready is not None and sec <= 0.1 and ready == 0
                    and network == 0 and sample.get("ended") is not True):
                return {
                    "event": "media_unloaded_after_playback",
                    "phase_rate": sample.get("phase_rate"),
                    "wall_seconds": sample.get("elapsed_wall_seconds"),
                    "previous_source_seconds": last_ready.get("seconds"),
                    "last_ready_state": last_ready.get("ready_state"),
                    "last_network_state": last_ready.get("network_state"),
                    "video_element_replaced": (
                        last_ready.get("element_generation") !=
                        sample.get("element_generation")
                        if (last_ready.get("element_generation") is not None
                            and sample.get("element_generation") is not None)
                        else None),
                    "new_element_attached": sample.get("element_attached"),
                    "new_element_has_current_src": sample.get("current_src_present"),
                }
            if sec >= 2.0 and ready >= 2 and network in (1,2):
                last_ready = sample
    return None


def speed_results(samples, *, rates=RATES):
    """Score only consecutive, non-ad, unpaused samples on the exact source."""
    results = []
    for rate in rates:
        matching = [
            x for x in samples
            if x.get("phase_rate") == rate and x.get("ad_showing") is False
            and x.get("paused") is False and x.get("has_video") is True
            and x.get("requested_video_page") is True
            and type(x.get("ready_state")) is int and x["ready_state"] >= 2
            and x.get("network_state") in (1, 2)
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
        frame_samples = [x for x in matching if
            type(x.get("dropped_frames")) in (int,float) and
            type(x.get("total_frames")) in (int,float)]
        dropped = max(0,frame_samples[-1]["dropped_frames"]-
                      frame_samples[0]["dropped_frames"]) if len(frame_samples)>=2 else None
        total_frames = max(0,frame_samples[-1]["total_frames"]-
                           frame_samples[0]["total_frames"]) if len(frame_samples)>=2 else None
        drop_pct = (round(100*dropped/total_frames,2)
                    if dropped is not None and total_frames else None)
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
            "video_frames_counted":total_frames,
            "video_frames_dropped":dropped,
            "video_frame_drop_percent":drop_pct,
            "frame_drop_warning":drop_pct is not None and drop_pct >= 5,
            "note":"Playback rate and source progression only; captions/audio mastery unverified",
        })
    return results


def classify_sweep(samples, *, rates=RATES):
    per_rate = speed_results(samples,rates=rates)
    unloaded = detect_media_unload(samples)
    errors = list(dict.fromkeys(x["media_error_code"] for x in samples
            if type(x.get("media_error_code")) is int and x["media_error_code"]>0))
    result={
        "requested_video_page_verified":observed_expected_video(samples),
        "advertisements_seen":sum(x.get("ad_showing") is True for x in samples),
        "browser_media_error_codes":errors,
        "media_unload_event":unloaded,
        "speeds":per_rate,
        "all_speeds_verified":(
            observed_expected_video(samples)
            and not errors
            and unloaded is None
            and all(x["pass"] for x in per_rate)),
        "learning_verified":False,
        "full_caption_or_audio_coverage_verified":False,
        "rishi_exam_verified":False,
    }
    return result


def run(root, *, url=TRIAL_VIDEO, channel="chromium",
        per_speed_seconds=16, sample_seconds=2, total_seconds=115,
        rates=RATES):
    validated_video(url)
    rates = tuple(rates)
    if not rates or len(set(rates)) != len(rates) or any(x not in RATES for x in rates):
        raise ValueError("Only unique speeds from 1x, 1.5x, 2x, 3x are allowed")
    require_garudanetra(channel)
    if not 12 <= per_speed_seconds <= 30:
        raise ValueError("per-speed seconds must be 12..30")
    if not 1 <= sample_seconds <= 3:
        raise ValueError("sample seconds must be 1..3")
    if (not 25 <= total_seconds <= 180
            or total_seconds < len(rates)*per_speed_seconds+10):
        raise ValueError("total seconds must cover selected stages plus startup")
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
        navigation_events=[]
        samples=[]
        hardware_checks=[]
        phase_index=0
        phase_started=None
        previous_play_requested=0.0
        aborted_reason=""
        try:
            with tempfile.TemporaryDirectory(prefix="suryadev-speed-check-") as profile:
                with sync_playwright() as playwright:
                    ctx=playwright.chromium.launch_persistent_context(
                        profile,channel=channel,headless=True,
                        args=["--autoplay-policy=no-user-gesture-required"],
                        viewport={"width":1280,"height":800})
                    try:
                        page=ctx.pages[0] if ctx.pages else ctx.new_page()
                        # Record top-level navigations without storing personal
                        # query strings or signed media URLs in the report.
                        page.on("framenavigated",lambda frame: (
                            navigation_events.append({
                                "wall_seconds":round(time.monotonic()-started_mono,2),
                                "main_frame_navigation":True})
                            if frame == page.main_frame else None))
                        page.goto(url,wait_until="domcontentloaded",timeout=30000)
                        deadline=time.monotonic()+total_seconds
                        while time.monotonic()<deadline and phase_index<len(rates):
                            now=time.monotonic()
                            try:
                                state=page.evaluate("""() => {
                                  const v=document.querySelector('video');
                                  const probe=(window.__suryadevSpeedProbe ||= {
                                    generation:0, lastElement:null});
                                  if (v !== probe.lastElement) {
                                    probe.lastElement=v;
                                    probe.generation++;
                                  }
                                  const q=v && v.getVideoPlaybackQuality ?
                                    v.getVideoPlaybackQuality() : null;
                                  return { source_url:location.href,has_video:!!v,
                                    element_generation:probe.generation,
                                    element_attached:v?!!v.isConnected:false,
                                    current_src_present:v?!!v.currentSrc:false,
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
                                state["phase_rate"]=rates[phase_index]
                                samples.append(state)
                                unload_event=detect_media_unload(samples[-120:])
                                if unload_event is not None:
                                    aborted_reason="media_unloaded_after_playback"
                                    diagnostics.append(unload_event)
                                    break
                                if state.get("media_error_code"):
                                    aborted_reason="HTML media error "+str(state["media_error_code"])
                                    break
                                if not state["requested_video_page"]:
                                    time.sleep(sample_seconds)
                                    continue
                                if state["ad_showing"] or not state["has_video"] or (
                                        state.get("ready_state",0) < 2 or
                                        state.get("network_state",0) == 0):
                                    # Never change speed on an empty/unloaded
                                    # video element, nor count advertisement time.
                                    time.sleep(sample_seconds)
                                    continue
                                if phase_started is None:
                                    safe,reason,phase_hardware=admission(root)
                                    hardware_checks.append({
                                        "requested_speed_x":rates[phase_index],
                                        "safe":safe,"reason":reason,
                                        "cpu_percent":phase_hardware.get("cpu_percent"),
                                        "ram_percent":phase_hardware.get("ram_percent"),
                                        "sample_time":time.time()})
                                    if not safe:
                                        aborted_reason="Hardware guard: "+reason
                                        break
                                    phase_started=time.monotonic()
                                    page.evaluate("(rate)=>{ const v=document.querySelector('video'); if(v) v.playbackRate=rate; }",
                                                  rates[phase_index])
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
        verdict=classify_sweep(samples,rates=rates)
        if aborted_reason:
            verdict["all_speeds_verified"]=False
        if aborted_reason=="media_unloaded_after_playback":
            failed_rate=detect_media_unload(samples).get("phase_rate")
            reached=False
            for rate_result in verdict["speeds"]:
                if rate_result["requested_speed_x"]==failed_rate:
                    reached=True
                    rate_result["test_status"]="interrupted_by_media_unload"
                elif reached:
                    rate_result["test_status"]="not_tested_after_media_unload"
                else:
                    rate_result["test_status"]=(
                        "verified" if rate_result["pass"] else "insufficient_samples")
        else:
            for rate_result in verdict["speeds"]:
                rate_result["test_status"]=(
                    "verified" if rate_result["pass"] else "insufficient_or_stalled")
        verdict["aborted_reason"]=aborted_reason
        report={
            "schema":"suryadev.video-speed-sweep.v1",
            "video_url":url,"browser_channel":channel,
            "browser_identity":browser_identity(),
            "started_at":started,"finished_at":time.time(),
            "cpu_percent_at_start":telemetry.get("cpu_percent"),
            "ram_percent_at_start":telemetry.get("ram_percent"),
            "evidence_only":True,"source_approvals_modified":False,
            "history_modified":False,"speed_results":verdict,
            "diagnostics":diagnostics,"main_frame_navigation_events":navigation_events[:40],
            "hardware_admission_checks":hardware_checks,"samples":samples,
        }
        out=root/"benchmark-reports"
        out.mkdir(exist_ok=True)
        # Single-speed diagnostics are *not* admitted by the separate
        # learning-speed ceiling parser, which requires a full 4-rate sweep.
        prefix=("video-speed-sweep-"+channel+"-" if rates==RATES else
                "video-speed-probe-"+channel+"-"+
                "-".join(str(x).replace(".","p")+"x" for x in rates)+"-")
        dest=out/(prefix+time.strftime(
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
    p.add_argument("--channel",choices=sorted(CHANNELS),default="chromium")
    p.add_argument("--per-speed-seconds",type=int,default=16)
    p.add_argument("--seconds",type=int,default=115)
    p.add_argument("--rate",type=float,choices=RATES,default=None,
                   help="One isolated speed only; does not change the learning cap")
    args=p.parse_args(argv)
    try:
        path,report=run(args.data,url=args.video,channel=args.channel,
                        per_speed_seconds=args.per_speed_seconds,
                        total_seconds=args.seconds,
                        rates=(args.rate,) if args.rate else RATES)
    except (ValueError,OSError,RuntimeError) as exc:
        print("SPEED TEST BLOCKED: "+type(exc).__name__+": "+str(exc))
        return 2
    result=report["speed_results"]
    print(json.dumps({"report":str(path),
                      "all_speeds_verified":result["all_speeds_verified"],
                      "aborted_reason":result["aborted_reason"],
                      "media_unload_event":result["media_unload_event"],
                      "speeds":result["speeds"],
                      "media_errors":result["browser_media_error_codes"]},
                     indent=2))
    return 0 if result["all_speeds_verified"] else 3


if __name__=="__main__":
    raise SystemExit(main())
