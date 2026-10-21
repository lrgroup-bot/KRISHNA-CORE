"""SURYADEV secure Core enrollment client.

Requires an operator-supplied HTTPS enrollment endpoint and pinned TLS
certificate fingerprint. Never guesses Core API routes or trusts LAN discovery.
"""
from __future__ import annotations
import argparse
import hashlib
import http.client
import json
import ssl
from urllib.parse import urlsplit

def enroll(endpoint, pairing_code, cert_sha256, timeout=8):
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("operator-confirmed HTTPS enrollment URL required")
    if not parsed.path or parsed.path == "/":
        raise ValueError("specific documented enrollment route required")
    expected = cert_sha256.lower().replace(":", "")
    if len(expected) != 64 or any(x not in "0123456789abcdef" for x in expected):
        raise ValueError("TLS certificate SHA-256 fingerprint must be 64 hex characters")
    if not pairing_code or len(pairing_code) > 256:
        raise ValueError("one-time pairing code required")
    port = parsed.port or 443
    context = ssl.create_default_context()
    conn = http.client.HTTPSConnection(parsed.hostname, port, timeout=timeout, context=context)
    try:
        conn.connect()
        actual = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
        if actual != expected:
            raise ssl.SSLError("Core certificate pin mismatch; pairing aborted")
        path = parsed.path + (("?" + parsed.query) if parsed.query else "")
        payload = json.dumps({"pairing_code": pairing_code, "agent": "suryadev"}).encode()
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json",
            "Accept": "application/json", "Content-Length": str(len(payload))})
        response = conn.getresponse()
        body = response.read(16385)
        if len(body) > 16384:
            raise ValueError("enrollment response too large")
        if response.status != 200:
            raise RuntimeError(f"enrollment rejected: HTTP {response.status}")
        result = json.loads(body)
        if not isinstance(result, dict) or result.get("paired") is not True:
            raise RuntimeError("server did not confirm enrollment")
        # Do not log credentials, tokens or raw server response.
        return {"paired": True, "server": parsed.hostname,
                "note": "Server confirmation received; token storage and command channel not enabled"}
    finally:
        conn.close()

def main(argv=None):
    ap = argparse.ArgumentParser(description="Operator-controlled TLS-pinned Core enrollment")
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--cert-sha256", required=True)
    args = ap.parse_args(argv)
    import getpass
    code = getpass.getpass("Core one-time pairing code: ")
    print(json.dumps(enroll(args.endpoint, code, args.cert_sha256)))

if __name__ == "__main__":
    main()
