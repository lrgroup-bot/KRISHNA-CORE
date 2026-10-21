"""Optional KRISHNA-side reader for SURYADEV's explicitly enabled HTTPS bridge.

TLS certificate SHA-256 is pinned before any bearer secret is sent.
Read-only HTTPS GET only. No automatic enrollment or polling is enabled.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import http.client
import ipaddress
import json
from pathlib import Path
import ssl
from urllib.parse import urlsplit

MAX_REPLY = 262_144


def validate_endpoint(endpoint, expected_fingerprint):
    url = urlsplit(endpoint)
    if (url.scheme != "https" or url.username or url.password or url.fragment
            or not url.hostname):
        raise ValueError("HTTPS endpoint without credentials is required")
    try:
        address = ipaddress.ip_address(url.hostname)
    except ValueError as exc:
        raise ValueError("use an explicit approved private laptop IP") from exc
    if (address.version != 4 or address.is_unspecified
            or not (address.is_private or address.is_loopback)):
        raise ValueError("public, multicast or wildcard endpoints are forbidden")
    if (url.path not in ("/api/live", "/api/operations", "/api/diary", "/api/tasks")
            and not (url.path.startswith("/api/tasks/")
                     and url.path.rsplit("/", 1)[-1].isascii()
                     and url.path.rsplit("/", 1)[-1].isdecimal())):
        raise ValueError("unsupported read-only endpoint")
    value = expected_fingerprint.lower().replace(":", "")
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("TLS certificate SHA-256 must be 64 hex digits")
    return url, value


def read_live(endpoint, fingerprint, token, timeout=8):
    url, expected = validate_endpoint(endpoint, fingerprint)
    if not isinstance(token, str) or len(token) < 48:
        raise ValueError("strong bearer token required")
    # Pinned leaf-certificate identity replaces CA validation for local
    # self-signed Core-approved services. The pin is checked before token use.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    conn = http.client.HTTPSConnection(url.hostname, url.port or 443,
                                       timeout=max(2, min(timeout, 20)), context=context)
    try:
        conn.connect()
        got = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
        if not hmac.compare_digest(got, expected):
            raise ssl.SSLError("SURYADEV TLS pin mismatch; no credentials were sent")
        route = url.path + (("?" + url.query) if url.query else "")
        conn.request("GET", route, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
        })
        response = conn.getresponse()
        body = response.read(MAX_REPLY + 1)
        if len(body) > MAX_REPLY:
            raise ValueError("SURYADEV reply exceeds 256 KiB")
        if response.status != 200:
            raise RuntimeError("SURYADEV bridge rejected read: HTTP " + str(response.status))
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError("unexpected SURYADEV response")
        return result
    finally:
        conn.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Operator-approved read-only SURYADEV Core client")
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--cert-sha256", required=True)
    ap.add_argument("--token-file", required=True)
    args = ap.parse_args(argv)
    from suryadev_bridge import load_token
    token = load_token(args.token_file)
    print(json.dumps(read_live(args.endpoint, args.cert_sha256, token),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
