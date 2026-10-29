"""Explicit, fail-closed KRISHNA Core identity pinning for SURYADEV.

Discovery never authorizes commands or data transfer. Operator pins an expected
host and identity token after checking Core locally; only matching health data
is accepted. This is NOT a replacement for authenticated enrollment.
"""
from __future__ import annotations
import argparse
import hashlib
import hmac
import json
from pathlib import Path
from suryadev_discovery import discover, probe

def fingerprint(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def verify_candidate(candidate, *, expected_host, expected_identity):
    if not candidate or candidate.get("host") != expected_host:
        return False
    health = candidate.get("health")
    if not isinstance(health, dict):
        return False
    identity = health.get("instance_id")
    return isinstance(identity, str) and bool(identity) and hmac.compare_digest(
        fingerprint(identity), fingerprint(expected_identity))

def main(argv=None):
    ap = argparse.ArgumentParser(description="Explicit Core candidate identity check")
    ap.add_argument("--host", required=True, help="Operator-confirmed local Core IP")
    ap.add_argument("--instance-id", required=True, help="Instance ID verified directly on Core")
    args = ap.parse_args(argv)
    candidate = probe(args.host)
    ok = verify_candidate(candidate, expected_host=args.host, expected_identity=args.instance_id)
    print(json.dumps({"verified_candidate": ok, "host": args.host,
                      "paired": False, "message": "Identity check only; no enrollment or command channel."}))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
