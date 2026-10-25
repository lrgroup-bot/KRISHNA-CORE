"""Owner-approved SURYADEV zero-code pairing with the existing KRISHNA Core.

Request uses only the SHA-256 of a locally generated token over pinned HTTPS.
Approval is performed on the KRISHNA PC, never by the laptop. Activation
verifies the paired token over that same pinned HTTPS before creating the
live fleet configuration. No source plans or research ledgers are touched.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import time
from urllib.parse import urlsplit

from suryadev_krishna_mission import load_config

PENDING = "core-pairing-pending.json"
CONFIG = "core-mission-connection.json"
TOKEN = "core-paired-device-token.txt"
MAX_RESPONSE = 16384


def _endpoint(origin, fingerprint):
    parsed = urlsplit(str(origin))
    if (parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/")
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Owner must specify only a plain private-IP HTTPS origin")
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise ValueError("Use a verified private IPv4 address, not a DNS name") from exc
    if ip.version != 4 or not (ip.is_private or ip.is_loopback) or ip.is_unspecified:
        raise ValueError("KRISHNA must have an explicitly verified private IPv4 address")
    digest = str(fingerprint).lower().replace(":", "")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Verified TLS certificate SHA-256 fingerprint required")
    return parsed, digest


def pinned_request(origin, fingerprint, method, route, *, payload=None, device="", token=""):
    parsed, expected = _endpoint(origin, fingerprint)
    if (method, route) not in (("POST", "/api/mobile/pair/request"),
                               ("GET", "/api/suryadev/device/status")):
        raise ValueError("Unsupported pairing operation")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # owner-verified leaf SHA-256 is the trust anchor
    conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443,
                                       timeout=12, context=context)
    try:
        conn.connect()
        actual = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
        if not hmac.compare_digest(actual, expected):
            raise ssl.SSLError("KRISHNA TLS leaf certificate pin mismatch; no data sent")
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if device and token:
            headers["X-Krishna-Device"] = device
            headers["Authorization"] = "Device " + token
        conn.request(method, route, body=body, headers=headers)
        reply = conn.getresponse()
        raw = reply.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("KRISHNA pairing response is oversized")
        answer = json.loads(raw)
        if not isinstance(answer, dict):
            raise ValueError("KRISHNA pairing response must be an object")
        return reply.status, answer
    finally:
        conn.close()


def _private_file(path, value):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)
        if os.name == "nt":
            # Do not accept inherited Everyone/Users access to a device token.
            account = getpass.getuser()
            if not account or any(c in account for c in "\r\n:"):
                raise RuntimeError("Cannot identify Windows owner of token file")
            run = subprocess.run(["icacls", str(path), "/inheritance:r",
                                  "/grant:r", account + ":R"],
                                 capture_output=True, text=True, timeout=10)
            if run.returncode != 0:
                raise RuntimeError("Could not restrict Windows credential-file ACL")
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def request_pairing(root, origin, fingerprint, device_id, *, sender=pinned_request):
    root = Path(root).expanduser().resolve()
    parsed, digest = _endpoint(origin, fingerprint)
    if (not isinstance(device_id, str) or not device_id.startswith("suryadev-")
            or not 10 <= len(device_id) <= 120
            or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in device_id)):
        raise ValueError("Use a unique lowercase suryadev- device ID")
    root.mkdir(parents=True, exist_ok=True)
    if any((root / name).exists() for name in (PENDING, CONFIG, TOKEN)):
        raise FileExistsError("Pairing files exist; refusing to replace credentials or approval")
    token = secrets.token_urlsafe(48)
    token_path = root / TOKEN
    _private_file(token_path, token + "\n")
    try:
        status, result = sender(origin, digest, "POST", "/api/mobile/pair/request",
                                payload={"device_id": device_id,
                                         "name": "SURYADEV " + device_id,
                                         "credential_sha256": hashlib.sha256(token.encode()).hexdigest()})
        if (status != 200 or not isinstance(result.get("request_id"), str)
                or result.get("device_id") != device_id
                or not isinstance(result.get("expires_at"), int)):
            raise RuntimeError("KRISHNA did not issue a valid pending pairing request")
        info = {"schema": "suryadev.zero-code-pairing-pending.v1",
                "endpoint": origin.rstrip("/"),
                "cert_sha256": digest, "device_id": device_id,
                "request_id": result["request_id"], "expires_at": result["expires_at"],
                "token_file": str(token_path),
                "created_at": int(time.time())}
        _private_file(root / PENDING, json.dumps(info, indent=2) + "\n")
    except BaseException:
        token_path.unlink(missing_ok=True)
        raise
    return {"state": "owner_approval_required", "device_id": device_id,
            "request_id": result["request_id"], "expires_at": result["expires_at"],
            "note": "Approve this request on KRISHNA PC loopback. No credential sent or pairing claimed."}


def activate_pairing(root, *, sender=pinned_request):
    root = Path(root).expanduser().resolve()
    pending_file = root / PENDING
    if (root / CONFIG).exists():
        raise FileExistsError("Live KRISHNA connection configuration already exists")
    info = json.loads(pending_file.read_text(encoding="utf-8"))
    if info.get("schema") != "suryadev.zero-code-pairing-pending.v1":
        raise ValueError("Unrecognized pairing request")
    token_path = (root / TOKEN).resolve()
    if info.get("token_file") != str(token_path) or not token_path.is_file():
        raise ValueError("Pairing token file mismatch")
    token = token_path.read_text(encoding="ascii").strip()
    if not 48 <= len(token) <= 256:
        raise ValueError("Invalid pairing token")
    status, answer = sender(info["endpoint"], info["cert_sha256"], "GET",
                            "/api/suryadev/device/status",
                            device=info["device_id"], token=token)
    if not (status == 200 or
            (status == 404 and answer.get("error") ==
             "Suryadev node has not sent a heartbeat yet")):
        raise PermissionError("KRISHNA has not accepted this device credential")
    configuration = {
        "schema": "suryadev.krishna-mission-connection.v1",
        "endpoint": info["endpoint"],
        "cert_sha256": info["cert_sha256"],
        "device_id": info["device_id"],
        "token_file": str(token_path)}
    # Reuse the production loader before publishing a configuration that
    # causes the existing node to begin Core mission polling.
    candidate = root / "core-pairing-validated.tmp"
    _private_file(candidate, json.dumps(configuration))
    try:
        validated = load_config(candidate)
        if validated["device_id"] != info["device_id"]:
            raise RuntimeError("Credential validation returned unexpected identity")
        os.replace(candidate, root / CONFIG)
        pending_file.unlink(missing_ok=True)
    finally:
        candidate.unlink(missing_ok=True)
    return {"state": "paired_configuration_active",
            "device_id": info["device_id"], "live_network_heartbeat_verified": False,
            "knowledge_accepted": False, "rishi_exam_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zero-code HTTPS-pinned SURYADEV/Core pairing")
    parser.add_argument("--data", required=True, type=Path)
    actions = parser.add_subparsers(dest="action", required=True)
    request = actions.add_parser("request")
    request.add_argument("--endpoint", required=True)
    request.add_argument("--cert-sha256", required=True)
    request.add_argument("--device-id", required=True)
    actions.add_parser("activate")
    args = parser.parse_args(argv)
    result = (request_pairing(args.data, args.endpoint, args.cert_sha256, args.device_id)
              if args.action == "request" else activate_pairing(args.data))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
