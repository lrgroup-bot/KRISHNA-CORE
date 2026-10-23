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
import secrets
import sqlite3
from pathlib import Path
import re
import threading
import time
from urllib.parse import parse_qs, urlsplit, quote

from suryadev import Library, summarize
from suryadev_resources import snapshot, admission
from suryadev_parallel import AdaptiveResearchWorkers
from suryadev_continuity import ContinuityFeeder
from suryadev_mission_renewal import renewal_tick
from suryadev_krishna_mission import MissionRelay
from suryadev_fleet_client import FleetClient
from suryadev_book_continuity import BookContinuity, BookEvidenceCollector, may_study_books
from suryadev_book_handoff import BookHandoff
from suryadev_sources import breakdown
from suryadev_task_details import list_tasks, task_detail, diary_days, diary_day
from suryadev_liveops import operations_snapshot, worker_note
from suryadev_operator_api import settings_snapshot, handle_operator_action
from mimetypes import guess_type
from suryadev_lock import worker_lock
from suryadev_video_review import VideoReview
from suryadev_dashboard_worker import DashboardWorkerControl
from suryadev_evidence import save_evidence, backup_database, verify_evidence

MAX_TRANSCRIPT = 2_000_000
MAX_REQUEST = 4096
UI_VERSION = "2026-10-23-v7.1-mission-first"

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

def _send_http_response(handler, status, mime, body):
    """Ignore a client closing its socket; never conceal unrelated server failures.

    Rapid dashboard refreshes can abort requests while the server writes a
    completed response (Windows WinError 10053/10054). These disconnects
    are not research failures and should not print a server traceback.
    """
    try:
        handler.send_response(status)
        handler.send_header("Content-Type", mime)
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("Content-Security-Policy", "default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'none'")
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        return False
    return True


class DashboardReader:
    """Read-only dashboard view, no schema migrations or write locks per poll.

    The owning Library creates/migrates the DB before serve() starts. This
    connection NEVER changes journal mode or initializes tables.
    """
    def __init__(self, root):
        dbfile = Path(root).expanduser().resolve() / "suryadev.sqlite3"
        if not dbfile.is_file():
            raise FileNotFoundError("SURYADEV database is not initialized")
        uri = "file:" + quote(dbfile.as_posix(), safe="/:") + "?mode=ro"
        self.db = sqlite3.connect(uri, uri=True, timeout=10)
        self.db.execute("PRAGMA query_only=ON")
        self.db.execute("PRAGMA busy_timeout=10000")

    def stats(self):
        return dict(self.db.execute("SELECT status,count(*) FROM jobs GROUP BY status").fetchall())


