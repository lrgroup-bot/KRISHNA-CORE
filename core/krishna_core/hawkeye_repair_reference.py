"""HAWKEYE repair reference lookup, with opt-in iFixit public API.

Read-only. Returns attributed search metadata and source URLs, not training data.
No crawling, guide copying, device access or autonomous repair.
"""
from __future__ import annotations
import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE="https://www.ifixit.com/api/2.0"
MAX_RESPONSE=512_000

def _query(value):
    if not isinstance(value,str) or not 2 <= len(value.strip()) <= 120:
        raise ValueError("model or module query must be 2-120 characters")
    return value.strip()

class HawkeyeRepairReference:
    def __init__(self, *, enabled=False, opener=None):
        self.enabled=bool(enabled)
        self._opener=opener or urlopen

    def _read(self, path):
        if not self.enabled:
            raise PermissionError("iFixit reference lookup is opt-in")
        req=Request(BASE+path,headers={"Accept":"application/json","User-Agent":"KRISHNA-Hawkeye-RepairReference/0.1"})
        with self._opener(req,timeout=10) as response:
            if getattr(response,"status",200)!=200:
                raise RuntimeError("reference provider unavailable")
            raw=response.read(MAX_RESPONSE+1)
        if len(raw)>MAX_RESPONSE:
            raise ValueError("reference response too large")
        return json.loads(raw.decode("utf-8"))

    def search_module(self, device_model, module):
        query=_query(device_model)+" "+_query(module)
        data=self._read("/suggest/"+quote(query,safe="")+"?doctypes=guide,device,category")
        if not isinstance(data,dict) or not isinstance(data.get("results"),list):
            raise ValueError("unexpected provider response")
        results=[]
        for row in data["results"][:10]:
            if not isinstance(row,dict):
                continue
            url=row.get("url","")
            if not isinstance(url,str) or not re.match(r"^https://(?:www\\.)?ifixit\\.com/",url,re.I):
                continue
            results.append({"title":str(row.get("title") or row.get("subject") or "")[:200],
                            "url":url,"kind":str(row.get("dataType") or "")[:40],
                            "source":"iFixit","usage":"reference_link_only",
                            "verified":False})
        return {"query":query,"results":results,"source":"iFixit public API",
                "license_notice":"CC BY-NC-SA; respect source terms; no model training or bulk ingestion",
                "knowledge_promotion_allowed":False}

    def hawkeye_module_card(self, device_model, module, *, measured_evidence=()):
        refs=self.search_module(device_model,module)
        evidence=tuple(measured_evidence)
        if len(evidence)>32 or not all(isinstance(x,str) and 0<len(x)<=256 for x in evidence):
            raise ValueError("invalid evidence")
        return {"device_model":_query(device_model),"module":_query(module),
                "observations":list(evidence),"repair_references":refs["results"],
                "diagnosis":"not_established","repair_authorized":False,
                "source_notice":refs["license_notice"]}
