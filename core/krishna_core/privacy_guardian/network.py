from __future__ import annotations

from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import ipaddress
import json
import os
import ssl
import time

from .models import PrivacyFinding, PrivacyRiskClass


class NetworkPrivacyProbeClient:
    """Optional client for a KRISHNA-controlled external observation service.

    No third-party endpoint is used by default. The configured service must expose
    minimal JSON endpoints such as /ip, /headers and /tls.
    """

    def __init__(self,base_url: str|None=None,timeout: float=8.0):
        self.base_url=str(base_url or os.getenv("KRISHNA_PRIVACY_PROBE_URL") or "").strip().rstrip("/")
        self.timeout=max(1.0,float(timeout))

    def status(self) -> dict:
        return {
            "configured":bool(self.base_url),
            "base_url":self.base_url if self.base_url else None,
            "policy":"disabled unless explicitly configured; expected to be KRISHNA-controlled and minimal-retention",
        }

    def _get(self,path: str) -> dict:
        if not self.base_url:
            raise RuntimeError("KRISHNA privacy probe service is not configured")
        full=urljoin(self.base_url+"/",path.lstrip("/"))
        parts=urlsplit(full)
        if parts.scheme not in {"https","http"}:
            raise ValueError("privacy probe service must use http or https")
        if parts.scheme=="http" and parts.hostname not in {"127.0.0.1","localhost","::1"}:
            raise ValueError("remote privacy probe service must use HTTPS")
        req=Request(full,headers={
            "User-Agent":"KRISHNA-KABACH-PrivacyGuardian/1",
            "Accept":"application/json",
            "Cache-Control":"no-store",
        })
        with urlopen(req,timeout=self.timeout) as resp:
            raw=resp.read(256_000)
        data=json.loads(raw.decode("utf-8"))
        return data if isinstance(data,dict) else {"value":data}

    def audit(self) -> dict:
        if not self.base_url:
            return {
                "configured":False,"status":"unsupported",
                "findings":[PrivacyFinding(
                    test="network.external_probe",state="unsupported",
                    summary="No KRISHNA-controlled external privacy probe is configured.",
                    risk_class=PrivacyRiskClass.UNSUPPORTED,
                    recommendation="Configure KRISHNA_PRIVACY_PROBE_URL only when an owner-controlled minimal-retention probe service is available.",
                    limitations=["Public IP, DNS-resolver and client-TLS observations require an external vantage point."],
                    source_methodology="KRISHNA minimal external observation service",
                ).as_dict()],
            }
        started=time.perf_counter(); payloads={};errors={}
        for name,path in (("ip","/ip"),("headers","/headers"),("tls","/tls")):
            try: payloads[name]=self._get(path)
            except Exception as exc: errors[name]=f"{type(exc).__name__}: {exc}"
        findings=[]
        ip_data=payloads.get("ip") or {}
        ip_value=ip_data.get("ip") or ip_data.get("address")
        ip_version=None
        if ip_value:
            try: ip_version=ipaddress.ip_address(str(ip_value)).version
            except ValueError: ip_version=None
        findings.append(PrivacyFinding(
            test="network.public_ip",state="observed" if ip_value else ("failed" if "ip" in errors else "unsupported"),
            summary="External probe observed the browser/client public network address." if ip_value else "Public IP observation was unavailable.",
            risk_class=PrivacyRiskClass.LOW_EXPOSURE if ip_value else PrivacyRiskClass.INCONCLUSIVE,
            evidence={"ip":ip_value,"version":ip_version} if ip_value else {"error":errors.get("ip")},
            limitations=["The raw network identifier is sensitive and must be encrypted or redacted in persistent history."],
            source_methodology="KRISHNA minimal external observation service",
            sensitive=True,
        ).as_dict())
        tls=payloads.get("tls") or {}
        findings.append(PrivacyFinding(
            test="network.tls_fingerprint",state="observed" if tls else ("failed" if "tls" in errors else "unsupported"),
            summary="TLS/client-stack characteristics were observed by the configured probe." if tls else "TLS fingerprint observation was unavailable.",
            risk_class=PrivacyRiskClass.MODERATE_EXPOSURE if tls.get("ja4") else PrivacyRiskClass.INCONCLUSIVE,
            evidence={
                "tls_version":tls.get("tls_version"),
                "alpn":tls.get("alpn"),
                "http_version":tls.get("http_version"),
                "ja4":tls.get("ja4"),
                "quic":tls.get("quic"),
            } if tls else {"error":errors.get("tls")},
            recommendation="Treat stable TLS fingerprints as another possible linkability surface; do not assume browser-state changes alter the network stack.",
            source_methodology="JA4/base TLS self-fingerprint methodology",
            sensitive=True,
        ).as_dict())
        headers=payloads.get("headers") or {}
        safe_headers={}
        for k,v in headers.items():
            low=str(k).lower()
            if low in {"authorization","cookie","proxy-authorization","set-cookie"}:
                safe_headers[k]="present" if v else "absent"
            else:
                safe_headers[k]=str(v)[:500]
        findings.append(PrivacyFinding(
            test="network.http_headers",state="observed" if headers else ("failed" if "headers" in errors else "unsupported"),
            summary="Outbound request headers were observed with credential-bearing values suppressed." if headers else "Header observation was unavailable.",
            risk_class=PrivacyRiskClass.LOW_EXPOSURE if headers else PrivacyRiskClass.INCONCLUSIVE,
            evidence={"headers":safe_headers} if headers else {"error":errors.get("headers")},
            source_methodology="BrowserLeaks/HTTP header defensive observation",
        ).as_dict())
        return {
            "configured":True,
            "status":"completed" if payloads else "failed",
            "elapsed_ms":int((time.perf_counter()-started)*1000),
            "findings":findings,
            "errors":errors,
        }


def compare_vpn_consistency(*,http_ip=None,webrtc=None,dns=None,timezone=None,browser_locale=None,
                            system_locale=None,expected_vpn=False) -> dict:
    if not expected_vpn:
        return {
            "classification":"inconclusive",
            "observations":{
                "http_ip_present":bool(http_ip),
                "webrtc_public_candidate":bool((webrtc or {}).get("publicCandidateExposed")),
                "dns_observed":bool(dns),
                "timezone":timezone,"browser_locale":browser_locale,"system_locale":system_locale,
            },
            "note":"No intended VPN/proxy state was supplied; mismatches are observations, not compromise claims.",
        }
    unexpected=[]
    if (webrtc or {}).get("publicCandidateExposed"):
        unexpected.append("webrtc_public_candidate_visible")
    if browser_locale and system_locale and str(browser_locale).split("-")[0].lower()!=str(system_locale).split("-")[0].lower():
        unexpected.append("browser_system_locale_mismatch")
    return {
        "classification":"unexpected" if unexpected else ("expected" if http_ip else "inconclusive"),
        "unexpected":unexpected,
        "observations":{"http_ip_present":bool(http_ip),"dns_observed":bool(dns),"timezone":timezone},
        "note":"Unexpected does not mean the VPN is compromised; it means the tested surfaces differ from the intended privacy configuration.",
    }
