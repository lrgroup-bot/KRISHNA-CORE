"""Passive Windows inventory for the local owner; never scans or probes devices."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
import subprocess
import threading
import time


# This command is constant and reads Windows' existing IP, route and neighbor
# tables. Do not add ping, discovery traffic or caller-provided command text.
_WINDOWS_SNAPSHOT = r"""
$ErrorActionPreference = 'Stop'
$interfaces = @(Get-NetIPAddress | Select-Object InterfaceIndex,IPAddress,PrefixLength)
$routes = @(Get-NetRoute | Where-Object { $_.DestinationPrefix -in @('0.0.0.0/0','::/0') } | Select-Object InterfaceIndex,NextHop,RouteMetric)
$neighbors = @(Get-NetNeighbor | ForEach-Object { [pscustomobject]@{InterfaceIndex=$_.InterfaceIndex;IPAddress=$_.IPAddress;State=$_.State.ToString()} })
[pscustomobject]@{interfaces=$interfaces;routes=$routes;neighbors=$neighbors} | ConvertTo-Json -Depth 4 -Compress
"""


def _rows(value):
    if isinstance(value, dict):
        return [value]
    return [row for row in value[:512] if isinstance(row, dict)] if isinstance(value, list) else []


def _address(value):
    try:
        address = ipaddress.ip_address(str(value))
    except ValueError:
        return None
    if address.is_loopback or address.is_unspecified or address.is_multicast:
        return None
    if address.version == 4 and (address.is_link_local or address.is_reserved):
        return None
    return address


def _index(value):
    try:
        index = int(value)
        return index if 0 < index < 2**31 else None
    except (ValueError, TypeError, OverflowError):
        return None


def normalize_snapshot(raw):
    """Validate OS data, omit hardware identifiers, and label observation honestly."""
    if not isinstance(raw, dict):
        raise ValueError("invalid inventory document")
    interfaces, devices, seen = [], [], set()
    routes = {}
    for row in _rows(raw.get("routes")):
        index, gateway = _index(row.get("InterfaceIndex")), _address(row.get("NextHop"))
        if index and gateway:
            try:
                metric = max(0, int(row.get("RouteMetric") or 0))
            except (ValueError, TypeError, OverflowError):
                continue
            key = (index, gateway.version)
            if key not in routes or metric < routes[key][0]:
                routes[key] = (metric, str(gateway))
    for row in _rows(raw.get("interfaces")):
        index, address = _index(row.get("InterfaceIndex")), _address(row.get("IPAddress"))
        if index is None or address is None or (index, str(address)) in seen:
            continue
        try:
            prefix = int(row.get("PrefixLength"))
            subnet = str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))
        except (TypeError, ValueError, OverflowError):
            continue
        seen.add((index, str(address)))
        route = routes.get((index, address.version))
        interfaces.append({"name": f"Interface {index}", "interface_index": index, "ip": str(address),
                           "prefix": prefix, "subnet": subnet,
                           "gateway": route[1] if route else None})
    seen.clear()
    own_addresses = {(row["interface_index"], row["ip"].split("%")[0]) for row in interfaces}
    non_devices = set()
    for row in interfaces:
        subnet = ipaddress.ip_network(row["subnet"])
        if subnet.version == 4 and subnet.prefixlen < 31:
            non_devices.update(((row["interface_index"], str(subnet.network_address)),
                                (row["interface_index"], str(subnet.broadcast_address))))
    known_states = {"Reachable", "Stale", "Delay", "Probe", "Permanent"}
    for row in _rows(raw.get("neighbors")):
        index, address = _index(row.get("InterfaceIndex")), _address(row.get("IPAddress"))
        state = str(row.get("State") or "")
        if index is None or address is None or state not in known_states:
            continue
        key = (index, str(address))
        if key in seen or key in non_devices or (index, str(address).split("%")[0]) in own_addresses:
            continue
        seen.add(key)
        # This is a synthetic presentation ID, never a device identity or MAC.
        identifier = hashlib.sha256(f"{index}:{address}".encode()).hexdigest()[:16]
        gateway = any(route[1] == str(address) for key, route in routes.items() if key[0] == index)
        devices.append({"id": identifier, "name": "Default gateway" if gateway else f"Observed neighbor {len(devices) + 1}",
                        "ip": str(address), "status": "observed", "state": state,
                        "interface_index": index,
                        "kind": "gateway" if gateway else "network-neighbor", "type": "network-neighbor",
                        "identity_verified": False, "connectivity_verified": False,
                        "recognition_source": "OS default route" if gateway else "OS neighbor cache",
                        "recognition": "Gateway role inferred from route; make and owner unknown" if gateway else "Device type, make and owner unknown"})
    preferred = next((row for row in interfaces if row["gateway"] and ":" not in row["ip"]),
                     next((row for row in interfaces if row["gateway"]), None))
    return {"interfaces": interfaces, "devices": devices,
            "gateway": preferred["gateway"] if preferred else None,
            "subnet": preferred["subnet"] if preferred else None}


class NetworkInventory:
    """Bounded, cached read-only inventory. Errors never disclose shell output."""
    def __init__(self, *, runner=None, platform=None, clock=None, cache_seconds=30):
        self._runner = runner or subprocess.run
        self._platform = platform or os.name
        self._clock = clock or time.monotonic
        self._cache_seconds = max(1, float(cache_seconds))
        self._lock = threading.Lock()
        self._cached = None
        self._expires_at = 0
        self._previous = None
        self._changes = []
        self._sequence = 0

    def _track_changes(self, result):
        # An absent cache entry is not proof of disconnection. Keep a bounded,
        # session-only observation log; failures never replace the baseline.
        if result["available"]:
            current = {row["id"]: row for row in result["devices"]}
            if self._previous is not None:
                for identifier, row in current.items():
                    if identifier not in self._previous:
                        self._sequence += 1
                        self._changes.append({"sequence": self._sequence,
                            "kind": "newly_observed", "id": identifier, "ip": row["ip"],
                            "at": result["updated_at"], "identity_verified": False})
                for identifier, row in self._previous.items():
                    if identifier not in current:
                        self._sequence += 1
                        self._changes.append({"sequence": self._sequence,
                            "kind": "no_longer_observed", "id": identifier, "ip": row["ip"],
                            "at": result["updated_at"], "identity_verified": False})
            self._previous = current
            self._changes = self._changes[-64:]
        result["changes"] = deepcopy(self._changes)
        result["change_sequence"] = self._sequence
        result["monitoring"] = {"mode": "passive-on-refresh", "cache_seconds": self._cache_seconds,
            "baseline_established": self._previous is not None,
            "scope": "OS neighbor observations only; absence is not disconnection; no automatic trust or hardware test"}

    def status(self):
        with self._lock:
            if self._cached is not None and self._clock() < self._expires_at:
                return deepcopy(self._cached)
            result = {"source": "windows-route-neighbor-cache", "available": False,
                      "updated_at": datetime.now(timezone.utc).isoformat(),
                      "scan_performed": False, "devices_verified": False,
                      "interfaces": [], "devices": [], "gateway": None, "subnet": None,
                      "policy": "Existing Windows observations; device connectivity is unverified"}
            if self._platform != "nt":
                result["error"] = "Windows inventory unavailable on this platform"
            else:
                try:
                    completed = self._runner(
                        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _WINDOWS_SNAPSHOT],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=5, check=True,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    if len(completed.stdout) > 1024 * 1024:
                        raise ValueError("oversized inventory document")
                    result.update(normalize_snapshot(json.loads(completed.stdout.lstrip("\ufeff"))))
                    result["available"] = True
                except (OSError, ValueError, TypeError, subprocess.SubprocessError):
                    result["error"] = "Windows inventory could not be read"
            self._track_changes(result)
            self._cached = result
            self._expires_at = self._clock() + self._cache_seconds
            return deepcopy(result)
