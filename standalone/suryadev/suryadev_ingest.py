"""Strict source ingestion: public website text, approved PDF pages, YouTube captions.

PDF text extraction and YouTube caption extraction are optional dependencies.
No result here proves full video *visual* learning, or comprehension.
"""
from __future__ import annotations

from html import unescape
from io import BytesIO
import os
import re
from pathlib import Path
import tempfile
from urllib.request import Request, build_opener, ProxyHandler

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 500
MAX_LEARNING_CHARS = 220_000
MAX_CAPTION_BYTES = 2_000_000
_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com",
             "youtu.be", "www.youtu.be", "www.youtube-nocookie.com"}
_YT_ID = re.compile(r"^[a-zA-Z0-9_-]{11}$")
_CUE = re.compile(
    r"(?m)^(?:\d+\s*\n)?"
    r"((?:\d{2}:)?\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*"
    r"((?:\d{2}:)?\d{2}:\d{2}[.,]\d{1,3})[^\n]*\n"
    r"([\s\S]*?)(?=\n\s*\n|\Z)"
)


def _seconds(value):
    parts = value.replace(",", ".").split(":")
    return sum(float(part) * 60 ** i for i, part in enumerate(reversed(parts)))


def caption_cues(value):
    """Extract timestamped SRT/VTT cues. Do not mistake plain transcripts for coverage."""
    text = value.replace("\r", "")
    cues = []
    for match in _CUE.finditer(text):
        start, end = _seconds(match.group(1)), _seconds(match.group(2))
        speech = unescape(re.sub(r"<[^>]*>", "", match.group(3))).strip()
        speech = re.sub(r"\s+", " ", speech)
        if 0 <= start < end and speech:
            cues.append((start, end, speech))
    return sorted(cues, key=lambda row: row[0])


def caption_report(cues, duration):
    if not cues:
        raise ValueError("YouTube captions have no usable timestamped cues")
    latest = max(end for _, end, _ in cues)
    earliest = min(start for start, _, _ in cues)
    gaps = []
    end_so_far = earliest
    for start, end, _ in cues:
        if start - end_so_far > 60:
            gaps.append({"start_seconds": round(end_so_far, 1),
                         "end_seconds": round(start, 1)})
        end_so_far = max(end_so_far, end)
    duration = float(duration) if duration else None
    near_end = bool(duration and latest >= duration - max(30, duration * 0.02))
    return {
        "cue_count": len(cues), "duration_seconds": duration,
        "first_cue_seconds": round(earliest, 2),
        "last_cue_seconds": round(latest, 2),
        "long_uncaptioned_gaps": gaps[:50],
        "last_cue_near_duration_end": near_end,
        "full_video_visuals_verified": False,
        "full_audio_coverage_verified": False,
        "coverage_status": "caption_timeline_only_unverified",
        "note": "Captions alone do not prove full spoken or visual content coverage."
    }


