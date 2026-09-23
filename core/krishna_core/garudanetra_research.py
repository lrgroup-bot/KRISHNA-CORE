from __future__ import annotations

"""Garudanetra Research Fabric v2.

JetBot-inspired browser-native ideas are adapted behind KRISHNA's existing
authority model:
- durable research missions and crash-safe workspace;
- reusable research skill registry with lifecycle/quality;
- specialist research scouts;
- evidence + contradiction tracking;
- Rishi/LAB BOT handoff packages.

Playwright/Garudanetra remains the canonical browser authority. This module
does not create a competing browser agent and never bypasses Sudarshan.
"""

from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from .privacy_guardian.store import PrivacyEvidenceStore
import json
import math
import re
import time
import uuid


_SENSITIVE=re.compile(r"(?:token|secret|pass(?:word)?|api[_-]?key|auth|signature|credential|session|code)",re.I)
_WORD=re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


def _now():
    return time.time()


def _clean(value, limit=4000):
    return str(value or "").strip()[:limit]


def _redact_url(value):
    raw=_clean(value,4000)
    if not raw:return ""
    try:
        p=urlsplit(raw)
        query=urlencode([(k,"REDACTED" if _SENSITIVE.search(k) else v)
                         for k,v in parse_qsl(p.query,keep_blank_values=True)],doseq=True)
        return urlunsplit((p.scheme,p.netloc.rsplit("@",1)[-1],p.path,query,""))
    except Exception:
        return "[invalid-url]"


def _tokens(value):
    return {x.lower() for x in _WORD.findall(_clean(value,8000)) if len(x)>=3}


