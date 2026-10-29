"""LAN discovery of KRISHNA Core, without implicit trust or enrollment.

Only probes candidate hosts on the current local /24 and never sends credentials.
Pairing must be completed through a verified Core enrollment endpoint separately.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import json
import socket
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import URLError

PORT = 8766

class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def local_ipv4():
    """Best-effort interface IP, no external traffic is sent."""
    ips = set()
    try:
        for record in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = ipaddress.ip_address(record[4][0])
            if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                ips.add(str(ip))
    except OSError:
        pass
    return sorted(ips)

def candidates(ips):
    hosts = set()
    for address in ips:
        ip = ipaddress.ip_address(address)
        if not ip.is_private or ip.is_loopback or ip.is_link_local:
            continue
        network = ipaddress.ip_network(f"{ip}/24", strict=False)
        hosts.update(str(host) for host in network.hosts())
        hosts.discard(str(ip))
    return sorted(hosts, key=lambda x: tuple(map(int, x.split("."))))

def probe(host, timeout=0.35):
    ip = ipaddress.ip_address(host)
    if not ip.is_private or ip.is_loopback or ip.is_link_local:
        return None
    url = f"http://{ip}:{PORT}/health"
    opener = build_opener(ProxyHandler({}), RejectRedirect())
    try:
        with opener.open(Request(url, headers={"User-Agent": "SuryadevDiscovery/1.0"}), timeout=timeout) as response:
            if response.status != 200 or int(response.headers.get("Content-Length", "0")) > 8192:
                return None
            payload = response.read(8193)
            if len(payload) > 8192:
                return None
            data = json.loads(payload)
            if not isinstance(data, dict):
                return None
            # A health endpoint alone is NOT authentication or proof of identity.
            return {"host": str(ip), "port": PORT, "health": data, "trusted": False}
    except (OSError, URLError, ValueError, json.JSONDecodeError, TypeError):
        return None

def discover(ips=None, max_workers=32):
    addresses = local_ipv4() if ips is None else ips
    found = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(probe, host) for host in candidates(addresses)]
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                found.append(result)
    return sorted(found, key=lambda x: tuple(map(int, x["host"].split("."))))

def main(argv=None):
    parser = argparse.ArgumentParser(description="Find possible KRISHNA Core nodes on local /24 networks")
    parser.add_argument("--local-ip", action="append", help="Local interface IPv4; default auto-detect")
    args = parser.parse_args(argv)
    print(json.dumps({"candidates": discover(args.local_ip),
                      "note": "Discovery only. Identity verification and explicit pairing are required before joining."},
                     indent=2))

if __name__ == "__main__":
    main()
