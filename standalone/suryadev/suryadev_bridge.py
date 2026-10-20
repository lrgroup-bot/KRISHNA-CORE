"""Opt-in, read-only SURYADEV HTTPS telemetry bridge for approved Core readers.

Never enabled by installation or by the localhost dashboard. Requires explicit
TLS certificate, private IPv4 bind address, allowed reader IPs, and secret file.
Successful API reads are NOT Core enrollment or Rishi acceptance.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import ipaddress
import json
from pathlib import Path
import ssl
import time
from urllib.parse import parse_qs, urlsplit

from suryadev import Library
from suryadev_liveops import operations_snapshot, atomic_json, READER_FILE
from suryadev_task_details import list_tasks, task_detail, diary_day, diary_days
from suryadev_resources import snapshot
from suryadev_sources import breakdown

MAX_QUERY = 2048


def private_address(value):
    try:
        addr = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError("an explicit private or loopback IP address is required") from exc
    if addr.version != 4 or not (addr.is_private or addr.is_loopback):
        raise ValueError("public and wildcard bind/reader addresses are forbidden")
    if addr.is_unspecified or addr.is_multicast:
        raise ValueError("wildcard or multicast addresses are forbidden")
    return str(addr)


def load_token(filename):
    path = Path(filename).expanduser().resolve(strict=True)
    token = path.read_text(encoding="ascii").strip()
    if len(token) < 48 or len(token) > 256 or not token.isascii() or not token.isprintable():
        raise ValueError("token file must hold one private printable secret of 48-256 characters")
    return token


def authorized(header, token):
    if not isinstance(header, str) or not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[7:].encode("utf-8"), token.encode("utf-8"))


def create_bridge(root, *, bind, port, cert, key, token, allowed_ips):
    """Create a TLS-only API server, explicitly operator controlled."""
    bind = private_address(bind)
    allowed_ips = frozenset(private_address(addr) for addr in allowed_ips)
    if not allowed_ips:
        raise ValueError("specify an allowed Core reader IP")
    if not 1 <= int(port) <= 65535:
        raise ValueError("invalid port")
    if len(token) < 48:
        raise ValueError("strong secret required")
    if not Path(cert).is_file() or not Path(key).is_file():
        raise ValueError("TLS certificate and key files are required")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(cert), keyfile=str(key))

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, payload, *, challenge=False):
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if challenge:
                self.send_header("WWW-Authenticate", 'Bearer realm="SURYADEV"')
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            if self.client_address[0] not in allowed_ips:
                return self.respond(403, {"error": "client address not approved"})
            if not authorized(self.headers.get("Authorization"), token):
                return self.respond(401, {"error": "authentication required"}, challenge=True)
            if len(self.path) > MAX_QUERY:
                return self.respond(414, {"error": "query too long"})
            route = urlsplit(self.path)
            args = parse_qs(route.query)
            lib = Library(root)
            try:
                if route.path == "/api/operations":
                    result = operations_snapshot(lib.db, root)
                elif route.path == "/api/live":
                    status = lib.stats()
                    result = {
                        "timestamp": time.time(), "status": status,
                        "total": sum(status.values()),
                        "sources": breakdown(lib.db),
                        "findings": lib.db.execute("SELECT count(*) FROM findings").fetchone()[0],
                        "resources": snapshot(root),
                    }
                elif route.path == "/api/diary":
                    day = args.get("date", [""])[0]
                    result = diary_day(lib.db, day) if day else {"days": diary_days(lib.db, limit=365)}
                elif route.path == "/api/tasks":
                    result = list_tasks(
                        lib.db,
                        offset=int(args.get("offset", ["0"])[0]),
                        limit=int(args.get("limit", ["25"])[0]),
                        q=args.get("q", [""])[0], kind=args.get("kind", [""])[0],
                        status=args.get("status", [""])[0],
                        day=args.get("date", [""])[0],
                    )
                elif route.path.startswith("/api/tasks/"):
                    raw_id = route.path.split("/")[-1]
                    if not raw_id.isascii() or not raw_id.isdecimal() or len(raw_id) > 12:
                        raise ValueError("invalid task ID")
                    result = task_detail(lib.db, root, int(raw_id))
                    if result is None:
                        return self.respond(404, {"error": "task not found"})
                else:
                    return self.respond(404, {"error": "not found"})
            except (ValueError, OverflowError):
                return self.respond(400, {"error": "invalid request"})
            finally:
                lib.db.close()
            # Receipt records an authorized reader, NOT verified KRISHNA identity.
            atomic_json(root, READER_FILE, {
                "type": "authenticated_tls_read",
                "last_read_at": time.time(),
                "reader_ip": self.client_address[0],
            })
            return self.respond(200, result)

        def do_POST(self):
            return self.respond(405, {"error": "read-only HTTPS interface"})

        def do_PUT(self):
            return self.respond(405, {"error": "read-only HTTPS interface"})

        def do_DELETE(self):
            return self.respond(405, {"error": "read-only HTTPS interface"})

        def log_message(self, fmt, *args):
            # Do not log bearer tokens, paths, or IPs to console.
            return

    server = ThreadingHTTPServer((bind, int(port)), Handler)
    server.daemon_threads = True
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def main(argv=None):
    ap = argparse.ArgumentParser(description="Opt-in SURYADEV authenticated HTTPS read-only bridge")
    ap.add_argument("--data", required=True)
    ap.add_argument("--bind", default="127.0.0.1", help="explicit private laptop IPv4; never 0.0.0.0")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--cert", required=True, help="TLS cert, pinned separately by Core")
    ap.add_argument("--key", required=True, help="private TLS key")
    ap.add_argument("--token-file", required=True, help="owner-controlled secret, never included on CLI")
    ap.add_argument("--allow-ip", required=True, action="append", help="Core reader IPv4 address")
    args = ap.parse_args(argv)
    token = load_token(args.token_file)
    server = create_bridge(args.data, bind=args.bind, port=args.port,
                           cert=args.cert, key=args.key, token=token,
                           allowed_ips=args.allow_ip)
    print("SURYADEV read-only HTTPS bridge: active on approved private interface.", flush=True)
    print("Enrollment NOT verified; configure client-side TLS pin and bearer token.", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
