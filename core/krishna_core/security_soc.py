"""Lightweight defensive SOC primitives for KABACH.

Local/authorized telemetry only. This module normalizes events, extracts IOCs,
correlates repeated activity and maps a small set of defensive ATT&CK hints.
It never performs exploitation or active scanning.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib, ipaddress, re, time

_IPV4=re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
_DOMAIN=re.compile(r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b")
_SHA256=re.compile(r"(?i)\b[a-f0-9]{64}\b")

@dataclass(frozen=True,slots=True)
class SecurityEvent:
    timestamp:float
    source:str
    event_type:str
    message:str
    severity:str="info"
    actor:str=""
    target:str=""
    def as_dict(self): return asdict(self)

class DefensiveSOC:
    """Small in-process SOC suitable for KRISHNA's local-first runtime."""
    def __init__(self, window_seconds:int=300, threshold:int=5):
        self.window_seconds=max(30,int(window_seconds))
        self.threshold=max(2,int(threshold))
        self._events=[]

    def normalize(self, raw, source="krishna"):
        if isinstance(raw,SecurityEvent): return raw
        if isinstance(raw,dict):
            return SecurityEvent(
                float(raw.get("timestamp") or raw.get("ts") or time.time()),
                str(raw.get("source") or source),
                str(raw.get("event_type") or raw.get("type") or "generic"),
                str(raw.get("message") or raw.get("msg") or ""),
                str(raw.get("severity") or "info").lower(),
                str(raw.get("actor") or raw.get("user") or ""),
                str(raw.get("target") or raw.get("resource") or ""),
            )
        return SecurityEvent(time.time(),source,"generic",str(raw))

    def extract_iocs(self,text):
        text=str(text or ""); ips=[]
        for candidate in _IPV4.findall(text):
            try:
                ip=ipaddress.ip_address(candidate)
                if not (ip.is_private or ip.is_loopback or ip.is_link_local):
                    ips.append(str(ip))
            except ValueError: pass
        return {"ipv4":sorted(set(ips)),"domains":sorted(set(x.lower() for x in _DOMAIN.findall(text))),
                "sha256":sorted(set(x.lower() for x in _SHA256.findall(text)))}

    def attack_hints(self,event):
        msg=(event.message+" "+event.event_type).lower(); out=[]
        rules=(("failed login","T1110","Brute Force"),("credential","T1555","Credentials from Password Stores"),
               ("powershell","T1059.001","PowerShell"),("scheduled task","T1053.005","Scheduled Task"),
               ("startup","T1547","Boot or Logon Autostart Execution"))
        for needle,tech,name in rules:
            if needle in msg: out.append({"technique":tech,"name":name})
        return out

    def ingest(self,raw,source="krishna"):
        e=self.normalize(raw,source); self._events.append(e)
        cutoff=time.time()-self.window_seconds
        self._events=[x for x in self._events if x.timestamp>=cutoff]
        key=(e.source,e.event_type,e.actor,e.target)
        matches=[x for x in self._events if (x.source,x.event_type,x.actor,x.target)==key]
        anomaly=len(matches)>=self.threshold
        receipt=hashlib.sha256(repr((e.timestamp,key,e.message)).encode()).hexdigest()
        return {"event":e.as_dict(),"iocs":self.extract_iocs(e.message),"attack_hints":self.attack_hints(e),
                "correlation":{"window_seconds":self.window_seconds,"matching_events":len(matches),
                "anomaly":anomaly,"reason":"repetition_threshold" if anomaly else "below_threshold"},"receipt":receipt}

    def status(self):
        return {"mode":"defensive_local_soc","events_in_window":len(self._events),
                "window_seconds":self.window_seconds,"threshold":self.threshold,
                "active_scanning":False,"exploitation":False}
