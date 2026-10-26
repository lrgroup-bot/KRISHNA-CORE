#!/usr/bin/env python3
from __future__ import annotations

"""Low-load SURYDEV video learning adapter.

The adapter watches one browser video lane, reads visible captions/timestamps, keeps a
temporary timestamped transcript, selects bounded visual evidence, and emits
learning-bundle.json for the existing BRAHMA/Rishi path.

It intentionally does not download or persist the source video. The transcript and
selected frames are transient external-node evidence and are deleted by
suryadev_worker.py only after a matching server acknowledgement.
"""

import hashlib
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time
import wave
from urllib.parse import urlparse


BUNDLE_SCHEMA = "krishna.suryadev.learning-bundle.v1"


def _safe_name(value, limit=70):
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("._-")
    return (text or "subject")[:limit]


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _clock(seconds):
    seconds = max(0, int(float(seconds or 0)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}h{m:02d}m{s:02d}s"


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _is_http_url(value):
    try:
        u = urlparse(str(value or ""))
        return u.scheme in {"http", "https"} and bool(u.netloc)
    except Exception:
        return False


class _SystemAudioASR:
    """Bounded Windows loopback-ASR fallback used only when browser captions are absent."""

    def __init__(self, workspace, *, chunk_seconds=60):
        self.workspace = Path(workspace).resolve()
        self.audio_dir = self.workspace / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_seconds = max(20, min(int(chunk_seconds), 180))
        self.stop_event = threading.Event()
        self.queue = queue.Queue(maxsize=10)
        self.entries = []
        self.error = ""
        self.dropped_or_stopped_for_backlog = False
        self._threads = []
        self._started_at = time.monotonic()

    @staticmethod
    def available():
        try:
            import pyaudiowpatch  # noqa:F401
            import faster_whisper  # noqa:F401
            return sys.platform.startswith("win")
        except Exception:
            return False

    @staticmethod
    def _loopback_device(p, pyaudio):
        host = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        speakers = p.get_device_info_by_index(host["defaultOutputDevice"])
        if speakers.get("isLoopbackDevice"):
            return speakers
        name = str(speakers.get("name") or "")
        for row in p.get_loopback_device_info_generator():
            if name and name in str(row.get("name") or ""):
                return row
        raise RuntimeError("default Windows WASAPI loopback device not found")

    def start(self):
        if not self.available():
            return False
        recorder = threading.Thread(target=self._record_loop, name="suryadev-audio-record", daemon=True)
        transcriber = threading.Thread(target=self._transcribe_loop, name="suryadev-audio-asr", daemon=True)
        self._threads = [recorder, transcriber]
        transcriber.start()
        recorder.start()
        return True

    def _record_loop(self):
        try:
            import pyaudiowpatch as pyaudio
            pa = pyaudio.PyAudio()
            try:
                dev = self._loopback_device(pa, pyaudio)
                rate = int(dev.get("defaultSampleRate") or 48000)
                channels = max(1, min(int(dev.get("maxInputChannels") or 2), 2))
                sample_format = pyaudio.paInt16
                width = pa.get_sample_size(sample_format)
                stream = pa.open(
                    format=sample_format,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=int(dev["index"]),
                    frames_per_buffer=1024,
                )
                try:
                    chunk_index = 0
                    while not self.stop_event.is_set():
                        frames = []
                        chunk_started = time.monotonic()
                        while (
                            not self.stop_event.is_set()
                            and time.monotonic() - chunk_started < self.chunk_seconds
                        ):
                            frames.append(stream.read(1024, exception_on_overflow=False))
                        if not frames:
                            continue
                        offset = max(0.0, chunk_started - self._started_at)
                        path = self.audio_dir / f"audio_{chunk_index:05d}.wav"
                        chunk_index += 1
                        with wave.open(str(path), "wb") as wav:
                            wav.setnchannels(channels)
                            wav.setsampwidth(width)
                            wav.setframerate(rate)
                            wav.writeframes(b"".join(frames))
                        try:
                            self.queue.put((path, offset), timeout=2)
                        except queue.Full:
                            self.dropped_or_stopped_for_backlog = True
                            self.error = "audio ASR backlog reached safety limit"
                            self.stop_event.set()
                finally:
                    stream.stop_stream()
                    stream.close()
            finally:
                pa.terminate()
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.stop_event.set()
        finally:
            try:
                self.queue.put_nowait(None)
            except queue.Full:
                pass

    def _transcribe_loop(self):
        try:
            from faster_whisper import WhisperModel
            model_name = str(os.getenv("SURYADEV_WHISPER_MODEL") or "tiny").strip()
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            while True:
                try:
                    item = self.queue.get(timeout=1)
                except queue.Empty:
                    if self.stop_event.is_set():
                        break
                    continue
                if item is None:
                    break
                path, offset = item
                try:
                    segments, _ = model.transcribe(
                        str(path),
                        beam_size=1,
                        vad_filter=True,
                        condition_on_previous_text=False,
                    )
                    for seg in segments:
                        text = re.sub(r"\s+", " ", str(seg.text or "").strip())
                        if text:
                            self.entries.append({
                                "seconds": round(float(offset) + float(seg.start or 0), 2),
                                "text": text[:1800],
                                "source": "system_audio_asr",
                            })
                finally:
                    try:
                        Path(path).unlink(missing_ok=True)
                    except Exception:
                        pass
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.stop_event.set()

    def stop(self):
        self.stop_event.set()
        for thread in self._threads:
            thread.join(timeout=max(5, self.chunk_seconds + 30))
        for path in self.audio_dir.glob("*.wav"):
            try:
                path.unlink()
            except Exception:
                pass
        return list(self.entries)


# Conservative heuristic speed control. It evaluates recorded caption text,
# not source intent; it never certifies understanding or transcript coverage.
_CRITICAL_HINTS = re.compile(
    r"\b(?:warning|important|critical|must not|never do|be careful|"
    r"step\s*\d+|first step|second step|formula|equation|security|"
    r"exception|error|bug|failure|safety|remember this|"
    r"command|terminal|code|python|javascript|function|algorithm|"
    r"install|configuration|parameter|architecture|experiment|"
    r"measurement|voltage|current|watt|ampere|cpu|gpu|"
    r"example|demonstration)\b|[=<>]|\d", re.I)
_EXPLANATION_HINTS = re.compile(
    r"\b(?:because|means that|the reason|explains?|how it works|"
    r"in other words|definition|the difference|understand|"
    r"consider|notice that|the point is|for instance)\b", re.I)
_CHATTER_HINTS = re.compile(
    r"\b(?:like and subscribe|hit the bell|subscribe to the channel|"
    r"welcome back|hello everyone|hey everyone|hi guys|"
    r"thanks for watching|see you next time|leave a comment|"
    r"share this video|smash that like|just chatting|small talk|"
    r"how are you guys|let me know in the comments)\b", re.I)


def classify_video_caption(caption, *, important_terms=()):
    """Return (label, rate) for a new caption. High-value cues win over chatter."""
    text = re.sub(r"\s+", " ", str(caption or "")).strip().casefold()
    if not text:
        return "caption_missing", 1.0
    if any(str(term).strip().casefold() in text for term in important_terms if str(term).strip()):
        return "owner_important", 1.0
    if _CRITICAL_HINTS.search(text):
        return "important", 1.0
    # No English-only heuristic is allowed to treat Odia/Hindi/other
    # unfamiliar writing systems as known low-value chatter.
    if re.search(r"[\u0900-\u0d7f\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text):
        return "unclassified_language", 1.0
    if _EXPLANATION_HINTS.search(text):
        return "explanation", 1.5
    if _CHATTER_HINTS.search(text):
        return "chatter", 3.0
    return "ordinary", 2.0


def verified_video_speed_ceiling(data_root, *, browser_channel=None, now=None):
    """Derive a conservative node-local cap from genuine earlier speed tests.

    The official speed sweep emits a per-rate pass flag based on measured
    media-clock movement, not merely video.playbackRate. A failed 2x / 3x
    cannot silently become a permitted learning rate after a restart.
    When there is no recent compatible test, default to 1x (unverified).
    """
    result = {"max_rate": 1.0, "source": "no_recent_verified_sweep",
              "report": "", "tested_channel": browser_channel or "unknown"}
    root = Path(data_root).expanduser().resolve()
    report_dir = root / "benchmark-reports"
    if report_dir.is_symlink() or not report_dir.is_dir():
        return result
    if browser_channel not in ("chrome", "msedge", "chromium"):
        return result
    now = time.time() if now is None else float(now)
    candidates = sorted(report_dir.glob("video-speed-sweep-"+browser_channel+"-*.json"),
                        key=lambda p:p.name, reverse=True)
    for path in candidates[:20]:
        try:
            if path.is_symlink() or not 0 < path.stat().st_size <= 2_000_000:
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            tested = float(record.get("finished_at", 0))
            if not (0 <= now - tested <= 7*24*3600):
                continue
            if record.get("schema") != "suryadev.video-speed-sweep.v1":
                continue
            if record.get("browser_channel") != browser_channel:
                continue
            if record.get("evidence_only") is not True:
                continue
            assessment = record.get("speed_results", {})
            rows = assessment.get("speeds", [])
            if not isinstance(rows, list):
                continue
            passed = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                rate = row.get("requested_speed_x")
                if type(rate) in (int,float) and rate in (1.0,1.5,2.0,3.0):
                    passed[float(rate)] = row.get("pass") is True
            # Only contiguous, independently passed rates can be used.
            cap = 1.0
            if passed.get(1.0):
                for rate in (1.5,2.0,3.0):
                    if passed.get(rate):
                        cap = rate
                    else:
                        break
            return {"max_rate": cap, "source": "recent_local_media_clock_sweep",
                    "report": path.name, "tested_channel": browser_channel,
                    "passed_rates": [r for r in (1.0,1.5,2.0,3.0) if passed.get(r)]}
        except (OSError,ValueError,TypeError,OverflowError):
            continue
    return result


class AdaptiveVideoSpeed:
    """Playback controller for a *single approved* browser job.

    3x is a temporary optimization, only after repeated clear chatter
    captions. Captions/visuals may still be missed, especially at 3x.
    """
    def __init__(self, important_terms=(), enabled=True, max_rate=3.0):
        if type(max_rate) not in (int,float) or max_rate not in (1.0,1.5,2.0,3.0):
            raise ValueError("Max video learning speed must be 1, 1.5, 2 or 3")
        self.terms = tuple(important_terms)
        self.enabled = enabled
        self.max_rate = float(max_rate)
        self.chatter_streak = 0
        self.last_caption = ""
        self.last_caption_video_time = 0.0
        self.target_rate = 1.0
        self.category = "initial_safe_speed"

    def choose(self, caption, *, video_seconds, caption_available, asr_active=False):
        if not self.enabled or asr_active:
            self.target_rate = 1.0
            self.category = "disabled_or_audio_only"
            return self.target_rate, self.category
        clean = re.sub(r"\s+", " ", str(caption or "")).strip()
        if not caption_available or not clean:
            self.chatter_streak = 0
            self.target_rate = 1.0
            self.category = "no_captions"
            return self.target_rate, self.category
        video_seconds = max(0.0, float(video_seconds or 0))
        if clean != self.last_caption:
            category, suggested = classify_video_caption(clean, important_terms=self.terms)
            self.chatter_streak = self.chatter_streak + 1 if category == "chatter" else 0
            self.last_caption = clean
            self.last_caption_video_time = video_seconds
            self.category = category
            proposed = (3.0 if self.chatter_streak >= 2 else 2.0) if suggested == 3.0 else suggested
            self.target_rate = min(proposed, self.max_rate)
            if proposed > self.max_rate:
                self.category = category + "_speed_capped_by_measured_playback"
        elif video_seconds - self.last_caption_video_time > 5.0:
            # If captions stop changing, racing through unknown content is unsafe.
            self.chatter_streak = 0
            self.category = "caption_stalled"
            self.target_rate = 1.0
        return self.target_rate, self.category


def _apply_video_rate(page, desired):
    """Apply and read back HTMLVideoElement playbackRate; do not guess."""
    try:
        actual = page.evaluate(
            """(rate) => {
                 const v = document.querySelector('video');
                 if (!v) return null;
                 if (Math.abs(Number(v.playbackRate) - rate) > 0.05) v.playbackRate = rate;
                 return Number(v.playbackRate);
               }""", float(desired))
        if actual is None:
            return None
        actual = float(actual)
        return actual if actual in (1.0, 1.5, 2.0, 3.0) else None
    except Exception:
        return None


class VideoProgressGuard:
    """Observe a real content clock; ads and stalled playback are NOT learning."""

    def __init__(self, now, *, stalled_seconds=60, ad_wait_seconds=120):
        self.last_progress_at = float(now)
        self.last_content_seconds = 0.0
        self.ad_since = None
        self.ad_events = 0
        self.ad_wall_seconds = 0.0
        self.stalled_seconds = float(stalled_seconds)
        self.ad_wait_seconds = float(ad_wait_seconds)

    def tick(self, snapshot, *, now):
        now = float(now)
        if snapshot.get("ad_showing") is True:
            if self.ad_since is None:
                self.ad_since = now
                self.ad_events += 1
            # Waiting for ordinary provider playback is not content watching;
            # never skip forward, click ad buttons or forge video progress.
            if now - self.ad_since >= self.ad_wait_seconds:
                return "advertisement_wait_limit"
            return None
        if self.ad_since is not None:
            self.ad_wall_seconds += max(0.0, now - self.ad_since)
            self.ad_since = None
            self.last_progress_at = now
            self.last_content_seconds = 0.0
        try:
            position = float(snapshot.get("seconds") or 0)
        except (ValueError, TypeError):
            position = 0.0
        if position > self.last_content_seconds + 0.5:
            self.last_content_seconds = position
            self.last_progress_at = now
        if now - self.last_progress_at >= self.stalled_seconds:
            return "content_playback_stalled"
        return None


def _chromium_content_filter():
    """Opt-in local uBO Lite MV3 integration, without downloads or token access.

    Source: github.com/uBlockOrigin/uBOL-home and github.com/gorhill/uBlock.
    Operator supplies reviewed unpacked extension path; a missing or invalid
    extension FAILS CLOSED rather than silently launching an unfiltered browser.
    """
    raw = str(os.getenv("SURYADEV_UBOL_EXTENSION_DIR") or "").strip()
    if not raw:
        return {"enabled": False, "args": []}
    path = Path(raw).expanduser()
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("uBO Lite extension path must be a non-symlink absolute directory")
    path = path.resolve(strict=True)
    manifest = path / "manifest.json"
    if not path.is_dir() or not manifest.is_file() or manifest.is_symlink():
        raise ValueError("Unpacked uBO Lite manifest.json is missing")
    if manifest.stat().st_size > 65536:
        raise ValueError("uBO Lite extension manifest exceeds size limit")
    config = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Expected JSON object in unpacked uBO Lite manifest")
    perms = config.get("permissions", [])
    if (config.get("manifest_version") != 3
            or not isinstance(perms, list)
            or "declarativeNetRequest" not in perms):
        raise ValueError("Expected unpacked Manifest V3 declarative uBO Lite ruleset")
    if "nativeMessaging" in perms or "debugger" in perms:
        raise ValueError("Unexpected privileged extension permissions")
    # No remote lookup/auto installation. Playwright's bundled Chromium
    # supports MV3 with a persistent context and channel='chromium'.
    return {"enabled": True, "args": [
        "--disable-extensions-except=" + str(path),
        "--load-extension=" + str(path)]}


def _video_browser_channel(content_filter):
    """One local browser choice; no binary downloads or anti-bot workarounds.

    Branded Chrome/Edge may support media codecs absent from Playwright's
    bundled Chromium. They no longer allow MV3 extension side-loading
    through the flags used for optional reviewed uBO Lite.
    """
    requested = str(os.getenv("SURYADEV_VIDEO_BROWSER_CHANNEL") or "").strip().lower()
    if requested not in ("", "chromium", "chrome", "msedge"):
        raise ValueError("Supported local browser channels: chromium, chrome, msedge")
    if content_filter["enabled"]:
        if requested not in ("", "chromium"):
            raise ValueError(
                "Optional uBO Lite unpacked extension needs Playwright Chromium; "
                "Chrome/Edge block sideloading with those flags")
        return "chromium"
    return requested or None


def _video_snapshot(page):
    script = r"""
    () => {
      const v=document.querySelector('video');
      const caps=[...document.querySelectorAll('.ytp-caption-segment')]
        .map(x=>(x.innerText||'').trim()).filter(Boolean).join(' ');
      return {
        url: location.href,
        title: (document.title||'').replace(/\s*-\s*YouTube\s*$/i,'').trim(),
        seconds: v ? Number(v.currentTime||0) : 0,
        duration: v && Number.isFinite(v.duration) ? Number(v.duration) : 0,
        paused: v ? !!v.paused : true,
        video_ready_state: v ? Number(v.readyState) : null,
        video_network_state: v ? Number(v.networkState) : null,
        video_error_code: v && v.error ? Number(v.error.code) : null,
        ad_showing: !!document.querySelector('.html5-video-player.ad-showing'),
        ended: v ? !!v.ended : false,
        playback_rate: v ? Number(v.playbackRate||1) : null,
        caption: caps
      };
    }
    """
    try:
        row = page.evaluate(script)
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}


def _try_enable_captions(page):
    try:
        button = page.locator(".ytp-subtitles-button")
        if button.count() and button.first.get_attribute("aria-pressed") != "true":
            button.first.click(timeout=2000)
    except Exception:
        pass


def _try_play(page):
    try:
        page.evaluate("() => { const v=document.querySelector('video'); if(v && v.paused){ v.play().catch(()=>{}); } }")
    except Exception:
        pass


def _capture_video_frame(page, frames_dir, subject, seconds, reason, title):
    stamp = _clock(seconds)
    subject_name = _safe_name(subject)
    subject_dir = frames_dir / subject_name
    subject_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{subject_name}__{stamp}__{_safe_name(reason,40)}.jpg"
    path = subject_dir / filename
    try:
        video = page.locator("video")
        if video.count():
            video.first.screenshot(path=str(path), type="jpeg", quality=72)
        else:
            page.screenshot(path=str(path), type="jpeg", quality=72, full_page=False)
    except Exception:
        return None
    if not path.is_file() or path.stat().st_size <= 0:
        return None
    return {
        "subject": subject,
        "timestamp_seconds": round(float(seconds or 0), 2),
        "timestamp": stamp,
        "local_ref": str(path),
        "sha256": _sha256(path),
        "reason": reason,
        "source_title": title,
        "research_question": (
            f"What does the visual evidence at {stamp} establish about {subject}, "
            "and which parts require independent source/lab verification?"
        ),
        "lab_relevance": True,
    }


def _chunk_transcript(entries, chunk_seconds, subject, source_url, title):
    windows = {}
    for row in entries:
        sec = max(0.0, float(row.get("seconds") or 0))
        bucket = int(sec // chunk_seconds)
        windows.setdefault(bucket, []).append(row)
    out = []
    for bucket in sorted(windows):
        rows = windows[bucket]
        start = bucket * chunk_seconds
        end = max(float(x.get("seconds") or start) for x in rows)
        text = " ".join(str(x.get("text") or "").strip() for x in rows if str(x.get("text") or "").strip())
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        # Keep each BRAHMA intake bounded. Longer windows are split deterministically.
        while text:
            piece, text = text[:7000], text[7000:]
            out.append({
                "topic": subject,
                "text": piece,
                "start_seconds": round(float(start), 2),
                "end_seconds": round(float(end), 2),
                "source_ref": source_url,
                "source_title": title,
                "modality": "video_caption_text",
                "confidence": 0.72,
                "evidence_status": "candidate",
                "research_required": True,
            })
    return out[:120]


def observe(job, workspace):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is required by SURYDEV video learning adapter") from exc

    constraints = dict(job.get("constraints") or {})
    source_url = str(job.get("target") or job.get("source_ref") or "").strip()
    if not _is_http_url(source_url):
        raise ValueError("SURYDEV video adapter currently requires an http(s) browser source")

    duration_seconds = max(30, min(int(constraints.get("duration_seconds") or 6 * 3600), 6 * 3600))
    finish_grace = max(0, min(int(constraints.get("finish_grace_seconds") or 300), 600))
    adaptive_playback = constraints.get("adaptive_playback", True) is not False
    # Poll quickly at high speed: a 5-second wall-clock poll misses 15s at 3x.
    configured_sample = float(constraints.get("sample_seconds") or 5)
    sample_seconds = (max(0.25, min(configured_sample, 0.5))
                      if adaptive_playback else max(2, min(configured_sample, 30)))
    chunk_seconds = max(300, min(int(constraints.get("learning_chunk_seconds") or 600), 1800))
    visual_interval = max(300, min(int(constraints.get("visual_interval_seconds") or 1200), 3600))
    max_visuals = max(1, min(int(constraints.get("max_visual_evidence") or 24), 60))
    capture_terms = [
        str(x).strip().lower()
        for x in (constraints.get("capture_terms") or [])
        if str(x).strip()
    ][:80]
    subject_hint = str(constraints.get("subject") or job.get("target") or "video-learning").strip()[:240]

    workspace = Path(workspace).resolve()
    transcript_dir = workspace / "transcript"
    frames_dir = workspace / "frames"
    browser_profile = workspace / "browser-profile"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    browser_profile.mkdir(parents=True, exist_ok=True)

    transcript_rows = []
    visual_evidence = []
    audio_asr = None
    audio_asr_started = False
    caption_seen = False
    last_caption = ""
    last_periodic = -visual_interval
    term_last_seen = {}
    content_filter = _chromium_content_filter()
    browser_channel = _video_browser_channel(content_filter)
    # The benchmark probes a branded browser; no Chrome result is assumed
    # transferable to bundled Chromium. Other nodes retain independent caps.
    root_from_job = workspace.parents[3] if (
        workspace.parent.name == "jobs" and
        workspace.parent.parent.name == "runtime" and
        workspace.parent.parent.parent.name == "video-review") else None
    speed_ceiling = (verified_video_speed_ceiling(
        root_from_job, browser_channel=browser_channel)
        if root_from_job is not None else {
            "max_rate":1.0, "source":"unrecognized_video_workspace"})
    speed_controller = AdaptiveVideoSpeed(
        capture_terms, enabled=adaptive_playback,
        max_rate=speed_ceiling["max_rate"])
    speed_events = []
    speed_event_total = 0
    last_logged_rate = None
    seen_three_x = False
    started_wall = time.time()
    started_mono = time.monotonic()
    progress_guard = VideoProgressGuard(started_mono)
    ad_suppressed_samples = 0
    stop_reason = "observation_window_completed"
    final = {}
    title = ""
    subject = subject_hint
    headless = str(os.getenv("SURYADEV_HEADLESS") or "").strip().lower() in {"1", "true", "yes", "on"}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(browser_profile),
            headless=headless,
            **({"channel": browser_channel} if browser_channel else {}),
            args=["--autoplay-policy=no-user-gesture-required"] + content_filter["args"],
            viewport={"width": 1280, "height": 800},
        )
        try:
            pages = context.pages
            page = pages[0] if pages else context.new_page()
            page.goto(source_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2500)
            _try_enable_captions(page)
            _try_play(page)
            page.wait_for_timeout(5000)
            first = _video_snapshot(page)
            caption_seen = (first.get("ad_showing") is not True and
                            bool(re.sub(r"\s+", " ", str(first.get("caption") or "").strip())))
            allow_audio_asr = bool(constraints.get("allow_audio_asr_fallback", True))
            if not caption_seen and allow_audio_asr and _SystemAudioASR.available():
                audio_asr = _SystemAudioASR(
                    workspace,
                    chunk_seconds=int(constraints.get("audio_chunk_seconds") or 60),
                )
                audio_asr_started = audio_asr.start()

            while True:
                snap = _video_snapshot(page)
                if snap:
                    final = snap
                    title = str(snap.get("title") or title or "Video").strip()[:500]
                    if subject_hint == source_url or subject_hint == "video-learning":
                        subject = title or "video-learning"
                    sec = float(snap.get("seconds") or 0)
                    guard_result = progress_guard.tick(snap, now=time.monotonic())
                    if snap.get("ad_showing") is True:
                        # Never put advertisement captions/frames into knowledge.
                        ad_suppressed_samples += 1
                        if guard_result:
                            stop_reason = guard_result
                            break
                        time.sleep(sample_seconds)
                        continue
                    if guard_result:
                        stop_reason = guard_result
                        break
                    caption = re.sub(r"\s+", " ", str(snap.get("caption") or "").strip())
                    desired_rate, speed_category = speed_controller.choose(
                        caption, video_seconds=sec, caption_available=bool(caption),
                        asr_active=audio_asr_started)
                    observed_rate = _apply_video_rate(page, desired_rate)
                    if observed_rate != last_logged_rate:
                        speed_event_total += 1
                        if observed_rate == 3.0:
                            seen_three_x = True
                        speed_event = {
                            "video_seconds": round(sec, 2),
                            "requested_rate": desired_rate,
                            "observed_rate": observed_rate,
                            "category": speed_category,
                            "caption_available": bool(caption),
                            "audio_only_fallback": audio_asr_started,
                        }
                        speed_events.append(speed_event)
                        speed_events = speed_events[-120:]
                        last_logged_rate = observed_rate
                        # Optional dashboard telemetry, not an acceptance receipt.
                        _atomic_json(workspace / "playback-speed.json", {
                            "schema": "krishna.suryadev.playback-speed.v1",
                            "updated_at": time.time(),
                            "job_id": str(job.get("job_id") or ""),
                            **speed_event,
                            "coverage_verified": False,
                            "speed_event_total": speed_event_total,
                        })
                    if caption and caption != last_caption:
                        caption_seen = True
                        transcript_rows.append({"seconds": round(sec, 2), "text": caption[:1800], "source": "browser_caption"})
                        last_caption = caption

                        low = caption.lower()
                        matched = [term for term in capture_terms if term in low]
                        for term in matched:
                            if len(visual_evidence) >= max_visuals:
                                break
                            prior = float(term_last_seen.get(term) or -999999)
                            if sec - prior < 120:
                                continue
                            evidence = _capture_video_frame(
                                page, frames_dir, subject, sec, f"term_{term}", title
                            )
                            if evidence:
                                visual_evidence.append(evidence)
                                term_last_seen[term] = sec

                    if len(visual_evidence) < max_visuals and sec - last_periodic >= visual_interval:
                        evidence = _capture_video_frame(
                            page, frames_dir, subject, sec, "periodic_context", title
                        )
                        if evidence:
                            visual_evidence.append(evidence)
                            last_periodic = sec

                    elapsed = time.monotonic() - started_mono
                    duration = float(snap.get("duration") or 0)
                    remaining = max(0.0, duration - sec) if duration > 0 else None

                    if bool(snap.get("ended")):
                        stop_reason = "video_html_ended"
                        break
                    if elapsed >= duration_seconds:
                        # User requirement: if the shift ends with <=5 minutes left,
                        # finish the current video before handoff. Otherwise checkpoint.
                        # A stalled stream is still bounded and cannot hold the worker forever.
                        if (
                            remaining is not None
                            and remaining <= finish_grace
                            and elapsed <= duration_seconds + finish_grace + 120
                        ):
                            pass
                        else:
                            break
                    if bool(snap.get("paused")):
                        _try_play(page)
                else:
                    guard_result = progress_guard.tick({}, now=time.monotonic())
                    if guard_result:
                        stop_reason = "browser_snapshot_unavailable"
                        break

                time.sleep(sample_seconds)
        finally:
            context.close()

    asr_rows = audio_asr.stop() if audio_asr_started and audio_asr is not None else []
    if not caption_seen and asr_rows:
        transcript_rows = asr_rows

    transcript_path = transcript_dir / "transcript.txt"
    transcript_text = "\n".join(
        f"[{_clock(x['seconds'])}] {x['text']}" for x in transcript_rows
    )
    transcript_path.write_text(transcript_text, encoding="utf-8")

    chunks = _chunk_transcript(
        transcript_rows, chunk_seconds, subject, source_url, title
    )
    # No synthetic "visual-only learning session" transcript when captions
    # are missing. The frame hashes remain independently inspectable, but
    # only real timestamped source observations can become content candidates.

    evidence_dir = workspace / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    subject_manifest = {
        "schema": "krishna.suryadev.subject-evidence.v1",
        "job_id": str(job.get("job_id") or ""),
        "subject": subject,
        "source_url": source_url,
        "source_title": title,
        "visuals": visual_evidence,
        "research_questions": list(dict.fromkeys(
            x.get("research_question") for x in visual_evidence if x.get("research_question")
        )),
        "created_at": time.time(),
    }
    _atomic_json(evidence_dir / f"{_safe_name(subject)}__manifest.json", subject_manifest)

    lab_questions = list(dict.fromkeys(
        x.get("research_question") for x in visual_evidence if x.get("research_question")
    ))
    lab_dossier = {
        "schema": "krishna.suryadev.lab-dossier.v1",
        "job_id": str(job.get("job_id") or ""),
        "subject": subject,
        "source_url": source_url,
        "source_title": title,
        "transcript_sha256": _sha256(transcript_path),
        "learning_chunk_count": len(chunks),
        "selected_visuals": [{
            "timestamp": x.get("timestamp"),
            "sha256": x.get("sha256"),
            "reason": x.get("reason"),
            "research_question": x.get("research_question"),
        } for x in visual_evidence],
        "questions_for_rishi_or_lab": lab_questions,
        "verification_rules": [
            "separate what the frame visibly shows from what the speaker claimed",
            "find independent primary/technical sources before treating a claim as supported",
            "turn experimental ideas into falsifiable tests before LAB execution",
            "preserve contradictory or negative evidence",
        ],
        "created_at": time.time(),
    }
    _atomic_json(evidence_dir / f"{_safe_name(subject)}__lab-dossier.json", lab_dossier)

    bundle = {
        "schema": BUNDLE_SCHEMA,
        "job_id": str(job.get("job_id") or ""),
        "agent": "SURYDEV",
        "source": {
            "url": source_url,
            "title": title,
            "subject": subject,
        },
        "learning_chunks": chunks,
        "visual_evidence": visual_evidence,
        "lab_research": {
            "subject": subject,
            "questions": lab_questions,
            "dossier_local_ref": str(evidence_dir / f"{_safe_name(subject)}__lab-dossier.json"),
        },
        "transcript": {
            "local_ref": str(transcript_path),
            "sha256": _sha256(transcript_path),
            "temporary": True,
            "line_count": len(transcript_rows),
            "source": "browser_caption" if caption_seen else ("system_audio_asr" if asr_rows else "unavailable"),
            "audio_asr_started": audio_asr_started,
            "audio_asr_error": "" if audio_asr is None else audio_asr.error,
            "persistent_copy_allowed": False,
        },
        "session": {
            "started_at": started_wall,
            "ended_at": time.time(),
            "watched_seconds": round(float(final.get("seconds") or 0), 2),
            "source_duration_seconds": round(float(final.get("duration") or 0), 2),
            "video_ended": bool(final.get("ended")),
            "end_reason": stop_reason,
            "last_playback_diagnostic": {
                "paused": final.get("paused"),
                "ready_state": final.get("video_ready_state"),
                "network_state": final.get("video_network_state"),
                "media_error_code": final.get("video_error_code"),
                "ad_showing": final.get("ad_showing"),
                "observed_seconds": final.get("seconds"),
            },
            "video_advertisement_events": progress_guard.ad_events,
            "advertisement_wall_seconds": round(progress_guard.ad_wall_seconds, 2),
            "advertisement_samples_not_used_as_learning": ad_suppressed_samples,
            "content_filter": (
                "optional_local_ubol_mV3_loaded_unverified_effectiveness"
                if content_filter["enabled"] else "not_configured"),
            "provider_ad_blocking_verified": False,
            "browser_channel": browser_channel or "bundled_chromium_default",
            "browser_codec_support_verified": False,
            "finish_grace_seconds": finish_grace,
            "shift_limit_seconds": duration_seconds,
            "adaptive_playback": adaptive_playback,
            "playback_rates_attempted": sorted({
                float(e["requested_rate"]) for e in speed_events
                if type(e.get("requested_rate")) in (int, float)
            }),
            "playback_rate_cap": speed_controller.max_rate,
            "playback_rate_cap_source": speed_ceiling["source"],
            "speed_cap_benchmark_report": speed_ceiling.get("report", ""),
            "speed_events_total": speed_event_total,
            "speed_events_recent": speed_events,
            "three_x_observed": seen_three_x,
            "four_x_observed": False,
            "speed_heuristic_only": True,
            "complete_caption_coverage_verified": False,
            "high_speed_content_may_have_been_missed": seen_three_x,
        },
        "raw_media_included": False,
        "policy": {
            "source_video_downloaded": False,
            "full_transcript_transient": True,
            "selected_frames_transient_until_server_ack": True,
            "durable_learning": "bounded learning chunks + provenance + selected visual hashes only",
            "verification_required": True,
        },
        "created_at": time.time(),
    }
    bundle_path = workspace / "learning-bundle.json"
    _atomic_json(bundle_path, bundle)
    return bundle


def main(argv=None):
    argv = list(argv or sys.argv[1:])
    if len(argv) != 2:
        print("usage: SURYDEV_VIDEO_LEARNING_ADAPTER.py <job.json> <workspace>", file=sys.stderr)
        return 2
    job_path = Path(argv[0]).resolve()
    workspace = Path(argv[1]).resolve()
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if job.get("schema") != "krishna.suryadev.job.v1":
        raise ValueError("unsupported SURYDEV job schema")
    bundle = observe(job, workspace)
    print(json.dumps({
        "ok": True,
        "job_id": bundle["job_id"],
        "learning_chunks": len(bundle["learning_chunks"]),
        "visual_evidence": len(bundle["visual_evidence"]),
        "transcript_temporary": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