def ingest_pdf(url):
    """Download and text-extract every page, failing closed for missing page text."""
    from suryadev import validate_url, StrictRedirect
    validate_url(url)
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF support requires: python -m pip install pypdf") from exc
    opener = build_opener(ProxyHandler({}), StrictRedirect())
    request = Request(url, headers={"User-Agent": "SuryadevStandalone/0.3 (approved research)",
                                    "Accept": "application/pdf", "Accept-Encoding": "identity"})
    with opener.open(request, timeout=35) as response:
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("PDF content encoding unsupported")
        size_header = response.headers.get("Content-Length")
        if size_header and int(size_header) > MAX_PDF_BYTES:
            raise ValueError("PDF exceeds 20 MB limit")
        raw = response.read(MAX_PDF_BYTES + 1)
    if len(raw) > MAX_PDF_BYTES:
        raise ValueError("PDF exceeds 20 MB limit")
    if not raw.lstrip()[:8].startswith(b"%PDF-"):
        raise ValueError("source response is not a PDF")
    try:
        pdf = PdfReader(BytesIO(raw), strict=True)
    except Exception as exc:
        raise ValueError("PDF could not be parsed") from exc
    if pdf.is_encrypted:
        raise ValueError("Encrypted PDF requires separately approved access")
    count = len(pdf.pages)
    if count < 1 or count > MAX_PDF_PAGES:
        raise ValueError("PDF page count out of supported range")
    chunks = []
    missing = []
    for number, page in enumerate(pdf.pages, start=1):
        try:
            contents = (page.extract_text() or "").strip()
        except Exception as exc:
            raise ValueError(f"PDF text extraction failed at page {number}") from exc
        if not contents:
            missing.append(number)
        chunks.append(f"[PDF page {number}/{count}]\n{contents}")
    from suryadev_deep_pdf import deep_pdf_settings
    deep_enabled, model = deep_pdf_settings()
    extra = {}
    if deep_enabled:
        from suryadev_deep_pdf import inspect_pdf_pages, ollama_vision
        if not model:
            raise RuntimeError("SURYADEV_DEEP_PDF requires SURYADEV_VISION_MODEL for all page visuals")
        pages, extra = inspect_pdf_pages(
            raw, pdf, vision=lambda image: ollama_vision(image, model),
            analyze_visuals=True)
        chunks = []
        for page in pages:
            chunks.append(
                "[PDF page {}/{}]\\n{}\\n[OCR of page {}]\\n{}\\n"
                "[LOCAL MODEL VISUAL OBSERVATIONS, UNVERIFIED]\\n{}".format(
                    page["page"], count, page["selectable_text"],
                    page["page"], page["ocr_text"],
                    page["visual_observations"]))
        missing = []
    elif missing:
        raise ValueError("PDF page text missing or scanned; OCR review required for pages " +
                         ",".join(map(str, missing[:20])))
    text = "\n\n".join(chunks)
    if len(text) > MAX_LEARNING_CHARS:
        raise ValueError("PDF text exceeds supported full-extraction budget; split PDF first")
    title = url.split("/")[-1].split("?")[0] or "PDF document"
    return title, text, {
        "kind": "pdf", "pages_total": count, "pages_extracted": count,
        "pages_missing_text": [], "bytes_downloaded": len(raw),
        "coverage_status": extra.get("coverage_status", "all_pages_text_extracted"),
        "deep_pdf_enabled": deep_enabled, "full_document_visuals_verified": False,
        "note": ("Each PDF page was rasterized, OCR read and sent to a local visual model; "
                 "model comprehension is not independently validated." if deep_enabled else
                 "Every PDF page has selectable text; diagrams, equations and images not verified."),
        **extra,
    }


def _youtube_url(url):
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _YT_HOSTS or parsed.username or parsed.password:
        raise ValueError("an explicitly approved HTTPS YouTube video URL is required")
    if parsed.port not in (None,443):
        raise ValueError("nonstandard YouTube port blocked")
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        candidate = parsed.path.strip("/")
    else:
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    if not _YT_ID.fullmatch(candidate):
        raise ValueError("YouTube URL must identify exactly one video")
    return candidate


def selected_caption_language():
    """Request ONE caption language to avoid 3 independent subtitle downloads.

    Operator may choose en / hi / or via SURYADEV_CAPTION_LANG.  No implicit
    fallback to extra languages is attempted when a track is rate-limited.
    """
    language = os.environ.get("SURYADEV_CAPTION_LANG", "en").strip().lower()
    if language not in {"en", "hi", "or"}:
        raise ValueError("SURYADEV_CAPTION_LANG must be en, hi, or or")
    return language


