"""Local-only operator configuration and untrusted Core health diagnosis.

An IP/port is a *candidate*, not a trusted Core identity or pairing.
Only an explicit authenticated enrollment may authorize knowledge exchange.
"""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from suryadev_liveops import atomic_json

SETTINGS_FILE = "operator-settings.json"
DEFAULT_CLEANUP_HOURS = 0


class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_core(ip, port=8766):
    """Reject hostnames, URLs, wildcard and public IPs. No arbitrary HTTP targets."""
    if not isinstance(ip, str) or not ip.strip():
        raise ValueError("Enter the KRISHNA Core private IPv4 address")
    try:
        parsed = ipaddress.ip_address(ip.strip())
    except ValueError as exc:
        raise ValueError("Enter a single numeric IPv4 address, without http:// or a path") from exc
    if (parsed.version != 4 or not (parsed.is_private or parsed.is_loopback)
            or parsed.is_unspecified or parsed.is_multicast or parsed.is_link_local):
        raise ValueError("Only explicit private/loopback IPv4 addresses are allowed")
    if isinstance(port, bool):
        raise ValueError("Invalid Core port")
    try:
        port = int(port)
    except (TypeError, ValueError) as exc:
        raise ValueError("Core port must be a number") from exc
    if not 1 <= port <= 65535:
        raise ValueError("Core port must be between 1 and 65535")
    return str(parsed), port


def default_settings():
    return {
        "server": {"ip": "", "port": 8766},
        "cleanup": {"enabled": True, "retention_hours": DEFAULT_CLEANUP_HOURS},
        "pending_data_root": "",
    }


def read_settings(root):
    result = default_settings()
    path = Path(root).expanduser().resolve() / SETTINGS_FILE
    try:
        if not path.is_file() or path.stat().st_size > 8_192:
            return result
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return result
    if not isinstance(saved, dict):
        return result
    server = saved.get("server")
    if isinstance(server, dict):
        try:
            result["server"] = dict(zip(("ip", "port"), validate_core(
                server.get("ip"), server.get("port", 8766))))
        except ValueError:
            pass
    cleanup = saved.get("cleanup")
    if isinstance(cleanup, dict):
        hours = cleanup.get("retention_hours", DEFAULT_CLEANUP_HOURS)
        if isinstance(hours, int) and 0 <= hours <= 168:
            result["cleanup"]["retention_hours"] = hours
        result["cleanup"]["enabled"] = cleanup.get("enabled") is True
    pending = saved.get("pending_data_root")
    if isinstance(pending, str) and len(pending) < 1024:
        result["pending_data_root"] = pending
    return result


def write_settings(root, settings):
    atomic_json(root, SETTINGS_FILE, settings)


def save_core(root, ip, port=8766):
    ip, port = validate_core(ip, port)
    settings = read_settings(root)
    settings["server"] = {"ip": ip, "port": port}
    write_settings(root, settings)
    return {"server": settings["server"], "paired": False, "identity_verified": False,
            "message": "Saved Core candidate. Diagnosis checks connectivity only; no pairing."}


def diagnose_core(ip, port=8766, *, timeout=2.5):
    ip, port = validate_core(ip, port)
    result = {
        "ip": ip, "port": port, "checked_at": time.time(),
        "tcp_open": False, "health_reachable": False,
        "health_status": None, "reported_instance_id": None,
        "paired": False, "identity_verified": False,
        "authenticated": False,
        "message": "Not checked",
    }
    # TCP test only, no changes or authentication credentials ever sent.
    try:
        with socket.create_connection((ip, port), timeout=max(.2, min(timeout, 5.0))):
            result["tcp_open"] = True
    except OSError as exc:
        result["message"] = "Core TCP port is unreachable: " + type(exc).__name__
        return result
    url = f"http://{ip}:{port}/health"
    opener = build_opener(ProxyHandler({}), RejectRedirect())
    try:
        with opener.open(Request(url, headers={"Accept": "application/json",
                                                 "User-Agent": "SURYADEV-Diagnose/1.0"}),
                         timeout=max(.2, min(timeout, 5.0))) as response:
            result["health_status"] = response.status
            if response.status != 200:
                result["message"] = "Port open, but health endpoint did not return HTTP 200"
                return result
            raw = response.read(8193)
            if len(raw) > 8192:
                result["message"] = "Health reply exceeded 8 KB"
                return result
            health = json.loads(raw)
            if not isinstance(health, dict):
                result["message"] = "Health reply was not a JSON object"
                return result
            result["health_reachable"] = True
            reported = health.get("instance_id")
            if isinstance(reported, str) and 0 < len(reported) < 120:
                result["reported_instance_id"] = reported
            result["message"] = ("Health endpoint reachable. This is NOT authenticated identity "
                                 "or approved pairing; connection LEDs remain unpaired.")
    except HTTPError as exc:
        result["health_status"] = exc.code
        result["message"] = f"Core health returned HTTP {exc.code}"
    except (URLError, OSError, ValueError, TypeError) as exc:
        result["message"] = "Could not validate Core health: " + type(exc).__name__
    return result
