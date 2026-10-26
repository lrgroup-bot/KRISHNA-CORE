"""Offline GARUDANETRA open-source Chromium preflight. No source downloads.

Run with the supervisor worker stopped. Does not test YouTube or create
source approvals, lessons, signatures, account sessions or persisted cookies.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from suryadev_browser_engine import browser_channel, browser_identity
from suryadev_lock import worker_lock
from suryadev_resources import admission


CODEC_PROBE_JS = r"""() => {
  const el = document.createElement('video');
  return {
    html_video: typeof HTMLVideoElement !== 'undefined',
    h264_aac: el.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"'),
    vp9_opus: el.canPlayType('video/webm; codecs="vp9, opus"'),
    vp8_vorbis: el.canPlayType('video/webm; codecs="vp8, vorbis"')
  };
}"""


def check(root, *, browser_factory=None):
    root=Path(root).expanduser().resolve(strict=True)
    if not (root/"suryadev.sqlite3").is_file():
        raise ValueError("Use the existing SURYADEV data folder, not a new one")
    with worker_lock(root):
        safe,reason,telemetry=admission(root)
        if not safe:
            raise RuntimeError("GARUDANETRA hardware admission: "+str(reason))
        if browser_factory is not None:
            return _probe(browser_factory, telemetry)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright missing. Install the package explicitly; "
                "no software was installed automatically") from exc
        with sync_playwright() as p:
            return _probe(p.chromium, telemetry)


def _probe(chromium, telemetry):
    try:
        browser=chromium.launch(channel=browser_channel(),headless=True)
    except Exception as exc:
        raise RuntimeError(
            "GARUDANETRA Chromium unavailable. Check the local browser binary "
            "with: python -m playwright install chromium. Original error: "+
            type(exc).__name__+": "+str(exc)[:220]) from exc
    try:
        page=browser.new_page()
        # Internal source-free HTML only. No YouTube or other websites opened.
        page.goto("data:text/html,<title>GARUDANETRA local preflight</title>")
        codecs=page.evaluate(CODEC_PROBE_JS)
        return {
            "schema":"suryadev.garudanetra-browser-preflight.v1",
            "identity":browser_identity(),
            "browser_version":browser.version,
            "local_engine_started":True,
            "codec_can_play_type":codecs,
            "codec_support_is_declaration_not_live_video":True,
            "source_requests":0,
            "media_playback_verified":False,
            "caption_coverage_verified":False,
            "learning_verified":False,
            "cpu_percent_at_start":telemetry.get("cpu_percent"),
            "ram_percent_at_start":telemetry.get("ram_percent"),
        }
    finally:
        browser.close()


def main(argv=None):
    ap=argparse.ArgumentParser(description="Offline owned GARUDANETRA browser and codec test")
    ap.add_argument("--data",required=True,type=Path)
    args=ap.parse_args(argv)
    try:
        result=check(args.data)
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    except (OSError,RuntimeError,ValueError) as exc:
        print("GARUDANETRA PREFLIGHT BLOCKED: "+type(exc).__name__+": "+str(exc))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