def ingest_youtube(url):
    """Download available subtitles only; no private playback or bypass behavior."""
    video_id = _youtube_url(url)
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("YouTube captions require: python -m pip install yt-dlp") from exc
    language = selected_caption_language()
    with tempfile.TemporaryDirectory(prefix="suryadev-captions-") as directory:
        folder = Path(directory)
        comments_opt_in = os.getenv("SURYADEV_YT_COMMENTS", "").strip().lower() in ("1","true","yes")
        opts = {
            "skip_download": True, "writesubtitles": True, "writeautomaticsub": True,
            "subtitleslangs": [language], "subtitlesformat": "vtt",
            "outtmpl": str(folder / "%(id)s.%(ext)s"),
            "noplaylist": True, "quiet": True,
            "ignoreerrors": False, "socket_timeout": 20,
            "retries": 0, "fragment_retries": 0, "extractor_retries": 0,
            "sleep_interval_requests": 1.5, "sleep_interval_subtitles": 2,
        }
        if comments_opt_in:
            # Limited, explicit ONE-TIME comment collection: never retry 429.
            # Comments are opinions and cannot be promoted to verified facts.
            opts["getcomments"] = True
            opts["extractor_args"] = {"youtube": {"max_comments": ["50","50","0","0","1"]}}
        try:
            with yt_dlp.YoutubeDL(opts) as downloader:
                info = downloader.extract_info(url, download=True)
        except Exception as exc:
            error_text = str(exc)
            if "429" in error_text or "too many requests" in error_text.casefold():
                raise RuntimeError(
                    "YouTube HTTP 429 Too Many Requests while downloading " +
                    language + " captions. No automatic retry; stop requests " +
                    "and respect the provider's rate limit.") from exc
            raise
        if not isinstance(info, dict) or info.get("id") != video_id:
            raise ValueError("YouTube returned unexpected video metadata")
        if info.get("is_live") is True or info.get("live_status") == "is_live":
            raise ValueError("Live YouTube streams are not supported")
        duration = info.get("duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise ValueError("YouTube video duration unavailable; cannot assess caption timeline")
        files = sorted(folder.glob(video_id + ".*.vtt"))
        if not files:
            raise ValueError("No supported YouTube captions available; no full-video claim")
        best = None
        for file in files:
            if file.stat().st_size > MAX_CAPTION_BYTES:
                continue
            cues = caption_cues(file.read_text(encoding="utf-8-sig"))
            if not cues:
                continue
            report = caption_report(cues, duration)
            score = (report["last_cue_seconds"], len(cues))
            if best is None or score > best[0]:
                best = score, file, cues, report
        if best is None:
            raise ValueError("No usable timestamped captions within size limit")
        _, selected, cues, report = best
        lines = []
        previous = None
        for start, end, speech in cues:
            if speech != previous:
                lines.append(f"[{start:.2f}-{end:.2f}s] {speech}")
            previous = speech
        # Video description and chapter metadata are text evidence from the
        # same approved metadata response. The footage/audio are NOT decoded.
        description = str(info.get("description") or "").strip()
        if len(description) > 30_000:
            raise ValueError("YouTube description exceeds complete evidence budget")
        chapters = info.get("chapters") if isinstance(info.get("chapters"), list) else []
        chapter_lines = []
        for ch in chapters[:200]:
            if isinstance(ch, dict):
                chapter_lines.append("[{}-{}s] {}".format(
                    ch.get("start_time"), ch.get("end_time"),
                    str(ch.get("title") or "")[:180]))
        comments = info.get("comments") if isinstance(info.get("comments"), list) else []
        comments_text = []
        for item in comments[:50]:
            if isinstance(item, dict):
                comments_text.append(str(item.get("text") or "")[:1600])
        text = "\n".join(lines)
        text += "\n\n[VIDEO DESCRIPTION - PUBLISHER METADATA]\n" + description
        text += "\n\n[VIDEO CHAPTER MARKERS]\n" + "\n".join(chapter_lines)
        if comments_opt_in:
            text += "\n\n[PUBLIC COMMENTS - UNVERIFIED OPINIONS]\n" + "\n".join(comments_text)
        if len(text) > MAX_LEARNING_CHARS:
            raise ValueError("Caption transcript exceeds supported full-processing budget")
        report.update({
            "kind": "youtube", "video_id": video_id,
            "caption_file": selected.name, "caption_language": selected.suffixes[-2].lstrip("."),
            "caption_language_requested": language,
            "coverage_status": "caption_timeline_only_unverified",
            "description_characters": len(description),
            "chapter_markers": len(chapter_lines),
            "comments_requested": comments_opt_in,
            "comments_received": len(comments_text),
            "comments_completeness_verified": False,
            "full_video_visuals_verified": False,
            "full_audio_coverage_verified": False,
        })
        return str(info.get("title") or "YouTube video")[:500], text, report


def ingest_source(url, *, garudanetra=None, data_root=None, job_id=None):
    """Route all website reads through Garudanetra, never ordinary urllib."""
    from suryadev_sources import source_kind
    kind = source_kind(url)
    if kind == "pdf":
        return ingest_pdf(url)
    if kind == "youtube":
        return ingest_youtube(url)
    if kind == "website":
        from suryadev_garudanetra import render_website
        if garudanetra is None:
            title, text, receipt = render_website(url, root=data_root, job_id=job_id)
        else:
            title, text, receipt = garudanetra.render(url, job_id=job_id)
        if not text:
            raise ValueError("Garudanetra returned no readable webpage text")
        if len(text) > MAX_LEARNING_CHARS:
            raise ValueError("Rendered website text exceeds supported complete-processing budget")
        return title, text, receipt
    raise ValueError("unsupported queued source type")
