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
        ended: v ? !!v.ended : false,
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
    sample_seconds = max(2, min(float(constraints.get("sample_seconds") or 5), 30))
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
    started_wall = time.time()
    started_mono = time.monotonic()
    final = {}
    title = ""
    subject = subject_hint
    headless = str(os.getenv("SURYADEV_HEADLESS") or "").strip().lower() in {"1", "true", "yes", "on"}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(browser_profile),
            headless=headless,
            args=["--autoplay-policy=no-user-gesture-required"],
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
            caption_seen = bool(re.sub(r"\s+", " ", str(first.get("caption") or "").strip()))
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
                    caption = re.sub(r"\s+", " ", str(snap.get("caption") or "").strip())
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
    if not chunks and visual_evidence:
        chunks = [{
            "topic": subject,
            "text": (
                "Visual-only learning session. Captions were unavailable or unreadable. "
                "Use the selected visual evidence and source timestamp for follow-up research; "
                "do not infer spoken claims that were not captured."
            ),
            "start_seconds": 0,
            "end_seconds": round(float(final.get("seconds") or 0), 2),
            "source_ref": source_url,
            "source_title": title,
            "modality": "visual_observation",
            "confidence": 0.45,
            "evidence_status": "candidate",
            "research_required": True,
        }]

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
            "finish_grace_seconds": finish_grace,
            "shift_limit_seconds": duration_seconds,
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
