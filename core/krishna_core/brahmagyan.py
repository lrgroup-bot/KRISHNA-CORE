from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import RLock

from .rishi_council import RishiCouncil


MATURITY=(
    ("L0","Discovered"),
    ("L1","Read"),
    ("L2","Understood"),
    ("L3","Source Verified"),
    ("L4","Cross-checked"),
    ("L5","Applied"),
    ("L6","Tested"),
    ("L7","Mastered"),
    ("L8","Connected with wider knowledge"),
)
LEVEL_INDEX={code:i for i,(code,_) in enumerate(MATURITY)}
EVIDENCE_STATUS={
    "verified","strongly_supported","moderately_supported","weakly_supported",
    "contested","contradicted","unknown","historical_traditional_only",
}
TRACKS={"modern_science","vedic_classical","historical","philosophical","engineering","general"}


class BrahmagyanRuntime:
    """Deep, source-faithful knowledge maturation above Gyan-Bhandar.

    BRAHMAGYAN never equates reading with learning. It persists research missions,
    claims, contradictions, temporal validity and curiosity priorities. Trusted
    Gyan promotion requires evidence review and compilation, while actual browsing,
    model calls and temporary workers remain outside this class behind Sudarshan.
    """

    VERSION="brahmagyan-v1"

    def __init__(self,state_root,gyan,memory):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"state.json"
        self.gyan=gyan
        self.memory=memory
        self.council=RishiCouncil()
        self.lock=RLock()
        self.state={
            "missions":{},"claims":{},"curiosity":[],"shishya_archive":[],
            "created_at":time.time(),"version":self.VERSION,
        }
        self._load()

    def _load(self):
        if not self.path.is_file():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw,dict):
                for key in ("missions","claims","curiosity","shishya_archive"):
                    if key in raw:self.state[key]=raw[key]
        except Exception as exc:
            self.memory.audit("brahmagyan_state","load_failed",f"{type(exc).__name__}: {exc}")

    def _save(self):
        tmp=self.path.with_suffix(".tmp")
        payload=json.dumps(self.state,ensure_ascii=False,indent=2)
        tmp.write_text(payload,encoding="utf-8")
        os.replace(tmp,self.path)

    @staticmethod
    def _now():
        return time.time()

    @staticmethod
    def _track(value):
        value=str(value or "general").strip().lower()
        if value not in TRACKS:raise ValueError("invalid knowledge_track")
        return value

    @staticmethod
    def _source_row(source):
        if not isinstance(source,dict):raise TypeError("source must be an object")
        row={
            "title":str(source.get("title") or "").strip()[:500],
            "url":str(source.get("url") or "").strip()[:2000],
            "identifier":str(source.get("identifier") or source.get("doi") or "").strip()[:500],
            "author":str(source.get("author") or "").strip()[:500],
            "publication":str(source.get("publication") or "").strip()[:500],
            "publication_date":source.get("publication_date"),
            "retrieved_date":source.get("retrieved_date") or time.strftime("%Y-%m-%d"),
            "source_type":str(source.get("source_type") or "unknown").strip().lower()[:80],
            "primary":bool(source.get("primary",False)),
            "evidence":source.get("evidence"),
            "content_hash":source.get("content_hash"),
        }
        if not row["url"] and not row["identifier"] and not row["title"]:
            raise ValueError("source requires title, url or identifier")
        return row

    def create_mission(self,project,topic,question="",rishi_id=None,knowledge_track="general",priority=None,target_level="L8"):
        topic=str(topic or "").strip()
        if not topic:raise ValueError("topic is required")
        if target_level not in LEVEL_INDEX:raise ValueError("invalid target_level")
        selected=self.council.get(rishi_id) if rishi_id else self.council.select(topic,1)[0]
        mid=str(uuid.uuid4())
        mission={
            "mission_id":mid,"project":str(project or "KRISHNA"),"topic":topic,
            "question":str(question or topic).strip(),"lead_rishi":selected["id"],
            "knowledge_track":self._track(knowledge_track),"target_level":target_level,
            "maturity":"L0","status":"planned","created_at":self._now(),"updated_at":self._now(),
            "review_flow":self.review_flow(topic,selected["id"]),
            "deep_learning_loop":[
                "discover","read","understand_context","extract_claims","verify_sources",
                "cross_check","find_contradictions","apply","test","evaluate","connect","store",
            ],
            "source_policy":"prefer primary sources; secondary summaries cannot inherit primary-source weight",
            "dual_track_rule":"modern scientific evidence and Vedic/classical material stay separately labeled; similarities never imply scientific identity",
            "priority":priority or {},
            "claim_ids":[],"research_questions":[],"shishya_batches":[],
        }
        with self.lock:
            self.state["missions"][mid]=mission;self._save()
        self.memory.audit("brahmagyan_mission","planned",f"{mid}:{selected['id']}:{topic}")
        return dict(mission)

    def review_flow(self,topic,rishi_id=None):
        text=str(topic or "").lower()
        if any(x in text for x in ("security","cyber","resilience","failure","incident","supply chain")):
            return ["specialist","gautama","jamadagni","veda-vyasa","brahmagyan"]
        if any(x in text for x in ("ethic","governance","law","social","human consequence","public policy")):
            return ["specialist","gautama","vashistha","veda-vyasa","brahmagyan"]
        if any(x in text for x in ("frontier","quantum","robot","artificial intelligence","patent","new material","emerging")) or rishi_id=="vishwamitra":
            return ["vishwamitra","gautama","bharadvaja","jamadagni","veda-vyasa","brahmagyan"]
        return ["specialist","gautama","veda-vyasa","brahmagyan"]

    def deep_prompt(self,mission_id,rishi_id=None):
        m=self.mission(mission_id)
        r=self.council.get(rishi_id or m["lead_rishi"])
        return (
            f"You are {r['display_name']}, BRAHMAGYAN {r['role']}.\n"
            f"Mission: {m['topic']}\nQuestion: {m['question']}\n"
            "Do deep source-faithful research; a webpage read is not learned knowledge. "
            "Generate precise subquestions, seek primary sources, read source context, extract atomic claims, "
            "record provenance, search for independent support AND contradiction, grade uncertainty, and state what remains unknown. "
            "Do not collapse copied sources into independent evidence. Do not claim experiments/tests you did not perform. "
            "When modern science and Indian classical/Vedic material both apply, maintain separate labeled tracks and compare only after each is understood in its own context. "
            "Never force modern discoveries into ancient texts and never present symbolic/philosophical claims as experimentally demonstrated facts. "
            f"Target maturity: {m['target_level']}. Reviewer flow: {' -> '.join(m['review_flow'])}. "
            "Return: questions, sources, atomic claims, contradicting evidence, confidence, temporal validity, missing evidence, applications/tests, wider connections."
        )

    def mission(self,mission_id):
        with self.lock:
            row=self.state["missions"].get(str(mission_id))
            if not row:raise KeyError(mission_id)
            return dict(row)

    def missions(self,project=None,limit=100):
        with self.lock:rows=[dict(x) for x in self.state["missions"].values()]
        if project:rows=[x for x in rows if x.get("project")==project]
        return sorted(rows,key=lambda x:x.get("updated_at",0),reverse=True)[:max(1,min(int(limit),500))]

    def add_questions(self,mission_id,questions):
        questions=[str(x).strip()[:800] for x in (questions or []) if str(x).strip()]
        with self.lock:
            m=self.state["missions"].get(str(mission_id))
            if not m:raise KeyError(mission_id)
            existing=list(m.get("research_questions") or [])
            for q in questions:
                if q not in existing:existing.append(q)
            m["research_questions"]=existing[:300];m["updated_at"]=self._now();self._save()
            return dict(m)

    def record_claim(self,mission_id,claim,sources=None,knowledge_track=None,valid_from=None,valid_until=None):
        claim=str(claim or "").strip()
        if not claim:raise ValueError("claim is required")
        m=self.mission(mission_id)
        cid=str(uuid.uuid4())
        track=self._track(knowledge_track or m["knowledge_track"])
        source_rows=[self._source_row(x) for x in (sources or [])]
        row={
            "claim_id":cid,"mission_id":mission_id,"project":m["project"],"topic":m["topic"],
            "claim":claim,"knowledge_track":track,"maturity":"L0","evidence_status":"unknown",
            "sources":source_rows,"supporting_evidence":[],"contradicting_evidence":[],"qualifying_evidence":[],
            "context_summary":"","source_notes":[],"cross_check_notes":[],"application_notes":[],
            "test_evidence":[],"synthesis":"","teach_back":"","connections":[],
            "verified_by":None,"compiled_by":None,"confidence":0.0,
            "first_seen":self._now(),"last_verified":None,"valid_from":valid_from,"valid_until":valid_until,
            "replaced_by":None,"previous_state":None,"current_state":"active",
            "source_history":[dict(x) for x in source_rows],"knowledge_version":1,
            "created_at":self._now(),"updated_at":self._now(),
        }
        with self.lock:
            self.state["claims"][cid]=row
            self.state["missions"][mission_id]["claim_ids"].append(cid)
            self.state["missions"][mission_id]["updated_at"]=self._now()
            self._save()
        self.memory.audit("brahmagyan_claim","L0",f"{cid}:{m['lead_rishi']}:{claim[:160]}")
        return dict(row)

    def claim(self,claim_id):
        with self.lock:
            row=self.state["claims"].get(str(claim_id))
            if not row:raise KeyError(claim_id)
            return json.loads(json.dumps(row))

    def add_evidence(self,claim_id,kind,evidence):
        kind=str(kind or "").strip().lower()
        field={"supporting":"supporting_evidence","contradicting":"contradicting_evidence","qualifying":"qualifying_evidence"}.get(kind)
        if not field:raise ValueError("kind must be supporting, contradicting or qualifying")
        item=self._source_row(evidence)
        with self.lock:
            c=self.state["claims"].get(str(claim_id))
            if not c:raise KeyError(claim_id)
            c[field].append(item);c["source_history"].append(dict(item));c["updated_at"]=self._now();self._save()
            return json.loads(json.dumps(c))

    @staticmethod
    def _independent_source_count(c):
        keys=set()
        for src in list(c.get("sources") or [])+list(c.get("supporting_evidence") or [])+list(c.get("qualifying_evidence") or []):
            key=(src.get("identifier") or src.get("url") or src.get("publication") or src.get("title") or "").strip().lower()
            if key:keys.add(key)
        return len(keys)

    def _validate_advance(self,c,target,detail):
        i=LEVEL_INDEX[c["maturity"]];j=LEVEL_INDEX[target]
        if j!=i+1:raise ValueError("knowledge maturity must advance exactly one level at a time")
        sources=list(c.get("sources") or [])+list(c.get("supporting_evidence") or [])
        if target=="L1" and not sources:raise ValueError("L1 Read requires at least one traceable source")
        if target=="L2" and not str(detail.get("context_summary") or "").strip():
            raise ValueError("L2 Understood requires context_summary")
        if target=="L3":
            if not any(x.get("primary") for x in sources) and not str(detail.get("primary_source_unavailable_reason") or "").strip():
                raise ValueError("L3 Source Verified requires a primary source or an explicit primary-source-unavailable reason")
            if str(detail.get("verified_by") or "").strip().lower()!="gautama":
                raise ValueError("L3 Source Verified requires Gautama evidence review")
        if target=="L4":
            if self._independent_source_count(c)<2 and not str(detail.get("cross_check_notes") or "").strip():
                raise ValueError("L4 Cross-checked requires independent evidence or explicit cross-check notes")
            if str(detail.get("verified_by") or c.get("verified_by") or "").strip().lower()!="gautama":
                raise ValueError("L4 Cross-checked requires Gautama review")
        if target=="L5" and not detail.get("application_notes"):
            raise ValueError("L5 Applied requires application_notes")
        if target=="L6" and not detail.get("test_evidence"):
            raise ValueError("L6 Tested requires test_evidence")
        if target=="L7" and (not str(detail.get("synthesis") or "").strip() or not str(detail.get("teach_back") or "").strip()):
            raise ValueError("L7 Mastered requires synthesis and teach_back")
        if target=="L8" and not detail.get("connections"):
            raise ValueError("L8 Connected requires wider-knowledge connections")

    def advance_claim(self,claim_id,target_level,detail=None):
        target=str(target_level or "").strip().upper()
        if target not in LEVEL_INDEX:raise ValueError("invalid maturity level")
        detail=dict(detail or {})
        with self.lock:
            c=self.state["claims"].get(str(claim_id))
            if not c:raise KeyError(claim_id)
            self._validate_advance(c,target,detail)
            if "context_summary" in detail:c["context_summary"]=str(detail["context_summary"])
            if "source_notes" in detail:c["source_notes"]=list(detail["source_notes"] or [])
            if "cross_check_notes" in detail:
                v=detail["cross_check_notes"];c["cross_check_notes"]=v if isinstance(v,list) else [str(v)]
            if "application_notes" in detail:c["application_notes"]=list(detail["application_notes"] or [])
            if "test_evidence" in detail:c["test_evidence"]=list(detail["test_evidence"] or [])
            if "synthesis" in detail:c["synthesis"]=str(detail["synthesis"])
            if "teach_back" in detail:c["teach_back"]=str(detail["teach_back"])
            if "connections" in detail:c["connections"]=list(detail["connections"] or [])
            if detail.get("verified_by"):c["verified_by"]=str(detail["verified_by"]).strip().lower()
            if detail.get("compiled_by"):c["compiled_by"]=str(detail["compiled_by"]).strip().lower()
            if detail.get("evidence_status"):
                status=str(detail["evidence_status"]).strip().lower()
                if status not in EVIDENCE_STATUS:raise ValueError("invalid evidence_status")
                c["evidence_status"]=status
            if "confidence" in detail:c["confidence"]=max(0.0,min(float(detail["confidence"]),1.0))
            c["maturity"]=target;c["updated_at"]=self._now()
            if target in {"L3","L4","L6","L7","L8"}:c["last_verified"]=self._now()
            c["knowledge_version"]=int(c.get("knowledge_version") or 1)+1
            m=self.state["missions"][c["mission_id"]]
            levels=[LEVEL_INDEX[self.state["claims"][x]["maturity"]] for x in m["claim_ids"] if x in self.state["claims"]]
            if levels:m["maturity"]=MATURITY[min(levels)][0]
            m["updated_at"]=self._now();self._save()
            out=json.loads(json.dumps(c))
        self.memory.audit("brahmagyan_maturity",target,f"{claim_id}:{out['evidence_status']}:{out['confidence']}")
        return out

    def compile_claim(self,claim_id,compiled_by="veda-vyasa"):
        if str(compiled_by).strip().lower()!="veda-vyasa":raise PermissionError("Veda Vyasa is the canonical knowledge compiler")
        with self.lock:
            c=self.state["claims"].get(str(claim_id))
            if not c:raise KeyError(claim_id)
            if LEVEL_INDEX[c["maturity"]]<LEVEL_INDEX["L4"]:raise ValueError("claim must be cross-checked before Vyasa compilation")
            c["compiled_by"]="veda-vyasa";c["updated_at"]=self._now();self._save()
            return json.loads(json.dumps(c))

    def promotion_readiness(self,claim_id):
        c=self.claim(claim_id)
        unresolved=len(c.get("contradicting_evidence") or [])
        trusted=(
            LEVEL_INDEX[c["maturity"]]>=LEVEL_INDEX["L4"]
            and c.get("verified_by")=="gautama"
            and c.get("compiled_by")=="veda-vyasa"
            and c.get("evidence_status") in {"verified","strongly_supported"}
            and unresolved==0
            and bool(c.get("sources") or c.get("supporting_evidence"))
        )
        return {
            "claim_id":claim_id,"trusted_ready":trusted,"maturity":c["maturity"],
            "evidence_status":c["evidence_status"],"verified_by":c.get("verified_by"),
            "compiled_by":c.get("compiled_by"),"unresolved_contradictions":unresolved,
            "rule":"trusted Gyan requires L4+, Gautama review, Vyasa compilation, strong evidence and no unresolved contradiction",
        }

    def propose_to_gyan(self,claim_id):
        c=self.claim(claim_id);ready=self.promotion_readiness(claim_id)
        if not ready["trusted_ready"]:raise ValueError("claim is not ready for trusted Gyan promotion")
        provenance={
            "brahmagyan_claim_id":claim_id,"mission_id":c["mission_id"],"researching_rishi":self.mission(c["mission_id"])["lead_rishi"],
            "verification_agent":c["verified_by"],"compiler":c["compiled_by"],"knowledge_track":c["knowledge_track"],
            "maturity":c["maturity"],"evidence_status":c["evidence_status"],"first_seen":c["first_seen"],
            "last_verified":c["last_verified"],"valid_from":c["valid_from"],"valid_until":c["valid_until"],
            "knowledge_version":c["knowledge_version"],
        }
        evidence=list(c.get("sources") or [])+list(c.get("supporting_evidence") or [])+list(c.get("qualifying_evidence") or [])
        proposal=self.gyan.propose(
            c["project"],c["topic"],c["claim"],evidence,c["confidence"],
            source="BRAHMAGYAN",verified=True,memory_kind="semantic",provenance=provenance,
        )
        self.memory.audit("brahmagyan_gyan","waiting_approval",f"{claim_id}:{proposal['approval_id']}")
        return {"readiness":ready,"proposal":proposal}

    def supersede_claim(self,claim_id,replacement_claim_id):
        with self.lock:
            old=self.state["claims"].get(str(claim_id));new=self.state["claims"].get(str(replacement_claim_id))
            if not old or not new:raise KeyError("claim not found")
            old["current_state"]="superseded";old["replaced_by"]=replacement_claim_id;old["valid_until"]=old.get("valid_until") or self._now()
            new["previous_state"]=claim_id;new["knowledge_version"]=max(int(new.get("knowledge_version") or 1),int(old.get("knowledge_version") or 1)+1)
            old["updated_at"]=new["updated_at"]=self._now();self._save()
            return {"previous":json.loads(json.dumps(old)),"current":json.loads(json.dumps(new))}

    def add_curiosity(self,project,question,signals=None):
        q=str(question or "").strip()
        if not q:raise ValueError("question is required")
        s=dict(signals or {})
        weights={"relevance":.22,"project":.20,"knowledge_gap":.16,"importance":.12,"freshness":.08,"cross_domain":.07,"discovery":.05,"security":.05,"source_availability":.04,"coverage":-.05,"duplication":-.08,"resource_cost":-.06}
        score=.0
        for key,w in weights.items():
            score+=w*max(0.0,min(float(s.get(key,0.0) or 0.0),1.0))
        item={"id":str(uuid.uuid4()),"project":str(project or "KRISHNA"),"question":q,"signals":s,"priority":round(score,4),"status":"queued","created_at":self._now()}
        with self.lock:
            self.state["curiosity"].append(item)
            self.state["curiosity"]=sorted(self.state["curiosity"],key=lambda x:x.get("priority",0),reverse=True)[:1000]
            self._save()
        return dict(item)

    def curiosity_queue(self,project=None,limit=50):
        with self.lock:rows=[dict(x) for x in self.state["curiosity"] if x.get("status")=="queued"]
        if project:rows=[x for x in rows if x.get("project")==project]
        return sorted(rows,key=lambda x:x.get("priority",0),reverse=True)[:max(1,min(int(limit),200))]

    def background_decision(self,cpu_percent,ram_percent,production_busy=False):
        allowed=(not bool(production_busy) and float(cpu_percent)<50.0 and float(ram_percent)<70.0)
        top=self.curiosity_queue(limit=1)
        return {
            "allowed":allowed,"cpu_percent":float(cpu_percent),"ram_percent":float(ram_percent),
            "production_busy":bool(production_busy),"next_question":top[0] if allowed and top else None,
            "policy":"checkpoint and release resources whenever production workloads need CPU/GPU/RAM; no autonomous background daemon in v1",
        }

    def shishya_plan(self,mission_id,specialties=None,count=None):
        m=self.mission(mission_id)
        specs=[str(x).strip() for x in (specialties or []) if str(x).strip()]
        requested=int(count or len(specs) or 1)
        requested=max(1,min(requested,4))
        if not specs:specs=["Evidence Review"]
        specs=(specs+["Evidence Review"]*requested)[:requested]
        return {
            "mission_id":mission_id,"parent_rishi":m["lead_rishi"],"project":m["project"],
            "requested_count":requested,"specialties":specs,"ephemeral":True,
            "approval_required":True,"authority":"Sudarshan + AI-HR",
            "preserve_before_retirement":[
                "verified findings","successful methods","failed approaches","corrections","reusable skills",
                "evaluation results","research trajectory","sources","provenance","useful context","cross-domain relationships",
            ],
            "resource_policy":"max 4 BRAHMAGYAN Shishyas per batch; retire immediately after handover",
        }

    def absorb_shishya(self,mission_id,batch):
        m=self.mission(mission_id)
        receipt={
            "mission_id":mission_id,"parent_rishi":m["lead_rishi"],"batch_id":batch.get("batch_id"),
            "destroyed":bool(batch.get("destroyed")),"workers":[],
            "retired_at":self._now(),
        }
        for worker in batch.get("workers") or []:
            receipt["workers"].append({
                "worker_id":worker.get("worker_id"),"provider":worker.get("provider"),"model":worker.get("model"),
                "result":worker.get("result"),"security":worker.get("security"),
                "started_at":worker.get("started_at"),"ended_at":worker.get("ended_at"),
            })
        with self.lock:
            self.state["shishya_archive"].append(receipt)
            self.state["shishya_archive"]=self.state["shishya_archive"][-500:]
            self.state["missions"][mission_id]["shishya_batches"].append(receipt["batch_id"])
            self.state["missions"][mission_id]["updated_at"]=self._now();self._save()
        self.memory.remember(m["project"],"brahmagyan_shishya_handover",m["topic"],receipt)
        return receipt

    def status(self):
        with self.lock:
            missions=len(self.state["missions"]);claims=len(self.state["claims"]);curiosity=len([x for x in self.state["curiosity"] if x.get("status")=="queued"])
        return {
            "name":"BRAHMAGYAN","version":self.VERSION,"purpose":"autonomous universal-learning and research intelligence",
            "maturity_levels":[{"code":c,"name":n} for c,n in MATURITY],
            "deep_learning_loop":["discover","read","understand_context","extract_claims","verify_sources","cross_check","find_contradictions","apply","test","evaluate","connect","store"],
            "missions":missions,"claims":claims,"curiosity_queued":curiosity,
            "council":self.council.status(),
            "trusted_store":"Gyan-Bhandar","authority":"Sudarshan permissioned Action/Job architecture",
            "resource_policy":"council profiles are inert; workers are mission-scoped and temporary; no background daemon",
        }
