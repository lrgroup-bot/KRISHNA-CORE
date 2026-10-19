"""Opt-in SURYADEV media utilities. Explicit files/URLs only; no surveillance."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from suryadev import Library, validate_url
from suryadev_extras import import_transcript

def transcribe_file(path, *, model_size="small", language=None, device="cpu"):
    file = Path(path).expanduser().resolve(strict=True)
    if file.suffix.lower() not in {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".flac", ".ogg"}:
        raise ValueError("unsupported media extension")
    if file.stat().st_size > 1_000_000_000:
        raise ValueError("media exceeds 1 GB")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("install optional faster-whisper first") from exc
    model = WhisperModel(model_size, device=device, compute_type="int8" if device == "cpu" else "float16")
    segments, info = model.transcribe(str(file), language=language, vad_filter=True)
    rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    return {"language": info.language, "segments": rows, "text": "\n".join(x["text"] for x in rows)}

def youtube_subtitles(url, *, output_dir):
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {
        "www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"
    }:
        raise ValueError("approved HTTPS YouTube URL required")
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("install optional yt-dlp first") from exc
    folder = Path(output_dir).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    opts = {
        "skip_download": True, "writesubtitles": True, "writeautomaticsub": True,
        "subtitleslangs": ["en", "hi", "or"], "subtitlesformat": "vtt",
        "outtmpl": str(folder / "%(id)s.%(ext)s"), "noplaylist": True,
        "ignoreerrors": False, "quiet": True, "max_downloads": 1,
        "socket_timeout": 20
    }
    with yt_dlp.YoutubeDL(opts) as dl:
        info = dl.extract_info(url, download=True)
    if not info:
        raise RuntimeError("video metadata unavailable")
    return sorted(str(p) for p in folder.glob(f"{info.get('id', '')}*.vtt"))

def capture_page(url, output, *, allow_hosts):
    validate_url(url)
    parsed = urlparse(url)
    if parsed.hostname not in allow_hosts:
        raise ValueError("hostname not allowlisted")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("install optional playwright and Chromium first") from exc
    out = Path(output).expanduser().resolve()
    if out.suffix.lower() != ".png":
        raise ValueError("output must be a PNG")
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=False, permissions=[], service_workers="block")
        def gate(route):
            target = urlparse(route.request.url)
            if target.scheme == "https" and target.hostname in allow_hosts:
                route.continue_()
            else:
                route.abort()
        context.route("**/*", gate)
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.screenshot(path=str(out), full_page=True, timeout=15000)
            return {"title": page.title()[:500], "screenshot": str(out)}
        finally:
            browser.close()

def main(argv=None):
    ap = argparse.ArgumentParser(description="SURYADEV optional media tools")
    ap.add_argument("--data", default=str(Path.home() / "SURYADEV-DATA"))
    sub = ap.add_subparsers(dest="action", required=True)
    t = sub.add_parser("transcribe")
    t.add_argument("file")
    t.add_argument("--model-size", default="small")
    t.add_argument("--language")
    t.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    t.add_argument("--no-ollama", action="store_true")
    y = sub.add_parser("youtube-subtitles")
    y.add_argument("url")
    y.add_argument("--output-dir", default="transcripts")
    c = sub.add_parser("capture-page")
    c.add_argument("url")
    c.add_argument("output")
    c.add_argument("--allow-host", action="append", required=True)
    args = ap.parse_args(argv)
    if args.action == "transcribe":
        result = transcribe_file(args.file, model_size=args.model_size, language=args.language, device=args.device)
        folder = Path(args.data).expanduser().resolve() / "transcripts"
        folder.mkdir(parents=True, exist_ok=True)
        source_file = Path(args.file).expanduser().resolve(strict=True)
        fingerprint = hashlib.sha256(str(source_file).encode("utf-8")).hexdigest()[:12]
        target = folder / (source_file.stem + "-" + fingerprint + ".txt")
        target.write_text(result["text"], encoding="utf-8")
        lib = Library(args.data)
        try:
            receipt = import_transcript(lib, target, source_url=source_file.as_uri(), use_ollama=not args.no_ollama)
        finally:
            lib.db.close()
        print(json.dumps({"transcription": str(target), "language": result["language"], "finding": receipt}, indent=2))
    elif args.action == "youtube-subtitles":
        files = youtube_subtitles(args.url, output_dir=args.output_dir)
        lib = Library(args.data)
        try:
            results = [import_transcript(lib, f, source_url=args.url) for f in files]
        finally:
            lib.db.close()
        print(json.dumps({"files": files, "findings": results}, indent=2))
    else:
        print(json.dumps(capture_page(args.url, args.output, allow_hosts=set(args.allow_host)), indent=2))

if __name__ == "__main__":
    main()
