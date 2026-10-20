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
from suryadev_resources import snapshot, admission
from suryadev_sources import breakdown
from suryadev_lock import worker_lock
from suryadev_evidence import save_evidence, backup_database, verify_evidence

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
    evidence = save_evidence(lib.root, text, source=source_url or file.as_uri(), kind="transcript")
    digest = evidence["sha256"]
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
            "INSERT INTO findings(job_id,url,sha256,title,summary,excerpt,created,summary_method) VALUES (?,?,?,?,?,?,?,?)",
            (cur.lastrowid, reference, digest, title, summary, text[:4000], now,
             'ollama:' + model if use_ollama else 'extractive'))
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
            if route.path == "/api/resources":
                return self.respond(200, json.dumps(snapshot(lib.root)), "application/json")
            if route.path == "/health":
                reader = Library(lib.root)
                try:
                    status = reader.stats()
                finally:
                    reader.db.close()
                return self.respond(200, json.dumps({"status": "ok", "jobs": status}), "application/json")
            if route.path != "/":
                return self.respond(404, "Not found", "text/plain")
            term = parse_qs(route.query).get("q", [""])[0][:200]
            reader = Library(lib.root)
            try:
                counts = reader.stats()
                by_source = breakdown(reader.db)
                jobs = reader.db.execute(
                    "SELECT j.id,j.url,j.status,j.created,j.updated,j.error,"
                    "f.id,f.title,f.summary,f.sha256,f.summary_method "
                    "FROM jobs j LEFT JOIN findings f ON f.job_id=j.id "
                    "ORDER BY j.id DESC LIMIT 100"
                ).fetchall()
                total_findings = reader.db.execute("SELECT count(*) FROM findings").fetchone()[0]
            finally:
                reader.db.close()
            def esc(value):
                return html.escape(str(value or ""), quote=True)
            def stamp(value):
                return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))
            source_cards = "".join(
                '<div class="stat"><strong>' + esc(kind.upper()) + '</strong>' +
                '<div>Queued: ' + esc(data["queued"]) + '</div>' +
                '<div>Processing: ' + esc(data["running"]) + '</div>' +
                '<div>Completed: ' + esc(data["done"]) + '</div>' +
                '<div>Failed: ' + esc(data["failed"]) + '</div>' +
                '<div>Total: ' + esc(data["total"]) + '</div></div>'
                for kind,data in by_source.items()
            )
            cards = []
            for job_id, source, state, created, updated, error, finding_id, title, summary, digest, method in jobs:
                if term and term.casefold() not in (" ".join([str(source),str(title),str(summary),str(state)])).casefold():
                    continue
                status_class = "ok" if state == "done" else ("bad" if state == "failed" else "wait")
                cards.append(
                    '<article><div class="top"><strong>Assignment #' + esc(job_id) +
                    '</strong><span class="' + status_class + '">' + esc(state.upper()) + '</span></div>' +
                    '<div class="meta">Assigned ' + esc(stamp(created)) + ' · Updated ' + esc(stamp(updated)) + '</div>' +
                    '<div><b>Given to learn from:</b> <span class="source">' + esc(source) + '</span></div>' +
                    ('<div><b>Learned:</b> ' + esc(title) + '</div>' if finding_id else '') +
                    ('<div class="meta">Finding #' + esc(finding_id) + ' · Method: ' + esc(method) +
                     ' · Evidence SHA-256: <code>' + esc(digest) + '</code></div>' if finding_id else '') +
                    ('<details><summary>Read learning result</summary><p>' + esc(summary) + '</p></details>' if finding_id else '') +
                    ('<p class="bad">Error: ' + esc(error) + '</p>' if error else '') +
                    '</article>'
                )
            page = (
                '<!doctype html><html><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta http-equiv="refresh" content="30">'
                '<title>SURYADEV Learning Control Room</title>'
                '<style>body{font:15px system-ui;background:#0b1220;color:#e9f0fc;max-width:1100px;margin:25px auto;padding:20px}'
                'h1{margin-bottom:4px}.muted,.meta{color:#9cacc3;font-size:13px}.stats{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}'
                '.stat,article{background:#17243a;border:1px solid #31435e;border-radius:12px;padding:18px}'
                '.stat{min-width:130px;flex:1}.stat strong{font-size:25px;display:block}'
                'form{display:flex;gap:10px;margin-bottom:20px}input{flex:1;min-width:0;padding:12px;background:#0f1c2f;color:white;border:1px solid #435773;border-radius:8px}'
                'button{padding:12px;background:#3c76d3;color:white;border:0;border-radius:8px}article{margin:12px 0;line-height:1.7}'
                '.top{display:flex;justify-content:space-between}.ok{color:#7de3b1}.bad{color:#ff9b9b}.wait{color:#f5c778}'
                '.source,code{overflow-wrap:anywhere}details{margin-top:10px}summary{cursor:pointer;color:#9fc8ff}p{white-space:pre-wrap}'
                '</style></head><body><h1>SURYADEV · Learning Control Room</h1>'
                '<p class="muted">Local-only · Read-only · Auto-refresh every 30 seconds · Most recent 100 assignments</p>'
                '<div class="stats">' +
                ''.join('<div class="stat"><strong>' + esc(counts.get(k,0)) + '</strong>' + esc(k.title()) + '</div>'
                        for k in ('queued','running','done','failed')) +
                '<div class="stat"><strong>' + esc(total_findings) + '</strong>Findings</div></div>'
                '<h2>Sources: YouTube, PDF and websites</h2><div class="stats">' + source_cards + '</div>' +
                '<p class="muted">Counts reflect recorded assignments only. A completed transcript import is not proof of full video coverage or visual viewing. PDF reading is not yet supported by the web worker.</p>' +
                '<h2>Assigned work and learning evidence</h2>'
                '<form action="/" method="get"><input name="q" placeholder="Filter by source, title, status or learned text" value="' +
                esc(term) + '"><button>Filter</button></form>' +
                (''.join(cards) if cards else '<p>No matching assignments.</p>') +
                '<p class="muted">Legacy findings may contain unverified summaries. Completion does not mean Rishi approval.</p></body></html>'
            )
            return self.respond(200, page)

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
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
        allowed, reason, _ = admission(lib.root)
        if not allowed:
            print("SURYADEV paused: " + reason, flush=True)
            time.sleep(interval)
            continue
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
    backup = sub.add_parser("backup")
    backup.add_argument("destination")
    sub.add_parser("verify-evidence")
    args = ap.parse_args()
    if args.command == "backup":
        print(json.dumps(backup_database(args.data, args.destination), indent=2))
        return
    if args.command == "verify-evidence":
        print(json.dumps(verify_evidence(args.data), indent=2))
        return
    lib = Library(args.data)
    if args.command == "dashboard":
        serve(lib, args.port)
    elif args.command == "worker":
        with worker_lock(lib.root):
            work_loop(lib, args.interval, not args.no_ollama, args.model)
    else:
        print(json.dumps(import_transcript(lib, args.file, args.source, not args.no_ollama, args.model), indent=2))

if __name__ == "__main__":
    main()
