from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile

from .models import PrivacyFinding, PrivacyRiskClass


_TRACKER_SIGNATURES={
    "google_analytics":("com/google/android/gms/analytics","firebase/analytics"),
    "facebook_sdk":("com/facebook/appevents","com/facebook/analytics"),
    "adjust":("com/adjust/sdk",),
    "appsflyer":("com/appsflyer",),
    "mixpanel":("com/mixpanel",),
    "segment":("com/segment/analytics",),
}


class MobSFAdapter:
    """Optional adapter to an independently running local/owner-approved MobSF service."""

    def __init__(self,endpoint: str|None=None,api_key: str|None=None,timeout: float=30.0):
        self.endpoint=str(endpoint or os.getenv("KRISHNA_MOBSF_URL") or "").strip().rstrip("/")
        self.api_key=str(api_key or os.getenv("KRISHNA_MOBSF_API_KEY") or "")
        self.timeout=float(timeout)

    def status(self) -> dict:
        return {
            "configured":bool(self.endpoint),
            "authenticated":bool(self.api_key),
            "mode":"external_local_service",
            "license_boundary":"MobSF remains an independent GPL service; KRISHNA stores normalized summaries only",
        }

    def scan(self,apk_path: str|Path) -> dict:
        if not self.endpoint:
            return {"status":"unsupported","reason":"MobSF service is not configured"}
        if not self.api_key:
            return {"status":"blocked","reason":"MobSF credential is not configured"}
        target=Path(apk_path)
        if not target.is_file():
            raise FileNotFoundError(str(target))
        parts=urlsplit(self.endpoint)
        if parts.scheme not in {"http","https"}:
            raise ValueError("MobSF endpoint must use http or https")
        if parts.scheme=="http" and parts.hostname not in {"127.0.0.1","localhost","::1"}:
            raise ValueError("non-local MobSF endpoints must use HTTPS")
        # MobSF's API is multipart-based; the adapter deliberately does not reinvent
        # that protocol without a verified service contract. Status remains honest.
        return {
            "status":"configured_not_executed",
            "endpoint":self.endpoint,
            "apk_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
            "reason":"MobSF API upload contract requires runtime integration verification against the configured service",
        }


def _extract_ascii(blob: bytes, min_len: int=6, max_strings: int=20000) -> list[str]:
    pattern=re.compile(rb"[\x20-\x7e]{%d,}"%min_len)
    out=[]
    for match in pattern.finditer(blob):
        try: text=match.group().decode("ascii","ignore")
        except Exception: continue
        out.append(text[:500])
        if len(out)>=max_strings: break
    return out


def _aapt_permissions(apk: Path) -> dict:
    exe=shutil.which("aapt2") or shutil.which("aapt")
    if not exe:
        sdk=os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")
        if sdk:
            build_tools=Path(sdk)/"build-tools"
            candidates=[]
            if build_tools.is_dir():
                for child in build_tools.iterdir():
                    for name in ("aapt2.exe","aapt2","aapt.exe","aapt"):
                        p=child/name
                        if p.is_file():candidates.append(p)
            if candidates:
                candidates.sort(key=lambda p:p.parent.name,reverse=True)
                exe=str(candidates[0])
    if not exe:
        return {"available":False,"permissions":[],"raw_retained":False}
    commands=[
        [exe,"dump","permissions",str(apk)],
        [exe,"dump","badging",str(apk)],
    ]
    text=""
    for cmd in commands:
        try:
            cp=subprocess.run(cmd,capture_output=True,text=True,timeout=20,check=False)
            if cp.returncode==0 and cp.stdout:
                text+="\n"+cp.stdout
        except Exception:
            continue
    permissions=sorted(set(re.findall(r"(?:uses-permission(?:: name=)?['\"]?|permission: )([A-Za-z0-9._]+)",text)))
    return {"available":bool(text),"permissions":permissions,"raw_retained":False}


