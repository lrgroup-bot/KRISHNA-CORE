from __future__ import annotations

import json
import socket
import threading
import time


DISCOVERY_MAGIC = b"KRISHNA_DISCOVER_V1"
DISCOVERY_PORT = 8767


def discovery_payload(http_port: int) -> bytes:
    return json.dumps({
        "service": "KRISHNA_CORE",
        "version": 1,
        "port": int(http_port),
        "pairing": "client-hash-zero-code",
        "network": "lan-only",
    }, separators=(",", ":")).encode("utf-8")


class LanDiscoveryService:
    """Small LAN-only UDP responder for zero-code KRISHNA Mobile discovery.

    The responder never sends credentials or host state. The phone uses the source
    address of the UDP reply as the Core host, then normal HTTP pairing/auth applies.
    """

    def __init__(self, http_port: int, discovery_port: int = DISCOVERY_PORT, bind_host: str = "0.0.0.0"):
        self.http_port = int(http_port)
        self.discovery_port = int(discovery_port)
        self.bind_host = str(bind_host)
        self._stop = threading.Event()
        self._thread = None
        self.last_error = None
        self.requests = 0
        self.started_at = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return self.status()
        self._stop.clear()
        self.last_error = None
        self._thread = threading.Thread(target=self._loop, name="krishna-lan-discovery", daemon=True)
        self._thread.start()
        self.started_at = time.time()
        return self.status()

    def stop(self):
        self._stop.set()
        # Wake recvfrom on platforms where socket timeout has not fired yet.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(b"STOP", ("127.0.0.1", self.discovery_port))
        except OSError:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        return self.status()

    def _loop(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.bind_host, self.discovery_port))
                s.settimeout(1.0)
                while not self._stop.is_set():
                    try:
                        data, addr = s.recvfrom(1024)
                    except socket.timeout:
                        continue
                    if data != DISCOVERY_MAGIC:
                        continue
                    self.requests += 1
                    s.sendto(discovery_payload(self.http_port), addr)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self._stop.set()

    def status(self):
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "http_port": self.http_port,
            "discovery_port": self.discovery_port,
            "requests": self.requests,
            "started_at": self.started_at,
            "last_error": self.last_error,
            "policy": "LAN discovery reveals only service metadata; normal device pairing/auth is still required",
        }