class GarudanetraResearchFabric:
    VERSION="garudanetra-research-fabric-v2"

    BUILTIN_SKILLS={
        "research.paper.search":{
            "description":"Find strong scientific papers, reviews and replication evidence",
            "scout":"papers",
        },
        "research.github.inspect":{
            "description":"Inspect open-source implementations, issues and reproducible code",
            "scout":"github",
        },
        "research.patent.search":{
            "description":"Find patents and prior-art signals relevant to a research question",
            "scout":"patents",
        },
        "research.dataset.find":{
            "description":"Find datasets suitable for validation or benchmarking",
            "scout":"datasets",
        },
        "research.standard.find":{
            "description":"Find standards, metrology and authoritative technical guidance",
            "scout":"standards",
        },
        "research.claim.verify":{
            "description":"Collect evidence that supports, weakens or qualifies a claim",
            "scout":"verification",
        },
        "research.contradiction.find":{
            "description":"Actively seek conflicting results, failed replications and alternative explanations",
            "scout":"contradictions",
        },
        "research.lab.handoff":{
            "description":"Package a research question and evidence for Rishi/Shishya/LAB BOT",
            "scout":"handoff",
        },
    }

    SCOUTS={
        "papers":{
            "role":"scientific literature scout",
            "url":"https://pubmed.ncbi.nlm.nih.gov/?{query}",
            "query_key":"term",
        },
        "github":{
            "role":"implementation and failure-case scout",
            "url":"https://github.com/search?{query}",
            "query_key":"q",
            "extra":{"type":"repositories"},
        },
        "patents":{
            "role":"patent and prior-art scout",
            "url":"https://patents.google.com/?{query}",
            "query_key":"q",
        },
        "datasets":{
            "role":"dataset and benchmark scout",
            "url":"https://datasetsearch.research.google.com/search?{query}",
            "query_key":"query",
        },
        "standards":{
            "role":"standards and metrology scout",
            "url":"https://www.nist.gov/search?{query}",
            "query_key":"query",
        },
        "contradictions":{
            "role":"contradiction and failed-replication scout",
            "url":"https://pubmed.ncbi.nlm.nih.gov/?{query}",
            "query_key":"term",
            "suffix":" replication failure contradictory negative result",
        },
    }

    def __init__(self,runtime_root,session_factory=None):
        self.runtime_root=Path(runtime_root).resolve()
        self.root=self.runtime_root/"state"/"garudanetra"/"research"
        self.mission_root=self.root/"missions"
        self.root.mkdir(parents=True,exist_ok=True)
        self.mission_root.mkdir(parents=True,exist_ok=True)
        self.skills_path=self.root/"skills.json"
        self.session_factory=session_factory
        self._seed_skills()

    def _atomic(self,path,data):
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
        tmp.replace(path)

    def _load_json(self,path,default):
        try:return json.loads(path.read_text(encoding="utf-8"))
        except Exception:return default

    def _seed_skills(self):
        data=self._load_json(self.skills_path,{"schema":1,"skills":{}})
        skills=data.setdefault("skills",{})
        changed=False
        for name,spec in self.BUILTIN_SKILLS.items():
            if name not in skills:
                skills[name]={
                    "name":name,"description":spec["description"],"scout":spec["scout"],
                    "origin":"builtin","active":True,"use_count":0,"success_count":0,
                    "failure_count":0,"quality_score":0.5,"stage":"new",
                    "created_at":_now(),"last_used_at":None,
                }
                changed=True
        if changed or not self.skills_path.exists():self._atomic(self.skills_path,data)

    def _skills(self):
        return self._load_json(self.skills_path,{"schema":1,"skills":{}})

    @staticmethod
    def _quality(row):
        uses=max(0,int(row.get("use_count") or 0))
        success=max(0,int(row.get("success_count") or 0))
        failure=max(0,int(row.get("failure_count") or 0))
        if uses<=0:return 0.5
        ratio=(success+1)/(success+failure+2)
        breadth=min(1.0,math.log2(uses+1)/5.0)
        return round(max(0.0,min(1.0,0.25+0.55*ratio+0.20*breadth)),4)

    @staticmethod
    def _stage(row):
        uses=int(row.get("use_count") or 0);quality=float(row.get("quality_score") or 0)
        last=row.get("last_used_at")
        if last and (_now()-float(last))>60*60*24*45:return "stale"
        if uses<3:return "new"
        if uses>=10 and quality>=0.75:return "stable"
        return "active"

    def skills(self):
        rows=list(self._skills().get("skills",{}).values())
        rows.sort(key=lambda x:x["name"])
        return rows

    def use_skill(self,name,success=None):
        data=self._skills();skills=data.get("skills",{})
        row=skills.get(_clean(name,160))
        if not row:raise KeyError(name)
        row["use_count"]=int(row.get("use_count") or 0)+1
        if success is True:row["success_count"]=int(row.get("success_count") or 0)+1
        elif success is False:row["failure_count"]=int(row.get("failure_count") or 0)+1
        row["last_used_at"]=_now()
        row["quality_score"]=self._quality(row)
        row["stage"]=self._stage(row)
        self._atomic(self.skills_path,data)
        return dict(row)

    def propose_skill(self,name,description,instructions,source_mission=None):
        name=_clean(name,160).lower()
        if not name.startswith("research."):raise ValueError("distilled Garudanetra research skills must use research.* namespace")
        data=self._skills()
        if name in data.get("skills",{}):raise ValueError("skill already exists")
        return {
            "name":name,"description":_clean(description,1000),"instructions":_clean(instructions,8000),
            "source_mission":_clean(source_mission,120),"status":"candidate",
            "requires_owner_approval":True,
        }

    def promote_skill(self,candidate,approved=False):
        if not approved:raise PermissionError("promoting a distilled browser skill requires owner approval")
        row=dict(candidate or {})
        name=_clean(row.get("name"),160).lower()
        if not name.startswith("research."):raise ValueError("invalid research skill name")
        data=self._skills();skills=data.setdefault("skills",{})
        if name in skills:return dict(skills[name])
        skills[name]={
            "name":name,"description":_clean(row.get("description"),1000),
            "instructions":_clean(row.get("instructions"),8000),
            "scout":"custom","origin":"distilled","active":True,
            "use_count":0,"success_count":0,"failure_count":0,
            "quality_score":0.5,"stage":"new","created_at":_now(),"last_used_at":None,
            "source_mission":_clean(row.get("source_mission"),120),
        }
        self._atomic(self.skills_path,data)
        return dict(skills[name])

    def _mission_path(self,mission_id):
        return self.mission_root/(str(mission_id)+".json")

    def _load_mission(self,mission_id):
        path=self._mission_path(mission_id)
        if not path.is_file():raise KeyError(mission_id)
        return self._load_json(path,{})

    def _save_mission(self,row):
        row["updated_at"]=_now()
        self._atomic(self._mission_path(row["mission_id"]),row)

    def create_mission(self,payload):
        question=_clean(payload.get("question") or payload.get("goal"),4000)
        if not question:raise ValueError("question or goal is required")
        mid=str(uuid.uuid4())
        scouts=list(payload.get("scouts") or self.SCOUTS.keys())
        scouts=[str(x).strip().lower() for x in scouts if str(x).strip().lower() in self.SCOUTS]
        if not scouts:raise ValueError("at least one valid research scout is required")
        row={
            "schema":1,"version":self.VERSION,"mission_id":mid,
            "project":_clean(payload.get("project") or "KRISHNA",160),
            "requested_by":_clean(payload.get("requested_by") or "KRISHNA",160),
            "question":question,"status":"PLANNED",
            "scouts":scouts,"targets":[],"sessions":[],
            "evidence":[],"contradictions":[],"notes":[],
            "created_at":_now(),"updated_at":_now(),
            "handoff":None,
        }
        row["targets"]=self.plan_targets(question,scouts)
        self._save_mission(row)
        return row

    def plan_targets(self,question,scouts=None):
        selected=scouts or list(self.SCOUTS)
        out=[]
        for name in selected:
            spec=self.SCOUTS.get(name)
            if not spec:continue
            q=question+str(spec.get("suffix") or "")
            params={spec["query_key"]:q}
            params.update(spec.get("extra") or {})
            url=spec["url"].format(query=urlencode(params))
            out.append({
                "scout":name,"role":spec["role"],"url":url,
                "mode":"task_memory","purpose":"candidate evidence; independent verification required",
            })
        return out

    def launch_scout(self,mission_id,scout):
        row=self._load_mission(mission_id)
        scout=str(scout or "").strip().lower()
        target=next((x for x in row.get("targets",[]) if x.get("scout")==scout),None)
        if not target:raise KeyError(scout)
        launches=[x for x in (row.get("sessions") or []) if x.get("scout")==scout]
        if len(launches)>=3:
            raise RuntimeError("research scout circuit breaker: repeated launch limit reached")
        if launches and (_now()-float(launches[-1].get("started_at") or 0))<10:
            raise RuntimeError("research scout duplicate launch suppressed")
        if not callable(self.session_factory):raise RuntimeError("Garudanetra session factory is unavailable")
        result=self.session_factory(row.get("project") or "KRISHNA",target["url"],"task_memory")
        row["sessions"].append({
            "scout":scout,"session_id":result.get("session_id"),
            "url":_redact_url(target["url"]),"started_at":_now(),
        })
        row["status"]="RUNNING"
        self._save_mission(row)
        self.use_skill({
            "papers":"research.paper.search","github":"research.github.inspect",
            "patents":"research.patent.search","datasets":"research.dataset.find",
            "standards":"research.standard.find","contradictions":"research.contradiction.find",
        }[scout])
        return {"mission_id":mission_id,"scout":scout,"session":result}

    def ingest(self,mission_id,payload):
        row=self._load_mission(mission_id)
        stance=_clean(payload.get("stance") or "neutral",32).lower()
        if stance not in {"support","contradict","neutral","mixed"}:
            raise ValueError("stance must be support, contradict, neutral or mixed")
        # Research evidence is persistent state. Reuse KABACH's canonical text
        # sanitizer so credentials/tokens copied from pages are never written into
        # mission JSON, even when they appear inside otherwise ordinary fields.
        claim=_clean(PrivacyEvidenceStore.sanitize(str(payload.get("claim") or "")),4000)
        if not claim:raise ValueError("claim is required")
        title=_clean(PrivacyEvidenceStore.sanitize(str(payload.get("title") or "")),1000)
        excerpt=_clean(PrivacyEvidenceStore.sanitize(str(payload.get("excerpt") or "")),3000)
        claim_key=_clean(PrivacyEvidenceStore.sanitize(str(payload.get("claim_key") or claim)),500).lower()
        source_date=_clean(PrivacyEvidenceStore.sanitize(str(payload.get("source_date") or "")),80)
        item={
            "evidence_id":str(uuid.uuid4()),"source_kind":_clean(payload.get("source_kind") or "web",64),
            "url":_redact_url(payload.get("url")),"title":title,
            "claim":claim,"claim_key":claim_key,
            "stance":stance,"quality":max(0.0,min(1.0,float(payload.get("quality") or 0.5))),
            "excerpt":excerpt,
            "source_date":source_date,
            "added_at":_now(),
        }
        row["evidence"].append(item)
        row["status"]="EVIDENCE_COLLECTED"
        self._save_mission(row)
        return item

    def analyze(self,mission_id):
        row=self._load_mission(mission_id)
        evidence=list(row.get("evidence") or [])
        groups={}
        for item in evidence:
            key=item.get("claim_key") or item.get("claim") or ""
            groups.setdefault(key,[]).append(item)
        contradictions=[]
        for key,items in groups.items():
            support=[x for x in items if x.get("stance")=="support"]
            oppose=[x for x in items if x.get("stance")=="contradict"]
            if support and oppose:
                contradictions.append({
                    "claim_key":key,"supporting":len(support),"contradicting":len(oppose),
                    "max_support_quality":max(float(x.get("quality") or 0) for x in support),
                    "max_contradict_quality":max(float(x.get("quality") or 0) for x in oppose),
                    "status":"UNRESOLVED",
                })
        # Also detect near-duplicate claims with opposite stance so callers are not
        # forced to supply an identical claim_key.
        for i,a in enumerate(evidence):
            if a.get("stance") not in {"support","contradict"}:continue
            ta=_tokens(a.get("claim"))
            if not ta:continue
            for b in evidence[i+1:]:
                if {a.get("stance"),b.get("stance")}!={"support","contradict"}:continue
                tb=_tokens(b.get("claim"))
                union=ta|tb
                score=len(ta&tb)/max(1,len(union))
                if score>=0.55 and a.get("claim_key")!=b.get("claim_key"):
                    contradictions.append({
                        "claim_key":"semantic:"+str(uuid.uuid5(uuid.NAMESPACE_URL,(a["claim"]+"|"+b["claim"]).lower())),
                        "supporting":1,"contradicting":1,"similarity":round(score,4),"status":"UNRESOLVED",
                    })
        # dedupe
        seen=set();unique=[]
        for x in contradictions:
            k=x["claim_key"]
            if k in seen:continue
            seen.add(k);unique.append(x)
        row["contradictions"]=unique
        row["status"]="ANALYZED"
        self._save_mission(row)
        return {
            "mission_id":mission_id,"evidence_count":len(evidence),
            "supporting":sum(1 for x in evidence if x.get("stance")=="support"),
            "contradicting":sum(1 for x in evidence if x.get("stance")=="contradict"),
            "neutral_or_mixed":sum(1 for x in evidence if x.get("stance") in {"neutral","mixed"}),
            "contradictions":unique,"unresolved_contradictions":len(unique),
            "verification_policy":"contradictions remain visible; no automatic truth promotion",
        }

    def handoff(self,mission_id,target="rishi"):
        row=self._load_mission(mission_id)
        analysis=self.analyze(mission_id)
        target=str(target or "rishi").strip().lower()
        if target not in {"rishi","shishya","lab_bot","gyan_candidate"}:
            raise ValueError("target must be rishi, shishya, lab_bot or gyan_candidate")
        package={
            "mission_id":mission_id,"target":target,"project":row.get("project"),
            "question":row.get("question"),"evidence":row.get("evidence") or [],
            "analysis":analysis,
            "scientific_state":"candidate" if analysis["unresolved_contradictions"] else "evidence_collected",
            "next_step":(
                "design a controlled experiment with explicit controls/measurements"
                if target=="lab_bot" else
                "review evidence quality, provenance and unresolved contradictions"
            ),
            "requires_independent_verification":True,
        }
        row["handoff"]=package
        row["status"]="HANDED_OFF"
        self._save_mission(row)
        return package

    def mission(self,mission_id):
        return self._load_mission(mission_id)

    def missions(self,limit=100):
        rows=[]
        for path in sorted(self.mission_root.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True):
            row=self._load_json(path,{})
            rows.append({
                "mission_id":row.get("mission_id"),"project":row.get("project"),
                "requested_by":row.get("requested_by"),"question":row.get("question"),
                "status":row.get("status"),"evidence_count":len(row.get("evidence") or []),
                "contradictions":len(row.get("contradictions") or []),"updated_at":row.get("updated_at"),
            })
            if len(rows)>=max(1,min(int(limit),500)):break
        return rows

    def status(self):
        return {
            "version":self.VERSION,
            "authority":"KRISHNA -> Sudarshan -> Garudanetra -> Playwright",
            "canonical_browser":"playwright",
            "jetbot_inspiration":[
                "durable browser workspace","skill registry lifecycle","cross-task recall pattern",
                "agent-loop circuit-breaker philosophy","skill distillation with explicit promotion",
            ],
            "implemented":[
                "research_missions","specialist_scouts","browser_launch_targets","evidence_ingestion",
                "contradiction_detection","skill_lifecycle","rishi_lab_handoff","task_memory_sessions",
                "duplicate_launch_suppression","scout_circuit_breaker",
            ],
            "scouts":{k:{"role":v["role"]} for k,v in self.SCOUTS.items()},
            "skills":self.skills(),
            "missions":self.missions(50),
            "policy":{
                "playwright_remains_canonical":True,
                "jetbot_is_not_a_competing_authority":True,
                "distilled_skills_require_owner_approval":True,
                "evidence_is_candidate_until_verified":True,
                "contradictions_are_preserved":True,
            },
        }
