"""SURYADEV plugin trust registry (read-only foundation; NEVER executes plugin code).

A stable host can discover independently packaged plugins from its own data
folder. Registrations require operator-trusted Ed25519 keys plus a signed
manifest and SHA-256-pinned payload. This module does NOT load/execute any
third-party Python or grant source permissions; a separate sandboxed plugin
host and lifecycle/update protocol are required before enabling execution.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re

SCHEMA = "suryadev.plugin.v1"
HOST_API = 1
MAX_PLUGINS = 40
MAX_MANIFEST_BYTES = 8192
MAX_PLUGIN_BYTES = 32 * 1024 * 1024
NAME = re.compile(r"[a-z][a-z0-9_-]{1,63}\Z")
TYPES = {"web", "video", "pdf", "book", "model", "vision", "connector"}


def _read_limited(path: Path, ceiling: int) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError("plugin file missing or is a symbolic link")
    if path.stat().st_size > ceiling:
        raise ValueError("plugin file exceeds size limit")
    return path.read_bytes()


def verify_manifest(folder: Path, keys: Path) -> dict:
    """Validate metadata and immutable payload; does not import plugin modules."""
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("plugin directory must not be linked")
    m = json.loads(_read_limited(folder / "manifest.json", MAX_MANIFEST_BYTES))
    required = {"schema","plugin_id","api_version","kind","entrypoint",
                "sha256","key_id","signature"}
    if not isinstance(m,dict) or set(m) != required:
        raise ValueError("plugin manifest fields mismatch")
    if m["schema"] != SCHEMA or type(m["api_version"]) is not int or m["api_version"] != HOST_API:
        raise ValueError("unsupported plugin API version")
    if any(not isinstance(m[k],str) or not NAME.fullmatch(m[k])
           for k in ("plugin_id","key_id")):
        raise ValueError("invalid plugin ID or signer key ID")
    if m["plugin_id"] != folder.name:
        raise ValueError("plugin ID differs from installation directory")
    if m["kind"] not in TYPES or not isinstance(m["entrypoint"],str):
        raise ValueError("unsupported plugin capability or entrypoint")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}\.py",m["entrypoint"]):
        raise ValueError("entrypoint must be one top-level .py filename")
    if not isinstance(m["sha256"],str) or not re.fullmatch(r"[a-f0-9]{64}",m["sha256"]):
        raise ValueError("invalid pinned payload digest")
    entry = folder / m["entrypoint"]
    digest = hashlib.sha256(_read_limited(entry, MAX_PLUGIN_BYTES)).hexdigest()
    if digest != m["sha256"]:
        raise ValueError("plugin executable contents changed")
    # No implicit trust-on-first-use. The operator must install a verified
    # 32-byte Ed25519 public key under trust/keys/<key_id>.pub.
    if keys.is_symlink():
        raise ValueError("linked trust directory not permitted")
    key_file = keys / (m["key_id"] + ".pub")
    raw_key = _read_limited(key_file, 128)
    try:
        public_key = bytes.fromhex(raw_key.decode("ascii").strip())
        signature = base64.b64decode(m["signature"], validate=True)
    except (ValueError,UnicodeError) as exc:
        raise ValueError("plugin signature/key encoding invalid") from exc
    if len(public_key) != 32 or len(signature) != 64:
        raise ValueError("invalid Ed25519 verification material")
    signed = {k:m[k] for k in sorted(required - {"signature"})}
    message = json.dumps(signed,sort_keys=True,separators=(",",":"),
                         ensure_ascii=False).encode("utf-8")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise RuntimeError("Ed25519 verification unavailable; no plugin accepted") from exc
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature,message)
    except ValueError as exc:
        raise ValueError("invalid Ed25519 public key") from exc
    except Exception as exc:
        # InvalidSignature is raised by cryptography; fail closed without
        # leaking sensitive signer data into the dashboard.
        raise ValueError("plugin signer verification failed") from exc
    return {"plugin_id":m["plugin_id"], "kind":m["kind"],
            "api_version":HOST_API,"sha256":digest,
            "trusted":True,"execution_enabled":False}


def plugin_registry(data_root: Path) -> dict:
    """Inspect up to forty plugins, recording exact validation failures."""
    root = Path(data_root).resolve()
    plugins = root / "plugins"
    keys = root / "plugin-trust" / "keys"
    if not plugins.exists():
        return {"schema":"suryadev.plugin-registry.v1","plugins":[],
                "rejected":[],"execution_enabled":False}
    if not plugins.is_dir() or plugins.is_symlink():
        raise ValueError("invalid plugin root")
    folders = sorted(plugins.iterdir(),key=lambda f:f.name)
    if len(folders) > MAX_PLUGINS:
        raise ValueError("plugin directory count exceeds safety limit")
    approved, rejected = [], []
    for folder in folders:
        try:
            approved.append(verify_manifest(folder,keys))
        except (OSError, ValueError, RuntimeError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            rejected.append({"plugin_id":folder.name[:64],
                             "reason":str(exc)[:140]})
    return {"schema":"suryadev.plugin-registry.v1","plugins":approved,
            "rejected":rejected,"execution_enabled":False}
