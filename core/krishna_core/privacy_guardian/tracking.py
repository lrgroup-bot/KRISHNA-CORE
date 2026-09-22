from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import json
import re


_TRACKING_PARAMS={
    "utm_source","utm_medium","utm_campaign","utm_content","utm_term",
    "fbclid","gclid","dclid","msclkid","yclid","mc_cid","mc_eid","vero_id",
}
_TRACKING_PREFIXES=("utm_","hsa_","_hs","hs_")
_HUBSPOT_EXACT={"__hstc","__hssc","__hssrc","hsCtaTracking"}
_FUNCTIONAL_HINTS={
    "id","page","q","query","search","sort","filter","lang","locale","tab","view",
    "token","code","state","session","redirect","return","next","download","file",
}
_CATEGORY_PATTERNS={
    "analytics":("analytics","metrics","telemetry","measurement","stats"),
    "advertising":("ads","doubleclick","adservice","advert","marketing"),
    "social":("facebook","instagram","twitter","x.com","tiktok","linkedin"),
    "cdn":("cdn","cloudfront","akamai","fastly","jsdelivr","unpkg"),
}


@dataclass(frozen=True)
class TrackerInfo:
    domain: str
    entity: str=""
    company: str=""
    category: str="unknown"
    confidence: str="unknown"
    prevalence: float|None=None
    known_purpose: str=""
    fingerprinting_association: bool=False
    cookie_behavior: str="unknown"
    source: str="local"

    def as_dict(self): return asdict(self)


class LocalTrackerProvider:
    """Optional provider abstraction over a KRISHNA-owned local tracker catalog."""

    def __init__(self,path: str|Path|None=None):
        self.path=Path(path) if path else None
        self.items={}
        if self.path and self.path.is_file():
            try:
                raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
                rows=raw.get("trackers",raw) if isinstance(raw,dict) else raw
                if isinstance(rows,list):
                    for row in rows:
                        if isinstance(row,dict) and row.get("domain"):
                            self.items[str(row["domain"]).lower().strip(".")]=dict(row)
            except Exception:
                self.items={}

    def lookup(self,domain: str) -> dict:
        host=str(domain or "").lower().strip(".")
        item=self.items.get(host)
        if not item:
            for root,row in self.items.items():
                if host.endswith("."+root):
                    item=row
                    break
        if item:
            return {**TrackerInfo(host).as_dict(),**item,"domain":host,"source":item.get("source","local")}
        return TrackerInfo(host).as_dict()

    def status(self) -> dict:
        return {
            "provider":"local",
            "loaded":bool(self.items),
            "entries":len(self.items),
            "path":str(self.path) if self.path else None,
            "policy":"provider abstraction only; no licensing-restricted tracker dataset is bundled",
        }


def is_known_tracking_param(name: str) -> bool:
    raw=str(name or "")
    low=raw.lower()
    if low in {x.lower() for x in _TRACKING_PARAMS|_HUBSPOT_EXACT}:
        return True
    return any(low.startswith(x.lower()) for x in _TRACKING_PREFIXES)


def clean_tracking_url(url: str) -> dict:
    original=str(url or "").strip()
    parts=urlsplit(original)
    if parts.scheme not in {"http","https"}:
        raise ValueError("tracking URL cleaner requires http:// or https:// URL")
    kept=[];removed=[]
    for key,value in parse_qsl(parts.query,keep_blank_values=True):
        if is_known_tracking_param(key):
            removed.append({"parameter":key,"reason":"known_tracking_parameter"})
        else:
            kept.append((key,value))
    cleaned=urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(kept,doseq=True),parts.fragment))
    return {
        "before":original,
        "after":cleaned,
        "changed":cleaned!=original,
        "removed":removed,
        "preserved_unknown":True,
        "policy":"known tracking parameters are removed; functional/unknown parameters are preserved by default",
    }


def classify_request(url: str, first_party_host: str="") -> dict:
    parts=urlsplit(str(url or ""))
    host=(parts.hostname or "").lower()
    first=(first_party_host or "").lower().strip(".")
    relation="first_party" if first and (host==first or host.endswith("."+first)) else "third_party"
    text=(host+" "+parts.path).lower()
    category="unknown"
    for name,needles in _CATEGORY_PATTERNS.items():
        if any(n in text for n in needles):
            category=name
            break
    if relation=="first_party":
        category="functional" if category=="unknown" else category
    query_names=[k for k,_ in parse_qsl(parts.query,keep_blank_values=True)]
    decorated=[k for k in query_names if is_known_tracking_param(k)]
    return {
        "url_host":host,
        "relation":relation,
        "category":category,
        "link_decoration_parameters":decorated,
        "tracking_like":bool(decorated) or category in {"analytics","advertising","social"},
        "confidence":"heuristic",
        "note":"classification is evidence for review, not a maliciousness verdict",
    }


class TrackerBehaviorLearner:
    """Evidence accumulator. It never auto-blocks a domain."""

    def __init__(self):
        self._observations={}

    def observe(self,domain: str,*,site: str="",identifier_cookie=False,
                link_decoration=False,fingerprinting_api=False,cross_site_state=False) -> dict:
        host=str(domain or "").lower().strip(".")
        if not host:
            raise ValueError("domain is required")
        row=self._observations.setdefault(host,{
            "domain":host,"sites":set(),"observations":0,
            "identifier_cookie":0,"link_decoration":0,"fingerprinting_api":0,"cross_site_state":0,
        })
        row["observations"]+=1
        if site: row["sites"].add(str(site).lower().strip("."))
        for key,value in {
            "identifier_cookie":identifier_cookie,
            "link_decoration":link_decoration,
            "fingerprinting_api":fingerprinting_api,
            "cross_site_state":cross_site_state,
        }.items():
            if value: row[key]+=1
        signals=sum(1 for k in ("identifier_cookie","link_decoration","fingerprinting_api","cross_site_state") if row[k]>0)
        probable=len(row["sites"])>=3 and signals>=2
        return {
            "domain":host,
            "cross_site_presence":len(row["sites"]),
            "observations":row["observations"],
            "signals":{k:row[k] for k in ("identifier_cookie","link_decoration","fingerprinting_api","cross_site_state")},
            "classification":"probable_tracker" if probable else "insufficient_evidence",
            "auto_block":False,
        }

    def snapshot(self) -> list[dict]:
        return [self.observe(k) if False else {
            "domain":k,
            "cross_site_presence":len(v["sites"]),
            "observations":v["observations"],
            "signals":{x:v[x] for x in ("identifier_cookie","link_decoration","fingerprinting_api","cross_site_state")},
        } for k,v in sorted(self._observations.items())]
