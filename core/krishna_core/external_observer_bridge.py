from __future__ import annotations

"""Trusted transport boundary for SURYDEV/CHANDRADEV external workers.

LAN transport reuses the trusted-node registry endpoint metadata. USB transport is
an offline JSON packet handoff with SHA-256 integrity. Neither transport treats a
packet as trusted merely because it exists; the sending node must already be owner-
approved in NodeRegistry.
"""

from pathlib import Path
import hashlib
import json
import os
import time
import uuid


class ExternalObserverBridge:
    VERSION = "external-observer-bridge-v1"
    AGENTS = {"suryadev", "chandradev"}
    TRANSPORTS = {"lan", "usb"}

    def __init__(self, state_root, node_registry, *, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.outbox = self.root / "outbox"
        self.inbox = self.root / "inbox"
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.node_registry = node_registry
        self.memory = memory

    @staticmethod
    def _canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")

    @classmethod
    def _sha256(cls, value):
        return hashlib.sha256(cls._canonical(value)).hexdigest()

    def _trusted_node(self, node_id):
        nodes = self.node_registry.load()
        node = nodes.get(str(node_id))
        if not node:
            raise KeyError(node_id)
        if not node.trusted:
            raise PermissionError("external observer node is not trusted")
        return node

    def envelope(self, *, agent, node_id, payload, transport="lan", direction="to_worker"):
        agent = str(agent or "").strip().lower()
        transport = str(transport or "").strip().lower()
        if agent not in self.AGENTS:
            raise ValueError("unsupported external observer agent")
        if transport not in self.TRANSPORTS:
            raise ValueError("transport must be lan or usb")
        node = self._trusted_node(node_id)
        required = f"{agent}.worker"
        if required not in set(node.capabilities or []):
            raise PermissionError(f"trusted node lacks required capability: {required}")
        payload = dict(payload or {})
        env = {
            "schema": "krishna.external-observer-envelope.v1",
            "envelope_id": "EXT-" + uuid.uuid4().hex[:20],
            "agent": agent,
            "node_id": node.id,
            "node_fingerprint": node.fingerprint,
            "transport": transport,
            "direction": str(direction or "to_worker"),
            "created_at": time.time(),
            "payload": payload,
            "payload_sha256": self._sha256(payload),
            "policy": {
                "node_trust_source": "owner-approved NodeRegistry",
                "credentials_in_packet": False,
                "raw_media_to_krishna": False,
            },
        }
        return env

    def validate(self, envelope):
        env = dict(envelope or {})
        if env.get("schema") != "krishna.external-observer-envelope.v1":
            raise ValueError("invalid external observer envelope schema")
        agent = str(env.get("agent") or "").lower()
        if agent not in self.AGENTS:
            raise ValueError("invalid external observer agent")
        node = self._trusted_node(env.get("node_id"))
        if str(env.get("node_fingerprint") or "") != str(node.fingerprint):
            raise PermissionError("node fingerprint mismatch")
        actual = self._sha256(dict(env.get("payload") or {}))
        if actual != str(env.get("payload_sha256") or ""):
            raise ValueError("external observer packet integrity check failed")
        return {
            "valid": True,
            "agent": agent,
            "node_id": node.id,
            "transport": env.get("transport"),
            "payload_sha256": actual,
        }

    def lan_target(self, *, agent, node_id):
        agent = str(agent or "").lower()
        node = self._trusted_node(node_id)
        if f"{agent}.worker" not in set(node.capabilities or []):
            raise PermissionError(f"node is not configured for {agent}")
        if not node.endpoint:
            return {
                "ready": False,
                "reason": "trusted node has no LAN endpoint configured",
                "node_id": node.id,
            }
        return {
            "ready": True,
            "node_id": node.id,
            "endpoint": node.endpoint,
            "agent": agent,
            "transport": "lan",
            "security": "use existing KRISHNA trusted-node authenticated transport; endpoint discovery alone grants no trust",
        }

    def export_usb(self, envelope, destination):
        self.validate(envelope)
        destination = Path(destination).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / f"{envelope['envelope_id']}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {
            "file": path.name,
            "sha256": digest,
            "envelope_id": envelope["envelope_id"],
            "agent": envelope["agent"],
            "created_at": time.time(),
        }
        manifest_path = destination / f"{envelope['envelope_id']}.sha256.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {
            "transport": "usb",
            "packet": str(path),
            "manifest": str(manifest_path),
            "sha256": digest,
        }

    def import_usb(self, packet_path, manifest_path=None):
        packet_path = Path(packet_path).resolve()
        if not packet_path.is_file():
            raise FileNotFoundError(str(packet_path))
        raw = packet_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if manifest_path:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            if digest != str(manifest.get("sha256") or ""):
                raise ValueError("USB packet file hash mismatch")
        env = json.loads(raw.decode("utf-8"))
        check = self.validate(env)
        copied = self.inbox / packet_path.name
        copied.write_bytes(raw)
        if self.memory:
            self.memory.audit(
                "external_observer_usb",
                "validated",
                f"{check['agent']}:{check['node_id']}:{digest[:16]}",
            )
        return {"envelope": env, "validation": check, "stored_copy": str(copied)}

    def status(self):
        return {
            "component": "KRISHNA External Observer Bridge",
            "version": self.VERSION,
            "agents": sorted(self.AGENTS),
            "transports": sorted(self.TRANSPORTS),
            "trust": "owner-approved NodeRegistry fingerprint",
            "usb_integrity": "SHA-256 manifest + trusted node fingerprint",
            "lan_authority": "existing trusted-node authenticated transport",
            "ready": True,
        }