def basic_apk_privacy_audit(apk_path: str|Path) -> dict:
    apk=Path(apk_path)
    if not apk.is_file():
        raise FileNotFoundError(str(apk))
    if apk.suffix.lower()!=".apk":
        raise ValueError("mobile privacy audit expects an APK")
    sha=hashlib.sha256(apk.read_bytes()).hexdigest()
    findings=[];tracker_hits=[];cleartext_hosts=set();entries=[]
    with zipfile.ZipFile(apk) as z:
        entries=z.namelist()
        dex_names=[x for x in entries if x.lower().endswith(".dex")]
        for name in dex_names[:20]:
            try: strings=_extract_ascii(z.read(name),6,30000)
            except Exception: continue
            low_strings=[x.lower() for x in strings]
            for tracker,needles in _TRACKER_SIGNATURES.items():
                if any(any(n.lower() in s for n in needles) for s in low_strings):
                    tracker_hits.append(tracker)
            for s in strings:
                for m in re.finditer(r"http://([A-Za-z0-9._-]+)",s):
                    host=m.group(1).lower().strip(".")
                    if host not in {"127.0.0.1","localhost"}:
                        cleartext_hosts.add(host)
    aapt=_aapt_permissions(apk)
    tracker_hits=sorted(set(tracker_hits))
    findings.append(PrivacyFinding(
        test="mobile.trackers.static",state="observed",
        summary=f"{len(tracker_hits)} known analytics/tracker SDK signature(s) were observed by a conservative local string scan.",
        risk_class=PrivacyRiskClass.MODERATE_EXPOSURE if tracker_hits else PrivacyRiskClass.LOW_EXPOSURE,
        evidence={"tracker_signatures":tracker_hits,"method":"DEX printable-string signature scan"},
        recommendation="Review each SDK's purpose before release; presence alone is not a maliciousness verdict." if tracker_hits else "",
        limitations=["String scanning can miss obfuscated SDKs and can produce false positives; use MobSF/verified dynamic testing for stronger evidence."],
        source_methodology="Exodus-style methodology independently implemented as a local signature check",
    ))
    findings.append(PrivacyFinding(
        test="mobile.cleartext_urls",state="observed",
        summary=f"{len(cleartext_hosts)} non-loopback cleartext HTTP host(s) were observed in printable APK strings.",
        risk_class=PrivacyRiskClass.MODERATE_EXPOSURE if cleartext_hosts else PrivacyRiskClass.LOW_EXPOSURE,
        evidence={"cleartext_hosts":sorted(cleartext_hosts)[:100]},
        recommendation="Confirm whether any observed cleartext endpoint is reachable/used at runtime and migrate owned traffic to TLS where practical." if cleartext_hosts else "",
        limitations=["String presence does not prove runtime use."],
        source_methodology="KRISHNA Mobile static privacy gate",
    ))
    perms=aapt.get("permissions") or []
    sensitive=[x for x in perms if any(n in x.upper() for n in (
        "CAMERA","RECORD_AUDIO","ACCESS_FINE_LOCATION","ACCESS_COARSE_LOCATION","READ_CONTACTS",
        "READ_SMS","READ_CALL_LOG","BLUETOOTH_CONNECT","POST_NOTIFICATIONS",
    ))]
    findings.append(PrivacyFinding(
        test="mobile.permissions",state="observed" if aapt.get("available") else "unsupported",
        summary=f"{len(perms)} manifest permission(s) observed; {len(sensitive)} privacy-sensitive permission category match(es)." if aapt.get("available") else "AAPT was unavailable, so manifest permissions were not decoded.",
        risk_class=PrivacyRiskClass.MODERATE_EXPOSURE if sensitive else (PrivacyRiskClass.LOW_EXPOSURE if aapt.get("available") else PrivacyRiskClass.UNSUPPORTED),
        evidence={"permissions":perms,"privacy_sensitive":sensitive,"aapt_available":aapt.get("available")},
        recommendation="Keep only permissions required by KRISHNA Mobile's conversation/voice/file workflow and compare against the previous release baseline." if sensitive else "",
        source_methodology="KRISHNA Mobile permission-surface audit",
    ))
    return {
        "apk":str(apk.resolve()),
        "apk_sha256":sha,
        "entries":len(entries),
        "findings":[x.as_dict() for x in findings],
        "mobsf_required_for_full_gate":True,
        "dynamic_test_required_for_full_gate":True,
        "policy":"Static findings are release evidence, not proof of malicious behavior.",
    }