def serve(lib, port=8769):
    """Dashboard binds only to loopback; state changes require same-origin CSRF."""
    csrf_token = secrets.token_urlsafe(32)
    settings_lock = threading.Lock()
    video_review = VideoReview(lib.root, Path(__file__).resolve().parent)
    worker_control = DashboardWorkerControl(lib.root, Path(__file__).resolve().parent)
    video_review.start_auto_scheduler(worker_control)
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, content, mime="text/html; charset=utf-8"):
            return _send_http_response(self, status, mime, content.encode("utf-8"))

        def do_GET(self):
            route = urlsplit(self.path)
            if route.path == "/api/learning/control":
                return self.respond(200, json.dumps(worker_control.snapshot()), "application/json")
            if route.path == "/api/video/review":
                return self.respond(200, json.dumps(video_review.snapshot()), "application/json")
            if route.path == "/api/operator/settings":
                payload = settings_snapshot(lib.root)
                payload["csrf_token"] = csrf_token
                return self.respond(200, json.dumps(payload), "application/json")
            if route.path == "/api/ui-version":
                return self.respond(
                    200, json.dumps({"version": UI_VERSION,
                                     "has_repo_r39_video_review": True,
                                     "has_connection_leds": True,
                                     "has_date_picker": True,
                                     "has_server_settings": True,
                                     "has_storage_settings": True,
                                     "has_garudanetra": True,
                                     "has_adaptive_parallel": True,
                                     "has_offline_worker_diagnostics": True,
                                     "has_dashboard_hardware_preview": True,
                                     "has_youtube_cooldown": True,
                                     "has_youtube_language_selection": True,
                                     "has_approved_source_continuity": True,
                                     "has_official_publisher_caption_recovery": True,
                                     "has_core_mission_relay_opt_in": True,
                                     "has_six_hour_renewal_request": True,
                                     "has_bounded_large_rss": True,
                                     "has_per_source_processing_timing": True,
                                     "has_xml_aware_feed_safety": True,
                                     "has_opt_in_deep_pdf": True,
                                     "has_opt_in_deep_web": True,
                                     "has_local_full_frame_video_audit": True,
                                     "has_local_book_line_by_line_reader": True,
                                     "has_idle_book_scheduler": True,
                                     "has_book_visual_ocr_audit": True,
                                     "has_book_core_candidate_handoff": True,
                                     "has_read_only_book_dashboard": True,
                                     "has_books_in_garudanetra": True,
                                     "has_books_in_source_coverage": False,
                                     "has_books_in_laptop_health": False,
                                     "has_single_date_filter": True,
                                     "has_static_video_review": True,
                                     "has_unified_frontend": True,
                                     "has_dashboard_worker_controls": True}),
                    "application/json")
            if route.path in ("/", "/dashboard.css", "/dashboard.js",
                              "/dashboard-settings.css", "/dashboard-settings.js",
                              "/dashboard-garudanetra.css", "/dashboard-garudanetra.js",
                              "/dashboard-books.css", "/dashboard-books.js",
                              "/dashboard-video.css", "/dashboard-video.js",
                              "/dashboard-api.js", "/dashboard-learning.js"):
                filename = {"/": "dashboard.html", "/dashboard.css": "dashboard.css",
                            "/dashboard.js": "dashboard.js",
                            "/dashboard-settings.css": "dashboard-settings.css",
                            "/dashboard-settings.js": "dashboard-settings.js",
                            "/dashboard-garudanetra.css": "dashboard-garudanetra.css",
                            "/dashboard-garudanetra.js": "dashboard-garudanetra.js",
                            "/dashboard-books.css": "dashboard-books.css",
                            "/dashboard-books.js": "dashboard-books.js",
                            "/dashboard-video.css": "dashboard-video.css",
                            "/dashboard-video.js": "dashboard-video.js",
                            "/dashboard-api.js": "dashboard-api.js",
                            "/dashboard-learning.js": "dashboard-learning.js"}[route.path]
                content = (Path(__file__).resolve().parent / filename).read_text(encoding="utf-8")
                mime = "text/html; charset=utf-8" if route.path == "/" else (
                    "text/css; charset=utf-8" if filename.endswith(".css") else "application/javascript; charset=utf-8")
                return self.respond(200, content, mime)
            if route.path == "/api/book-search":
                from suryadev_book_reader import BookLedger
                options=parse_qs(route.query)
                key=options.get("q",[""])[0]
                if not (Path(lib.root)/"book-learning.sqlite3").is_file():
                    return self.respond(200,json.dumps({
                        "query":key,"matches":[],"returned":0,"has_more":False
                    }),"application/json")
                ledger=BookLedger(lib.root)
                try:
                    result=ledger.search(key,limit=20)
                except ValueError as exc:
                    return self.respond(400,json.dumps({"error":str(exc)[:160]}),
                                       "application/json")
                except (OSError,RuntimeError):
                    return self.respond(503,json.dumps({
                        "error":"Book evidence unavailable or integrity mismatch"}),
                        "application/json")
                finally:
                    ledger.close()
                return self.respond(200,json.dumps(result,ensure_ascii=False),
                                    "application/json")
            if route.path == "/api/books":
                from suryadev_book_reader import BookLedger
                path = Path(lib.root) / "book-learning.sqlite3"
                if not path.is_file():
                    return self.respond(200, json.dumps({"books":[],
                        "note":"No local books registered yet"}),"application/json")
                reader = BookLedger(lib.root)
                try:
                    payload=reader.status()
                except (OSError,ValueError,RuntimeError) as exc:
                    return self.respond(503,json.dumps({
                        "error":"Local book ledger unavailable: "+type(exc).__name__}),
                        "application/json")
                finally:
                    reader.close()
                return self.respond(200,json.dumps(payload),"application/json")
            if route.path == "/api/operations":
                reader = DashboardReader(lib.root)
                try:
                    payload = operations_snapshot(reader.db, lib.root)
                finally:
                    reader.db.close()
                return self.respond(200, json.dumps(payload), "application/json")
            if route.path == "/api/diary":
                args = parse_qs(route.query)
                try:
                    reader = DashboardReader(lib.root)
                    try:
                        day_value = args.get("date", [""])[0]
                        payload = diary_day(reader.db, day_value) if day_value else {
                            "days": diary_days(reader.db, limit=365)}
                    finally:
                        reader.db.close()
                except (ValueError, OverflowError):
                    return self.respond(400, json.dumps({"error": "Invalid date; use YYYY-MM-DD"}), "application/json")
                return self.respond(200, json.dumps(payload), "application/json")
            if route.path == "/api/tasks":
                args = parse_qs(route.query)
                try:
                    reader = DashboardReader(lib.root)
                    try:
                        payload = list_tasks(
                            reader.db, offset=int(args.get("offset", ["0"])[0]),
                            limit=int(args.get("limit", ["25"])[0]),
                            q=args.get("q", [""])[0],
                            status=args.get("status", [""])[0],
                            kind=args.get("kind", [""])[0],
                            day=args.get("date", [""])[0])
                    finally:
                        reader.db.close()
                except (ValueError, OverflowError):
                    return self.respond(400, json.dumps({"error": "Invalid task filter"}), "application/json")
                return self.respond(200, json.dumps(payload), "application/json")
            if route.path.startswith("/api/tasks/"):
                part = route.path[len("/api/tasks/"):]
                if not part.isascii() or not part.isdecimal() or len(part) > 12:
                    return self.respond(400, json.dumps({"error": "Invalid task ID"}), "application/json")
                reader = DashboardReader(lib.root)
                try:
                    payload = task_detail(reader.db, lib.root, int(part))
                finally:
                    reader.db.close()
                if payload is None:
                    return self.respond(404, json.dumps({"error": "Task not found"}), "application/json")
                return self.respond(200, json.dumps(payload), "application/json")
            if route.path == "/api/live":
                reader = DashboardReader(lib.root)
                try:
                    status = reader.stats()
                    sources = breakdown(reader.db)
                    findings = reader.db.execute("SELECT count(*) FROM findings").fetchone()[0]
                    days = diary_days(reader.db, limit=365)
                    jobs = reader.db.execute(
                        "SELECT j.id,j.url,j.status,j.created,j.error,f.title,f.summary,f.summary_method "
                        "FROM jobs j LEFT JOIN findings f ON f.job_id=j.id "
                        "ORDER BY j.id DESC LIMIT 40"
                    ).fetchall()
                finally:
                    reader.db.close()
                from suryadev_book_dashboard import book_learning_snapshot
                books = book_learning_snapshot(lib.root)
                payload = {"time": time.time(), "status": status, "sources": sources,
                           "book_learning": books,
                           "total": sum(status.values()), "findings": findings,
                           "diary": days,
                           "jobs": [{"id": i, "url": url, "status": state, "created": created,
                                     "error": error, "title": title or "", "summary": summary or "",
                                     "method": method or ""}
                                    for i,url,state,created,error,title,summary,method in jobs],
                           "resources": snapshot(lib.root)}
                return self.respond(200, json.dumps(payload), "application/json")
            if route.path == "/api/resources":
                return self.respond(200, json.dumps(snapshot(lib.root)), "application/json")
            if route.path == "/health":
                reader = DashboardReader(lib.root)
                try:
                    status = reader.stats()
                finally:
                    reader.db.close()
                return self.respond(200, json.dumps({"status": "ok", "jobs": status}), "application/json")
            if route.path != "/":
                return self.respond(404, "Not found", "text/plain")
            term = parse_qs(route.query).get("q", [""])[0][:200]
            reader = DashboardReader(lib.root)
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
                '<style>:root{color-scheme:dark;--bg:#090f1d;--panel:#111c30;--edge:#26364f;--ink:#e8effb;--muted:#9db0c9;--accent:#70a8ff}'
                '*{box-sizing:border-box}body{font:15px/1.55 system-ui,Segoe UI,sans-serif;background:radial-gradient(ellipse at 90% 0%,#16294d 0%,var(--bg) 44%);color:var(--ink);max-width:1320px;margin:0 auto;padding:32px 26px}'
                'h1{font-size:clamp(27px,4vw,43px);letter-spacing:-1.4px;margin:0 0 6px}h2{font-size:18px;margin:34px 0 14px;letter-spacing:-.3px}.muted,.meta{color:var(--muted);font-size:13px}'
                '.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:14px;margin:22px 0}.stat,article{background:linear-gradient(145deg,#17243a,#101a2c);border:1px solid var(--edge);border-radius:16px;padding:19px;box-shadow:0 8px 24px #0002}'
                '.stat{min-height:100px;color:var(--muted);font-size:13px}.stat strong{font-size:30px;line-height:1.4;display:block;color:var(--ink);font-variant-numeric:tabular-nums}.stat div{font-size:13px;line-height:1.8}'
                'form{display:flex;gap:10px;margin-bottom:22px}input{flex:1;min-width:0;padding:13px 15px;background:#101b2e;color:white;border:1px solid #405572;border-radius:10px;outline-offset:3px}input:focus{border-color:var(--accent)}'
                'button{padding:12px 22px;background:#3878dd;color:white;border:0;border-radius:10px;font-weight:650;cursor:pointer}button:hover{background:#5090f4}article{margin:12px 0;line-height:1.7}'
                '.top{display:flex;justify-content:space-between;gap:12px;align-items:center}.top strong{font-size:16px}.ok,.bad,.wait{font-size:12px;font-weight:750;letter-spacing:.06em}.ok{color:#6ee7b7}.bad{color:#fca5a5}.wait{color:#fcd34d}'
                '.source,code{overflow-wrap:anywhere}code{color:#a8caff}details{margin-top:14px;padding:12px;background:#0c1728;border-radius:10px}summary{cursor:pointer;color:#a9cfff;font-weight:650}p{white-space:pre-wrap}article>div{margin-top:5px}'
                'body:before{content:"●  LOCAL LEARNING NODE";display:block;color:#7dc3ff;font-size:11px;font-weight:800;letter-spacing:.2em;margin-bottom:15px}'
                '@media(max-width:650px){body{padding:20px 14px}.stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.stat,article{padding:14px}form{flex-wrap:wrap}button{width:100%}.top{align-items:flex-start}}'
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

        def do_POST(self):
            # Mutating configuration is never exposed through the opt-in Core
            # read-only bridge. Only local browser requests with per-start CSRF
            # token and exact Origin/Host matching may change settings.
            origin = f"http://127.0.0.1:{port}"
            if (self.client_address[0] != "127.0.0.1"
                    or self.headers.get("Host") != f"127.0.0.1:{port}"
                    or self.headers.get("Origin") != origin
                    or self.headers.get("X-SURYADEV-CSRF") != csrf_token):
                return self.respond(403, json.dumps({"error": "Same-origin authorization required"}),
                                    "application/json")
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                return self.respond(415, json.dumps({"error": "JSON body required"}),
                                    "application/json")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 2 or length > 4096:
                return self.respond(413, json.dumps({"error": "Invalid request body length"}),
                                    "application/json")
            route = urlsplit(self.path)
            if not route.path.startswith("/api/operator/"):
                return self.respond(404, json.dumps({"error": "Unknown operation"}),
                                    "application/json")
            try:
                body = json.loads(self.rfile.read(length))
                with settings_lock:
                    if route.path == "/api/operator/learning/start":
                        outcome = worker_control.start(model=body.get("model", "qwen3.5:2b"))
                    elif route.path == "/api/operator/learning/stop":
                        outcome = worker_control.stop()
                    elif route.path == "/api/operator/video/approve-source":
                        outcome = video_review.approve_source(body.get("url"))
                    elif route.path == "/api/operator/video/auto":
                        outcome = video_review.set_auto(body.get("enabled"))
                    elif route.path == "/api/operator/video/import":
                        outcome = video_review.import_job(body.get("job"))
                    elif route.path == "/api/operator/video/run":
                        outcome = video_review.run_job(
                            body.get("job_id"), body.get("approved"), body.get("expected_sha256"))
                    else:
                        outcome = handle_operator_action(lib.root, route.path, body)
                return self.respond(200, json.dumps(outcome), "application/json")
            except (ValueError, TypeError) as exc:
                return self.respond(400, json.dumps({"error": str(exc)[:230]}),
                                    "application/json")
            except (RuntimeError, FileExistsError) as exc:
                return self.respond(409, json.dumps({"error": str(exc)[:230]}),
                                    "application/json")
            except OSError as exc:
                return self.respond(500, json.dumps({"error": "Storage or OS error: " +
                                                          type(exc).__name__}),
                                    "application/json")

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    print(f"SURYDEV dashboard: http://127.0.0.1:{port}/", flush=True)
    try:
        server.serve_forever()
    finally:
        video_review.stop_auto_scheduler()
        worker_control.close()
        server.server_close()

