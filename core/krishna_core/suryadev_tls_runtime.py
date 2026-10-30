"""Opt-in native HTTPS endpoint for owner-paired SURYADEV fleet devices.

Runs in the Core process with direct TCP client addresses, not a reverse
proxy that would turn remote authorization into trusted loopback traffic.
Plain HTTP port 8766 is unchanged. Bind only to an explicitly selected
private or loopback IPv4 interface, and restrict HTTPS routes.
"""
from __future__ import annotations

import ipaddress
import os
from pathlib import Path
import ssl
import threading
from urllib.parse import urlsplit

from .http_server_runtime import KrishnaThreadingHTTPServer

_ALLOWED = {
    ("POST", "/api/mobile/pair/request"),
    ("GET", "/api/suryadev/device/status"),
    ("POST", "/api/suryadev/device/heartbeat"),
    ("POST", "/api/suryadev/learning-plan/request"),
    ("POST", "/api/suryadev/mission/request"),
    ("POST", "/api/suryadev/mission/ack"),
    ("POST", "/api/suryadev/fleet/claim"),
    ("POST", "/api/suryadev/fleet/renew"),
    ("POST", "/api/suryadev/fleet/complete"),
    ("POST", "/api/suryadev/learning-bundle"),
}


def allowed_method_path(method, request_path):
    return (method, urlsplit(str(request_path)).path) in _ALLOWED


def checked_private_bind(value):
    try:
        ip = ipaddress.ip_address(str(value))
    except ValueError as exc:
        raise ValueError("Select an actual private IPv4 NIC, not a hostname") from exc
    if ip.version != 4 or ip.is_unspecified or not (ip.is_private or ip.is_loopback):
        raise ValueError("Suryadev TLS binding must be a specific private IPv4 or loopback IP")
    return str(ip)


def tls_settings(environ=None):
    env = os.environ if environ is None else environ
    cert = str(env.get("KRISHNA_SURYADEV_TLS_CERT_FILE") or "").strip()
    key = str(env.get("KRISHNA_SURYADEV_TLS_KEY_FILE") or "").strip()
    if not cert and not key:
        return None
    if not cert or not key:
        raise ValueError("Both SURYADEV TLS certificate and private key are required")
    bind = checked_private_bind(str(env.get("KRISHNA_SURYADEV_TLS_BIND_IP") or "127.0.0.1"))
    try:
        port = int(env.get("KRISHNA_SURYADEV_TLS_PORT") or "8443")
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid SURYADEV HTTPS port") from exc
    if port < 1024 or port > 65535:
        raise ValueError("SURYADEV HTTPS port must be between 1024 and 65535")
    cert_path, key_path = Path(cert).expanduser().resolve(strict=True), Path(key).expanduser().resolve(strict=True)
    if not cert_path.is_file() or not key_path.is_file():
        raise ValueError("SURYADEV TLS certificate/key must be regular files")
    return bind, port, cert_path, key_path


def start_suryadev_tls_listener(base_handler, environ=None):
    settings = tls_settings(environ)
    if settings is None:
        return None, None
    bind, port, certificate, private_key = settings

    class RestrictedTLSHandler(base_handler):
        def _authorize(self):
            if not allowed_method_path(self.command, self.path):
                self._json(403, {"error": "SURYADEV HTTPS listener exposes only device pairing and fleet API"})
                return False
            return super()._authorize()

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(certificate), keyfile=str(private_key))
    server = KrishnaThreadingHTTPServer((bind, port), RestrictedTLSHandler)
    try:
        server.socket = context.wrap_socket(server.socket, server_side=True)
    except BaseException:
        server.server_close()
        raise
    thread = threading.Thread(target=server.serve_forever, name="krishna-suryadev-https",
                              daemon=True)
    thread.start()
    return server, thread
