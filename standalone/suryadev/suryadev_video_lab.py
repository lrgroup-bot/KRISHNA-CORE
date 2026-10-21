"""Offline whole-file video research: decode every frame, audit modalities.

An owner supplies a lawfully available LOCAL video file and optional public
comment/description/transcript files. The tool never fetches videos, bypasses
a provider rate limit, patches a player, or claims sampled vision represents
every frame. Image hashing checks every decoded frame; selected screenshots
can be examined by the installed local Ollama vision model.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

from suryadev_ingest import caption_cues, caption_report
from suryadev_liveops import atomic_json

MAX_MEDIA_BYTES = 12 * 1024 ** 3
MAX_VIDEO_FRAMES = 300_000
MAX_SIDECAR_BYTES = 2_000_000
MAX_RESULT_CHARS = 220_000


def _read_text(path):
    if not path:
        return ""
    item = Path(path).expanduser().resolve(strict=True)
    if not item.is_file() or item.stat().st_size > MAX_SIDECAR_BYTES:
        raise ValueError("sidecar must be a regular local file <=2 MiB")
    return item.read_text(encoding="utf-8-sig")


def read_comments(path):
    if not path:
        return [], {"status": "not_supplied", "analyzed": 0}
    raw = _read_text(path)
    if str(path).lower().endswith(".jsonl"):
        items = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        items = json.loads(raw)
    if not isinstance(items, list) or len(items) > 5000:
        raise ValueError("comments sidecar must be a JSON list with <=5000 entries")
    comments = []
    for item in items:
        if isinstance(item, str):
            comment = item
        elif isinstance(item, dict):
            comment = item.get("text") or item.get("comment") or ""
        else:
            raise ValueError("invalid comment entry")
        if not isinstance(comment, str):
            raise ValueError("invalid comment text")
        comments.append(comment.strip()[:2000])
    return comments, {"status": "owner_supplied_public_comment_snapshot",
                      "analyzed": len(comments), "completeness_verified": False,
                      "note": "Comments are user opinions and cannot establish factual claims."}


def local_audio_transcript(media, model_dir):
    """Only a pre-downloaded local faster-whisper model: no surprise downloads."""
    directory = Path(model_dir).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("Whisper model path must be an installed local directory")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install faster-whisper to transcribe local audio") from exc
    model = WhisperModel(str(directory), device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(media), beam_size=5, vad_filter=False)
    rows = []
    for segment in segments:
        rows.append({
            "start": float(segment.start), "end": float(segment.end),
            "text": str(segment.text).strip()[:2000]})
        if len(rows) > 25_000:
            raise ValueError("audio transcript exceeds 25,000 segments")
    return rows, {"status": "local_audio_transcribed_unverified",
                  "segments": len(rows), "language": str(info.language),
                  "all_speech_correctness_verified": False}


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1_048_576), b""):
            digest.update(data)
    return digest.hexdigest()


def scan_video(path, *, capture=None, visual_fn=None, visual_interval_seconds=1,
               max_visual_frames=300, frame_limit=MAX_VIDEO_FRAMES,
               every_frame_vision=False):
    """Scan EVERY frame for count and digested pixels; optional sampled AI.

    All-frame checksum is NOT equivalent to visual semantic comprehension.
    An incomplete decoding raises and never writes a completed coverage claim.
    """
    video = Path(path).expanduser().resolve(strict=True)
    if not video.is_file() or video.stat().st_size > MAX_MEDIA_BYTES:
        raise ValueError("video must be a regular local file <=12 GiB")
    if not 0.25 <= visual_interval_seconds <= 60:
        raise ValueError("visual sample interval must be 0.25..60 seconds")
    if every_frame_vision and visual_fn is None:
        raise ValueError("every_frame_vision requires a local installed vision model")
    if not 0 <= max_visual_frames <= 50_000:
        raise ValueError("max_visual_frames must be 0..50000")
    if not 1 <= frame_limit <= MAX_VIDEO_FRAMES:
        raise ValueError("frame limit exceeds safe budget")
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Every-frame video scan requires opencv-python") from exc
    reader = capture if capture is not None else cv2.VideoCapture(str(video))
    if not reader.isOpened():
        raise RuntimeError("Cannot open permitted local video file")
    start = time.monotonic()
    chain = hashlib.sha256()
    processed = 0
    visual = []
    try:
        fps = float(reader.get(cv2.CAP_PROP_FPS))
        if not 0.1 <= fps <= 240:
            raise RuntimeError("Video frame rate is missing or invalid")
        expected = int(reader.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if expected and expected > frame_limit:
            raise ValueError("Video exceeds frame budget; split into audited chapters")
        if every_frame_vision and expected and expected > max_visual_frames:
            raise ValueError("each-frame vision exceeds explicit model-call budget")
        frame_period = (1 if every_frame_vision else
                        max(1, int(round(visual_interval_seconds * fps))))
        while True:
            success, frame = reader.read()
            if not success:
                break
            if processed >= frame_limit:
                raise ValueError("Decoded frame count exceeds safety limit; no full-video claim")
            # All decoded pixels are reflected in the rolling evidence digest.
            chain.update(hashlib.sha256(frame.tobytes()).digest())
            if visual_fn and processed % frame_period == 0 and len(visual) < max_visual_frames:
                observation = str(visual_fn(frame, processed / fps) or "").strip()
                if not observation:
                    raise ValueError("local vision model did not interpret sampled frame")
                visual.append({"frame": processed, "seconds": round(processed/fps, 3),
                               "observation": observation[:2000]})
            processed += 1
        if expected and abs(processed - expected) > max(2, round(expected * 0.01)):
            raise RuntimeError("Video ended before expected frames decoded")
        if every_frame_vision and len(visual) != processed:
            raise ValueError("Not every decoded frame received visual model interpretation")
        if processed == 0:
            raise RuntimeError("No video frames decoded")
        duration = processed / fps
        return {
            "frames_decoded": processed, "declared_frames": expected or None,
            "fps": fps, "video_duration_seconds": round(duration, 3),
            "last_frame_seconds": round((processed - 1) / fps, 3),
            "frame_pixel_chain_sha256": chain.hexdigest(),
            "all_decoded_frames_scanned": True,
            "frames_semantically_interpreted": len(visual),
            "all_frames_semantically_interpreted": bool(
                visual_fn and len(visual) == processed),
            "visual_samples": visual,
            "visual_coverage": ("local_vision_on_selected_frames_unverified"
                                if visual else "full_frame_scan_no_semantic_vision"),
            "duration_seconds_processing": round(time.monotonic() - start, 3),
            "note": "Frame decoding/hash is not the same as visual understanding.",
        }
    finally:
        reader.release()


def _vision_frame(frame, seconds, model):
    import cv2
    from PIL import Image
    from suryadev_deep_pdf import ollama_vision
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return ollama_vision(Image.fromarray(rgb), model)


def video_research(media, root, *, title="", description_file=None,
                   comments_file=None, transcript_file=None,
                   whisper_model_dir=None, vision_model=None,
                   visual_interval_seconds=1, max_visual_frames=300,
                   every_frame_vision=False, source_url="",
                   scanner=scan_video):
    """Create bounded evidence, not a claim of finished YouTube watching."""
    media = Path(media).expanduser().resolve(strict=True)
    if media.suffix.lower() not in {".mp4",".webm",".mkv",".mov",".avi"}:
        raise ValueError("only local approved video file formats are supported")
    if media.stat().st_size > MAX_MEDIA_BYTES:
        raise ValueError("local video exceeds size limit")
    description = _read_text(description_file)
    comments, comment_report = read_comments(comments_file)
    visual_fn = ((lambda frame, at: _vision_frame(frame, at, vision_model))
                 if vision_model else None)
    if every_frame_vision and not vision_model:
        raise ValueError("each-frame vision requires an explicitly selected local model")
    if source_url:
        from suryadev_ingest import _youtube_url
        _youtube_url(source_url)  # source provenance only; no network request.
    scan = scanner(media, visual_fn=visual_fn,
                   visual_interval_seconds=visual_interval_seconds,
                   max_visual_frames=max_visual_frames,
                   every_frame_vision=every_frame_vision)
    cues = []
    transcript_status = {"status": "not_supplied"}
    if transcript_file:
        cues = [{"start": start, "end": end, "text": text}
                for start,end,text in caption_cues(_read_text(transcript_file))]
        transcript_status = {
            "status": "timed_caption_sidecar_unverified",
            **(caption_report([(x["start"],x["end"],x["text"]) for x in cues],
                              scan["video_duration_seconds"]) if cues else
               {"cue_count": 0, "coverage_status": "no_caption_cues"})}
    elif whisper_model_dir:
        cues, transcript_status = local_audio_transcript(media, whisper_model_dir)
    media_digest = _file_sha256(media)
    text_sections = ["[VIDEO TITLE] " + str(title)[:500],
                     "[VIDEO FILE SHA256] " + media_digest,
                     "[DESCRIPTION] " + description,
                     "[TIMED TRANSCRIPT / AUDIO TEXT]"]
    text_sections.extend("[{start:.2f}-{end:.2f}s] {text}".format(**r) for r in cues)
    text_sections.append("[PUBLIC COMMENTS — OPINIONS, NOT FACTS]")
    text_sections.extend(comments)
    text_sections.append("[VISION MODEL OBSERVATIONS — UNVERIFIED]")
    text_sections.extend(
        "[{seconds:.2f}s/frame {frame}] {observation}".format(**r)
        for r in scan["visual_samples"])
    evidence = "\n".join(text_sections)
    if len(evidence) > MAX_RESULT_CHARS:
        raise ValueError("multi-modal text exceeds complete-processing budget; split chapters")
    result = {
        "schema": "suryadev.local-video-coverage.v1",
        "source_url": source_url, "media_file_name":media.name,
        "media_sha256":media_digest, "recorded_at":time.time(),
        "video":{k:v for k,v in scan.items() if k!="visual_samples"},
        "description_chars":len(description), "comments":comment_report,
        "transcript":transcript_status,
        "transcript_segments":len(cues),
        "semantic_comprehension_verified":False,
        "provider_youtube_requests":0, "rate_limit_bypass":False,
        "scope":"operator_provided_local_media_only",
    }
    root = Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    artifact = "video-audit-" + result["media_sha256"][:16] + ".json"
    evidence_name = "video-evidence-" + result["media_sha256"][:16] + ".txt"
    target = root / evidence_name
    temp = target.with_suffix(".txt.tmp")
    temp.write_text(evidence, encoding="utf-8")
    temp.replace(target)
    atomic_json(root, artifact, result)
    result["audit_file"] = str(root / artifact)
    result["evidence_file"] = str(target)
    return result