def work_loop(lib, interval, use_ollama, model, *,
              plan_path=None, refill_minutes=5, core_mission_config=None,
              book_plan_path=None, sync_book_handoff=False,
              book_visual_model=None, book_collect_plan_path=None, fleet_mode=False):
    if book_collect_plan_path and (book_plan_path or sync_book_handoff or book_visual_model):
        raise ValueError('Collector-only books cannot run model-reading, visual AI or Core candidate handoff')
    if interval < 10:
        raise ValueError("interval must be at least 10 seconds")
    if not 1 <= refill_minutes <= 360:
        raise ValueError("refill-minutes must be 1..360")
    if fleet_mode and not core_mission_config:
        raise ValueError("fleet mode requires a pinned paired --core-mission-config")
    if core_mission_config and not plan_path:
        raise ValueError("Core mission relay requires an explicit approved --plan")
    feeder = (ContinuityFeeder(lib.root, plan_path,
               refill_seconds=refill_minutes * 60) if plan_path else None)
    relay = (MissionRelay(lib.root, plan_path, core_mission_config)
             if core_mission_config and not fleet_mode else None)
    fleet = (FleetClient(lib.root, plan_path, core_mission_config)
             if fleet_mode else None)
    if sync_book_handoff and not (book_plan_path and core_mission_config):
        raise ValueError("Book BRAHMAGYAN handoff requires approved --book-plan and paired --core-mission-config")
    if book_visual_model and not book_plan_path:
        raise ValueError("Automatic book visuals require --book-plan")
    books = (BookContinuity(lib.root, book_plan_path, model=model,
                            use_ollama=use_ollama,vision_model=book_visual_model)
             if book_plan_path else None)
    collect_books = (BookEvidenceCollector(lib.root, book_collect_plan_path)
                     if book_collect_plan_path else None)
    handoff = (BookHandoff(lib.root,core_mission_config) if sync_book_handoff else None)
    lib.recover()
    print("SURYADEV Garudanetra adaptive worker started. Ctrl+C to stop.", flush=True)
    worker_note(lib.root, "starting", interval, "Adaptive source lanes starting")
    try:
        with AdaptiveResearchWorkers(lib.root, use_ollama=use_ollama,
                                     model=model, check_seconds=interval) as adaptive:
            while True:
                if feeder:
                    result = feeder.tick(lib, youtube_blocked=(
                        adaptive.youtube_access["state"] == "rate_limited"))
                    if result is not None:
                        print(json.dumps({"continuity":result}, ensure_ascii=False),flush=True)
                update = adaptive.pump()
                for result in update["finished"]:
                    print(json.dumps(result, ensure_ascii=False), flush=True)
                if feeder:
                    # Prepare a six-hour request when eligible research runs low.
                    # This is a LOCAL OUTBOX, not a claimed KRISHNA delivery.
                    renewal = renewal_tick(lib, youtube_blocked=(
                        adaptive.youtube_access["state"] == "rate_limited"))
                    if relay:
                        result = relay.tick(lib, renewal)
                        if result is not None:
                            print(json.dumps({"krishna_mission":result}, ensure_ascii=False), flush=True)
                if fleet:
                    fleet_event = fleet.tick(lib)
                    if fleet_event and fleet_event.get("state") != "no_approved_work":
                        print(json.dumps({"fleet": fleet_event}, ensure_ascii=False), flush=True)
                if books:
                    # Low-priority background books never compete with queued
                    # web/PDF/YouTube jobs or bypass one-worker ownership.
                    pending = (url for (url,) in lib.db.execute(
                        "SELECT url FROM jobs WHERE status IN ('queued','running')"))
                    idle = may_study_books(
                        update["capacity"],pending,
                        youtube_rate_limited=(
                            adaptive.youtube_access["state"]=="rate_limited"))
                    if idle:
                        with adaptive.summary_lock:
                            book_result = books.tick(available=True)
                        if book_result:
                            print(json.dumps({"book_learning":book_result}, ensure_ascii=False), flush=True)
                if collect_books:
                    # Index one owner-approved source without Ollama, including
                    # when source research remains queued. Admission is measured;
                    # original local book bytes and separate model journals persist.
                    capacity=update["capacity"]
                    available=bool(capacity.get("safe") and
                                   capacity.get("active_total",0)<capacity.get("max_total",0))
                    collected=collect_books.tick(available=available)
                    if collected:
                        print(json.dumps({"book_evidence_collection":collected},
                                         ensure_ascii=False),flush=True)
                if handoff and books:
                    approved_ids = ["book-"+b["sha256"] for b in books.plan["books"]]
                    book_ack = handoff.tick(approved_book_ids=approved_ids,
                                            require_visual_complete=bool(book_visual_model))
                    if book_ack:
                        print(json.dumps({"brahmagyan_candidate_receipt":book_ack},
                                         ensure_ascii=False), flush=True)
                # One worker can both discover approved sources and process them;
                # no second feeder process or duplicate worker is required.
                wait = 2 if update["capacity"]["active_total"] else interval
                if feeder:
                    wait = min(wait, max(0.1, feeder.next_due - time.time()))
                time.sleep(wait)
    finally:
        if feeder:
            feeder.stop()
        worker_note(lib.root, "stopped", interval, "Worker stopped")


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
    worker.add_argument("--plan", default=None,
                        help="Opt-in existing learning-plan.json for continual approved-source refilling")
    worker.add_argument("--refill-minutes", type=int, default=5)
    worker.add_argument("--book-visual-model", default=None,
                        help="Opt into one PDF page/EPUB figure local visual model call per idle book step")
    worker.add_argument("--sync-book-handoff", action="store_true",
                        help="Explicitly authorize pinned paired Core upload of book candidate observations")
    worker.add_argument("--book-plan", default=None,
                        help="Owner-approved SHA-256-pinned local books, learned during idle cycles only")
    worker.add_argument("--book-collect-plan", default=None,
                        help="Owner-approved books INDEXED WITHOUT Ollama or comprehension claims")
    worker.add_argument("--fleet-mode", action="store_true",
                        help="Opt in to owner-paired fleet task claims and evidence receipts")
    worker.add_argument("--core-mission-config", default=None,
                        help="Explicit opt-in TLS-pinned paired KRISHNA mission connection JSON")
    lab = sub.add_parser("analyze-local-video",
                         help="Whole-file frame scan of operator-provided lawful local media, no YouTube requests")
    lab.add_argument("media")
    lab.add_argument("--title", default="")
    lab.add_argument("--description-file")
    lab.add_argument("--comments-file")
    lab.add_argument("--transcript-file")
    lab.add_argument("--whisper-model-dir",
                     help="Already downloaded LOCAL faster-whisper model directory")
    lab.add_argument("--vision-model",
                     help="Already installed LOCAL Ollama vision model")
    lab.add_argument("--visual-interval-seconds", type=float, default=1)
    lab.add_argument("--max-visual-frames", type=int, default=300)
    lab.add_argument("--every-frame-vision", action="store_true",
                     help="Attempt model interpretation on EVERY decoded frame; expensive, strict budget")
    lab.add_argument("--source-url", default="",
                     help="Provenance-only approved YouTube video URL; does not download")
    # All book commands share the existing SURYADEV persistent root, but use
    # their own book-reading SQLite ledger and page/line checkpoint journal.
    book_approve = sub.add_parser("book-approve",
                                 help="Explicitly owner-approve and index one local SHA-pinned book")
    book_approve.add_argument("file")
    book_approve.add_argument("--ocr-scanned", action="store_true")
    book_approve.add_argument("--lines-per-step",type=int,default=1)
    book_import = sub.add_parser("book-import", help="Index every line of a local EPUB/PDF/TXT/MD")
    book_import.add_argument("file")
    book_import.add_argument("--title", default=None)
    book_import.add_argument("--ocr-scanned", action="store_true",
                             help="Use local Tesseract OCR only for PDF pages lacking text")
    book_read = sub.add_parser("book-read", help="Resume exact next unread line to the end")
    book_read.add_argument("book_id")
    book_read.add_argument("--model", default="gemma3:4b")
    book_read.add_argument("--no-ollama", action="store_true",
                           help="Record line evidence only, NEVER claim AI learning")
    book_read.add_argument("--lines-per-step", type=int, default=1)
    book_read.add_argument("--max-steps", type=int, default=0,
                           help="0 means continue until every line is processed")
    book_visual = sub.add_parser("book-visuals",
                         help="Resume local full-page PDF or EPUB image vision/OCR audit")
    book_visual.add_argument("book_id")
    book_visual.add_argument("--model", default="gemma3:4b")
    book_visual.add_argument("--max-items", type=int, default=0,
                             help="0 means through the last detected visual; 1 for checkpoint step")
    book_search = sub.add_parser("book-search")
    book_search.add_argument("query")
    book_search.add_argument("--limit", type=int, default=20)
    book_status = sub.add_parser("book-status")
    book_status.add_argument("book_id", nargs="?")
    book_verify = sub.add_parser("book-verify")
    book_verify.add_argument("book_id")
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
    if args.command == "book-visuals":
        from suryadev_book_visuals import BookVisualAuditor
        with worker_lock(args.data):
            auditor = BookVisualAuditor(args.data)
            try:
                result = auditor.run(args.book_id,model=args.model,
                                     max_items=args.max_items)
            finally:
                auditor.close()
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    if args.command == "book-approve":
        from suryadev_book_reader import default_pdf_ocr
        from suryadev_book_continuity import approve_book
        with worker_lock(args.data):
            result=approve_book(args.data,args.file,
                                lines_per_step=args.lines_per_step,
                                ocr=default_pdf_ocr if args.ocr_scanned else None)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return
    if args.command in ("book-import","book-read","book-status","book-verify",
                         "book-search"):
        from suryadev_book_reader import BookLedger, default_pdf_ocr
        if args.command in ("book-import","book-read"):
            # No concurrent mutation of the same learning library.
            with worker_lock(args.data):
                ledger = BookLedger(args.data)
                try:
                    if args.command == "book-import":
                        result = ledger.import_book(
                            args.file, title=args.title,
                            ocr=default_pdf_ocr if args.ocr_scanned else None)
                    else:
                        result = ledger.read(
                            args.book_id, model=args.model,
                            use_ollama=not args.no_ollama,
                            lines_per_step=args.lines_per_step,
                            max_steps=args.max_steps)
                finally:
                    ledger.close()
        else:
            ledger = BookLedger(args.data)
            try:
                result = (ledger.status(args.book_id) if args.command == "book-status"
                          else ledger.search(args.query,limit=args.limit)
                          if args.command == "book-search"
                          else ledger.verify(args.book_id))
            finally:
                ledger.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "analyze-local-video":
        from suryadev_video_lab import video_research
        with worker_lock(args.data):
            result = video_research(
                args.media, args.data, title=args.title,
                description_file=args.description_file,
                comments_file=args.comments_file,
                transcript_file=args.transcript_file,
                whisper_model_dir=args.whisper_model_dir,
                vision_model=args.vision_model,
                visual_interval_seconds=args.visual_interval_seconds,
                max_visual_frames=args.max_visual_frames,
                every_frame_vision=args.every_frame_vision,
                source_url=args.source_url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    lib = Library(args.data)
    if args.command == "dashboard":
        serve(lib, args.port)
    elif args.command == "worker":
        with worker_lock(lib.root):
            work_loop(lib, args.interval, not args.no_ollama, args.model,
                      plan_path=args.plan, refill_minutes=args.refill_minutes,
                      core_mission_config=args.core_mission_config,
                      book_plan_path=args.book_plan,
                      book_collect_plan_path=args.book_collect_plan,
                      sync_book_handoff=args.sync_book_handoff,
                      book_visual_model=args.book_visual_model,
                      fleet_mode=args.fleet_mode)
    else:
        print(json.dumps(import_transcript(lib, args.file, args.source, not args.no_ollama, args.model), indent=2))

if __name__ == "__main__":
    main()
