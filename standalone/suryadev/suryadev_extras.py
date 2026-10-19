"""SURYADEV local-only research dashboard, scheduler, and transcript importer.

Run from this directory. Standard-library only. No remote server connections
except the explicit HTTPS research jobs handled by suryadev.py.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import html
import json
from pathlib import Path
import re
import threading
import time
from urllib.parse import parse_qs, urlsplit

from suryadev import Library, summarize

MAX_TRANSCRIPT = 2_000_000
MAX_REQUEST = 4096

def parse_transcript(text):
    """Remove SRT/VTT cue numbering and timecodes, preserving spoken content."""
    lines = []
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line or line == "WEBVTT" or line.isdigit():
            continue
        if re.match(r"^\d\d:\d\d(?::\d\d)?[.,]\d+\s+-->\s+", line):
            continue
        if re.match(r"^\d\d:\d\d:\d\d[.,]\d+\s+-->\s+", line):
            continue
        if line.startswith(("NOTE ", "STYLE", "REGION")):
            continue
        clean = re.sub(r"<[^>]*>", "", line)
        if clean and (not lines or clean != lines[-1]):
            lines.append(clean)
    return "\n".join(lines)

def import_transcript(lib, filename, source_url="", use_ollama=True, model="qwen3.5:9b"):
    file = Path(filename).expanduser().resolve(strict=True)
    if file.suffix.lower() not in {".txt", ".srt", ".vtt"}:
        raise ValueError("only .txt, .srt and .vtt are supported")
    if file.stat().st_size > MAX_TRANSCRIPT:
        raise ValueError("transcript exceeds 2 MB")
    text = parse_transcript(file.read_text(encoding="utf-8-sig"))
    if not text.strip():
        raise ValueError("transcript has no text")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    existing = lib.db.execute("SELECT id FROM findings WHERE sha256=?", (digest,)).fetchone()
    if existing:
        return {"duplicate_of": existing[0], "sha256": digest}
    title = file.stem[:500]
    reference = source_url or file.as_uri()
    summary = summarize(text, model) if use_ollama else text[:2000]
    now = time.time()
    with lib.db:
        cur = lib.db.execute(
            "INSERT INTO jobs(url,status,created,updated) VALUES (?,?,?,?)",
            (reference, "done", now, now))
        lib.db.execute(
            "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created) VALUES (?,?,?,?,?,?,?)",
            (cur.lastrowid, reference, digest, title, summary, text[:4000], now))
    return {"status": "done", "title": title, "sha256": digest}

def serve(lib, port=8769):
    """Dashboard binds only to loopback and requires no external credentials."""
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, content, mime="text/html; charset=utf-8"):
            body = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlsplit(self.path)
            if route.path == "/health":
                return self.respond(200, json.dumps({"status": "ok", "jobs": lib.stats()}), "application/json")
            if route.path != "/":
                return self.respond(404, "Not found", "text/plain")
            term = parse_qs(route.query).get("q", [""])[0][:200]
            rows = lib.search(term) if term else []
            findings = "".join(
                "<article><h3>" + html.escape(x["title"]) + "</h3><p>" +
                html.escape(x["summary"]) + "</p><small>" +
                html.escape(x["url"]) + "</small></article>" for x in rows
            )
            counts = html.escape(json.dumps(lib.stats()))
            page = ("""<!doctype html><html><head><meta charset="utf-8">
<title>SURYDEV Learning Library</title><style>
body{font:16px system-ui;max-width:920px;margin:35px auto;padding:20px;background:#111827;color:#f9fafb}
input{padding:12px;width:65%;border-radius:6px}button{padding:12px}
article{background:#1f2937;padding:16px;margin:12px 0;border-radius:8px}
small{overflow-wrap:anywhere;color:#9ca3af}p{white-space:pre-wrap}
</style></head><body><h1>SURYDEV Learning Library</h1>
<p>Local-only dashboard · Jobs: """ + counts + """</p>
<form action="/" method="get"><input name="q" placeholder="Search saved findings" value="""" +
html.escape(term, quote=True) + """"><button>Search</button></form>""" +
findings + """</body></html>""")
            return self.respond(200, page)

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"SURYDEV dashboard: http://127.0.0.1:{port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()

def work_loop(lib, interval, use_ollama, model):
    if interval < 10:
        raise ValueError("interval must be at least 10 seconds")
    lib.recover()
    print("SURYDEV worker started. Ctrl+C to stop.", flush=True)
    while True:
        result = lib.run_next(use_ollama, model)
        if result:
            print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(interval)

def main():
    ap = argparse.ArgumentParser(description="SURYDEV standalone extensions")
    ap.add_argument("--data", default=str(Path.home() / "SURYADEV-DATA"))
    sub = ap.add_subparsers(dest="command", required=True)
    web = sub.add_parser("dashboard")
    web.add_argument("--port", type=int, default=8769)
    worker = sub.add_parser("worker")
    worker.add_argument("--interval", type=int, default=60)
    worker.add_argument("--no-ollama", action="store_true")
    worker.add_argument("--model", default="qwen3.5:9b")
    imp = sub.add_parser("import-transcript")
    imp.add_argument("file")
    imp.add_argument("--source", default="")
    imp.add_argument("--no-ollama", action="store_true")
    imp.add_argument("--model", default="qwen3.5:9b")
    args = ap.parse_args()
    lib = Library(args.data)
    if args.command == "dashboard":
        serve(lib, args.port)
    elif args.command == "worker":
        work_loop(lib, args.interval, not args.no_ollama, args.model)
    else:
        print(json.dumps(import_transcript(lib, args.file, args.source, not args.no_ollama, args.model), indent=2))

if __name__ == "__main__":
    main()
