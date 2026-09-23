from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

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
RESEARCH_PHASES=(
    ("scope","Scope and question framing"),
    ("literature","Literature and source discovery"),
    ("claims","Atomic claim extraction"),
    ("challenge","Contradiction and adversarial challenge"),
    ("test","Application, experiment and falsification planning"),
    ("synthesis","Verified synthesis"),
    ("report","Research dossier and Gyan handoff"),
)
RESEARCH_PHASE_INDEX={code:i for i,(code,_) in enumerate(RESEARCH_PHASES)}


class BrahmagyanRuntime:
    """Deep, source-faithful knowledge maturation above Gyan-Bhandar.

    BRAHMAGYAN never equates reading with learning. It persists research missions,
    claims, contradictions, temporal validity and curiosity priorities. Trusted
    Gyan promotion requires evidence review and compilation, while actual browsing,
    model calls and temporary workers remain outside this class behind Sudarshan.
    """

    VERSION="brahmagyan-v2"

    def __init__(self,state_root,gyan,memory):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"state.json"
        self.gyan=gyan
        self.memory=memory
        self.council=RishiCouncil()
        self.gyan_qc=None
        self.cognitive_brain=None
        self.lock=RLock()
        self.state={
            "missions":{},"claims":{},"debates":{},"curiosity":[],"shishya_archive":[],"council_proposals":[],
            "created_at":time.time(),"version":self.VERSION,
        }
        self.load_error=None
        self._load()

    def bind_gyan_qc(self,qc):
        """Bind BRAHMA's QC gate without changing Gyan-Bhandar storage authority."""
        self.gyan_qc=qc
        return {"bound":qc is not None,"authority":"BRAHMA QC -> Gyan proposal/approval"}

    def bind_cognitive_brain(self, cognitive_brain):
        """Bind BRAHMA's associative concept memory without changing research authority."""
        self.cognitive_brain=cognitive_brain
        return {
            "bound": cognitive_brain is not None,
            "authority": "BRAHMAGYAN matures evidence; Cognitive Brain stores associations only",
        }

    def _load(self):
        if not self.path.is_file():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw,dict):
                for key in ("missions","claims","debates","curiosity","shishya_archive","council_proposals"):
                    if key in raw:self.state[key]=raw[key]
        except Exception as exc:
            self.load_error=f"{type(exc).__name__}: {exc}"
            self.memory.audit("brahmagyan_state","load_failed",self.load_error)

    def _healthy(self):
        if self.load_error:
            raise RuntimeError("BRAHMAGYAN state is unreadable; refusing to overwrite research state: "+self.load_error)

    def _save(self):
        self._healthy()
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
            "publisher":str(source.get("publisher") or "").strip()[:500],
            "publication_date":source.get("publication_date"),
            "retrieved_date":source.get("retrieved_date") or time.strftime("%Y-%m-%d"),
            "source_type":str(source.get("source_type") or "unknown").strip().lower()[:80],
            "primary":bool(source.get("primary",False)),
            "peer_reviewed":source.get("peer_reviewed"),
            "retracted":bool(source.get("retracted",False)),
            "parent_source":str(source.get("parent_source") or "").strip()[:500],
            "evidence":source.get("evidence"),
            "content_hash":source.get("content_hash"),
            "citation_verified":source.get("citation_verified"),
            "citation_relation":source.get("citation_relation"),
            "citation_notes":source.get("citation_notes"),
            "citation_verifier":source.get("citation_verifier"),
            "citation_reviewed_at":source.get("citation_reviewed_at"),
        }
        if not row["url"] and not row["identifier"] and not row["title"]:
            raise ValueError("source requires title, url or identifier")
        identity=(row["identifier"] or row["url"] or f"{row['publication']}|{row['author']}|{row['title']}").strip().lower()
        row["source_id"]=str(source.get("source_id") or hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20])
        host=""
        if row["url"]:
            try:host=(urlparse(row["url"]).hostname or "").lower()
            except Exception:host=""
        family=str(source.get("source_family") or row["parent_source"] or row["publisher"] or host or row["publication"] or row["author"] or row["source_id"]).strip().lower()
        row["source_family"]=family[:500]
        return row

    @staticmethod
    def _needs_dual_track(topic):
        text=str(topic or "").lower()
        classical=("veda","vedic","upanishad","gita","yoga","ayurveda","shastra","itihasa","sanskrit","classical indian","ancient indian")
        modern=("science","medical","medicine","physics","biology","psychology","neuroscience","astronomy","technology","clinical","quantum","genetic")
        return any(x in text for x in classical) and any(x in text for x in modern)

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
            "dual_track_required":self._needs_dual_track(topic),
            "maturity":"L0","status":"planned","created_at":self._now(),"updated_at":self._now(),
            "review_flow":self.review_flow(topic,selected["id"]),
            "deep_learning_loop":[
                "discover","read","understand_context","extract_claims","verify_sources",
                "cross_check","find_contradictions","apply","test","evaluate","connect","store",
            ],
            "source_policy":"prefer primary sources; secondary summaries cannot inherit primary-source weight",
            "dual_track_rule":"modern scientific evidence and Vedic/classical material stay separately labeled; similarities never imply scientific identity",
            "priority":priority or {},
            "phase":"scope","phase_history":[{"phase":"scope","at":self._now(),"evidence":[]}],
            "perspectives":[],"debate_ids":[],
            "claim_ids":[],"research_questions":[],"shishya_batches":[],
        }
        with self.lock:
            self.state["missions"][mid]=mission;self._save()
        self.memory.audit("brahmagyan_mission","planned",f"{mid}:{selected['id']}:{topic}")
        return dict(mission)

    def advance_phase(self,mission_id,target_phase,evidence=None):
        target=str(target_phase or "").strip().lower()
        if target not in RESEARCH_PHASE_INDEX:raise ValueError("invalid research phase")
        with self.lock:
            m=self.state["missions"].get(str(mission_id))
            if not m:raise KeyError(mission_id)
            current=str(m.get("phase") or "scope")
            if RESEARCH_PHASE_INDEX[target]!=RESEARCH_PHASE_INDEX[current]+1:
                raise ValueError("research phase must advance exactly one stage at a time")
            m["phase"]=target
            m.setdefault("phase_history",[]).append({
                "phase":target,"at":self._now(),"evidence":list(evidence or []),
            })
            m["updated_at"]=self._now();self._save()
            return json.loads(json.dumps(m))

    def perspective_plan(self,mission_id,limit=5,preferred_rishis=None):
        m=self.mission(mission_id)
        limit=max(3,min(int(limit),8))
        preferred=[]
        for rid in preferred_rishis or []:
            rid=str(rid or "").strip().lower()
            if not rid or rid in preferred:continue
            self.council.get(rid)
            preferred.append(rid)
        core=[x for x in ("gautama","veda-vyasa") if x in {p["id"] for p in self.council.list()}]
        specialist_slots=max(1,limit-len(core))
        ordered=[x for x in preferred if x not in core][:specialist_slots]
        for profile in self.council.select(f"{m['topic']} {m['question']}",limit):
            if profile["id"] not in ordered and profile["id"] not in core and len(ordered)<specialist_slots:
                ordered.append(profile["id"])
        for rid in core:
            if rid not in ordered:ordered.append(rid)
        selected=[self.council.get(x) for x in ordered[:limit]]
        rows=[]
        seen=set()
        for r in selected:
            if r["id"] in seen:continue
            seen.add(r["id"])
            q=(f"{r['display_name']} lens — {r['question']} "
               f"Apply this lens to the mission question: {m['question']}")
            rows.append({
                "rishi_id":r["id"],"display_name":r["display_name"],"role":r["role"],
                "lens":r["question"],"research_question":q,
            })
        with self.lock:
            live=self.state["missions"].get(str(mission_id))
            if not live:raise KeyError(mission_id)
            live["perspectives"]=rows
            existing=list(live.get("research_questions") or [])
            for row in rows:
                if row["research_question"] not in existing:existing.append(row["research_question"])
            live["research_questions"]=existing[:300]
            live["updated_at"]=self._now();self._save()
        return {"mission_id":mission_id,"perspectives":rows,
                "preferred_rishis":preferred,
                "policy":"Science Atlas/mission specialists are preserved when supplied; multi-perspective questions broaden retrieval but are not independent evidence by themselves"}

    @staticmethod
    def _all_evidence_rows(c):
        return (
            list(c.get("sources") or [])+
            list(c.get("supporting_evidence") or [])+
            list(c.get("qualifying_evidence") or [])+
            list(c.get("contradicting_evidence") or [])
        )

    def evidence_audit(self,claim_id):
        c=self.claim(claim_id)
        supporting=list(c.get("sources") or [])+list(c.get("supporting_evidence") or [])
        all_rows=self._all_evidence_rows(c)
        support_families={str(x.get("source_family") or x.get("source_id") or "").strip().lower() for x in supporting}
        support_families.discard("")
        all_families={str(x.get("source_family") or x.get("source_id") or "").strip().lower() for x in all_rows}
        all_families.discard("")
        hashes=[str(x.get("content_hash") or "").strip().lower() for x in all_rows if x.get("content_hash")]
        duplicate_hashes=sorted({h for h in hashes if hashes.count(h)>1})
        audited=[x for x in all_rows if x.get("citation_verified") is not None]
        citation_verified=[x for x in audited if x.get("citation_verified") is True]
        retracted_support=[x for x in supporting if x.get("retracted")]
        contradictions=list(c.get("contradicting_evidence") or [])
        unresolved=[x for x in contradictions if not x.get("resolved_at")]
        issues=[]
        if len(support_families)<2:issues.append("fewer than two independent supporting source families")
        if not contradictions:issues.append("no contradicting evidence has been recorded")
        if retracted_support:issues.append("supporting evidence includes a source marked retracted")
        if duplicate_hashes:issues.append("duplicate source content detected")
        if not audited:issues.append("citation entailment has not yet been explicitly audited")
        return {
            "claim_id":claim_id,
            "source_count":len(all_rows),
            "supporting_source_count":len(supporting),
            "primary_source_count":len([x for x in supporting if x.get("primary")]),
            "independent_support_families":len(support_families),
            "independent_all_families":len(all_families),
            "contradicting_source_count":len(contradictions),
            "unresolved_contradictions":len(unresolved),
            "retracted_support_count":len(retracted_support),
            "duplicate_content_hashes":duplicate_hashes,
            "citation_audited_count":len(audited),
            "citation_verified_count":len(citation_verified),
            "issues":issues,
            "verifier_policy":"citation verification is a named, versioned instrument; its verdict is evidence about attribution, not infallible truth",
        }

    def citation_review(self,claim_id,source_id,supported,relation="supports",verifier="gautama",notes="",protocol="manual-v1"):
        sid=str(source_id or "").strip()
        if not sid:raise ValueError("source_id is required")
        relation=str(relation or "supports").strip().lower()
        if relation not in {"supports","contradicts","qualifies","unrelated"}:raise ValueError("invalid citation relation")
        verifier=str(verifier or "").strip().lower()
        if not verifier:raise ValueError("verifier is required")
        found=False
        with self.lock:
            c=self.state["claims"].get(str(claim_id))
            if not c:raise KeyError(claim_id)
            for field in ("sources","supporting_evidence","qualifying_evidence","contradicting_evidence"):
                for row in c.get(field) or []:
                    if str(row.get("source_id") or "")==sid:
                        row["citation_verified"]=bool(supported)
                        row["citation_relation"]=relation
                        row["citation_notes"]=str(notes or "")[:2000]
                        row["citation_verifier"]=verifier
                        row["citation_protocol"]=str(protocol or "manual-v1")[:200]
                        row["citation_reviewed_at"]=self._now()
                        found=True
            if not found:raise KeyError("source_id not found on claim")
            c["updated_at"]=self._now();c["knowledge_version"]=int(c.get("knowledge_version") or 1)+1
            self._save()
            return self.evidence_audit(claim_id)

    def debate_policy(self,mission_id,stakes="normal"):
        m=self.mission(mission_id)
        claims=[self.claim(x) for x in m.get("claim_ids") or []]
        unresolved=sum(len([e for e in c.get("contradicting_evidence") or [] if not e.get("resolved_at")]) for c in claims)
        contested=len([c for c in claims if c.get("evidence_status") in {"contested","contradicted"}])
        stakes=str(stakes or "normal").strip().lower()
        high_stakes=stakes in {"high","critical"}
        reasons=[]
        if unresolved:reasons.append("unresolved contradictory evidence")
        if contested:reasons.append("contested or contradicted claims")
        if m.get("dual_track_required"):reasons.append("dual evidence tracks require careful comparison")
        if high_stakes:reasons.append("high-stakes decision")
        recommended=bool(reasons)
        return {
            "mission_id":mission_id,"recommended":recommended,"stakes":stakes,
            "unresolved_contradictions":unresolved,"contested_claims":contested,"reasons":reasons,
            "policy":"debate is selective, not the default; use it where disagreement can reveal hidden assumptions or evidence conflicts",
        }

    def open_debate(self,mission_id,proposition="",participants=None,stakes="normal"):
        m=self.mission(mission_id)
        chosen=[str(x).strip().lower() for x in (participants or []) if str(x).strip()]
        if not chosen:
            chosen=[x["id"] for x in self.council.select(f"{m['topic']} {m['question']}",4)]
        dedup=[]
        for rid in chosen:
            self.council.get(rid)
            if rid not in dedup:dedup.append(rid)
        if len(dedup)<2:raise ValueError("debate requires at least two Rishi participants")
        did=str(uuid.uuid4())
        row={
            "debate_id":did,"mission_id":mission_id,
            "proposition":str(proposition or m["question"]).strip(),
            "participants":dedup[:6],"stakes":str(stakes or "normal").strip().lower(),
            "policy":self.debate_policy(mission_id,stakes),"turns":[],
            "status":"open","opened_at":self._now(),"closed_at":None,
            "synthesis":"","gautama_review":None,"unresolved":[],
        }
        with self.lock:
            self.state["debates"][did]=row
            live=self.state["missions"][mission_id]
            live.setdefault("debate_ids",[]).append(did);live["updated_at"]=self._now();self._save()
        return json.loads(json.dumps(row))

    def record_debate_turn(self,debate_id,rishi_id,position,claim_ids=None,objections=None,response_to=None):
        rid=str(rishi_id or "").strip().lower()
        position=str(position or "").strip()
        if not position:raise ValueError("position is required")
        with self.lock:
            d=self.state["debates"].get(str(debate_id))
            if not d:raise KeyError(debate_id)
            if d.get("status")!="open":raise ValueError("debate is closed")
            if rid not in d.get("participants",[]):raise PermissionError("Rishi is not a participant in this debate")
            self.council.get(rid)
            valid_claims=[]
            for cid in claim_ids or []:
                c=self.state["claims"].get(str(cid))
                if not c or c.get("mission_id")!=d["mission_id"]:raise ValueError("debate claim must belong to the same mission")
                valid_claims.append(str(cid))
            turn={
                "turn_id":str(uuid.uuid4()),"rishi_id":rid,"position":position,
                "claim_ids":valid_claims,
                "objections":[str(x).strip()[:1500] for x in (objections or []) if str(x).strip()],
                "response_to":response_to,"grounding":"claim_linked" if valid_claims else "argument_only",
                "created_at":self._now(),
            }
            d["turns"].append(turn);self._save()
            return json.loads(json.dumps(turn))

    def close_debate(self,debate_id,synthesis,gautama_review,unresolved=None,closed_by="veda-vyasa"):
        if str(closed_by or "").strip().lower()!="veda-vyasa":
            raise PermissionError("Veda Vyasa is the canonical debate synthesizer")
        synthesis=str(synthesis or "").strip()
        if not synthesis:raise ValueError("synthesis is required")
        review=dict(gautama_review or {})
        if "evidence_sufficient" not in review:raise ValueError("Gautama review must state evidence_sufficient")
        review["reviewer"]="gautama"
        with self.lock:
            d=self.state["debates"].get(str(debate_id))
            if not d:raise KeyError(debate_id)
            if d.get("status")!="open":raise ValueError("debate is already closed")
            contributors={x.get("rishi_id") for x in d.get("turns") or [] if x.get("rishi_id")}
            if len(contributors)<2:raise ValueError("debate requires contributions from at least two Rishis before synthesis")
            d["status"]="closed";d["synthesis"]=synthesis;d["gautama_review"]=review
            d["unresolved"]=[str(x).strip()[:1500] for x in (unresolved or []) if str(x).strip()]
            d["closed_at"]=self._now();self._save()
            return json.loads(json.dumps(d))

    def research_scorecard(self,mission_id):
        m=self.mission(mission_id)
        claims=[self.claim(x) for x in m.get("claim_ids") or []]
        audits=[self.evidence_audit(c["claim_id"]) for c in claims]
        return {
            "mission_id":mission_id,"phase":m.get("phase","scope"),"claim_count":len(claims),
            "cross_checked_claims":len([c for c in claims if LEVEL_INDEX.get(c.get("maturity","L0"),0)>=LEVEL_INDEX["L4"]]),
            "trusted_ready_claims":len([c for c in claims if self.promotion_readiness(c["claim_id"])["trusted_ready"]]),
            "contested_claims":len([c for c in claims if c.get("evidence_status") in {"contested","contradicted"}]),
            "source_count":sum(a["source_count"] for a in audits),
            "citation_audited_count":sum(a["citation_audited_count"] for a in audits),
            "citation_verified_count":sum(a["citation_verified_count"] for a in audits),
            "unresolved_contradictions":sum(a["unresolved_contradictions"] for a in audits),
            "research_questions":len(m.get("research_questions") or []),
            "perspectives":len(m.get("perspectives") or []),
            "debates":len(m.get("debate_ids") or []),
            "policy":"diagnostic scorecard only; it does not collapse research quality into a single truth score",
        }

    def dossier(self,mission_id):
        m=self.mission(mission_id)
        claims=[self.claim(x) for x in m.get("claim_ids") or []]
        debates=[]
        with self.lock:
            for did in m.get("debate_ids") or []:
                if did in self.state["debates"]:debates.append(json.loads(json.dumps(self.state["debates"][did])))
        return {
            "mission":m,"scorecard":self.research_scorecard(mission_id),
            "claims":[{
                "claim_id":c["claim_id"],"claim":c["claim"],"knowledge_track":c["knowledge_track"],
                "maturity":c["maturity"],"evidence_status":c["evidence_status"],"confidence":c["confidence"],
                "audit":self.evidence_audit(c["claim_id"]),
            } for c in claims],
            "debates":debates,
            "open_questions":list(m.get("research_questions") or []),
            "policy":"preserve disagreements, provenance and unknowns; synthesis must not erase unresolved evidence conflicts",
        }

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
        if m.get("dual_track_required") and track=="general":
            raise ValueError("this mission requires separate modern_science and vedic_classical/historical/philosophical claim tracks")
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
        if self.cognitive_brain is not None:
            try:
                self.cognitive_brain.learn_concept(
                    m["topic"],
                    track=track,
                    confidence=0.0,
                    maturity="L0",
                    evidence_status="unknown",
                    provenance={"mission_id":mission_id,"claim_id":cid},
                    rishi_id=m["lead_rishi"],
                )
            except Exception as exc:
                self.memory.audit("cognitive_brain","claim_seed_failed",f"{cid}:{type(exc).__name__}:{exc}")
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
            key=(src.get("source_family") or src.get("identifier") or src.get("url") or src.get("publication") or src.get("title") or "").strip().lower()
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
        if self.cognitive_brain is not None:
            try:
                mission=self.mission(out["mission_id"])
                self.cognitive_brain.learn_concept(
                    out["topic"],
                    track=out.get("knowledge_track") or "general",
                    confidence=out.get("confidence") or 0.0,
                    maturity=out.get("maturity") or "L0",
                    evidence_status=out.get("evidence_status") or "candidate",
                    provenance={"mission_id":out["mission_id"],"claim_id":claim_id},
                    rishi_id=mission.get("lead_rishi"),
                )
                if out.get("connections"):
                    self.cognitive_brain.ingest_research(
                        out["topic"],
                        related_concepts=out.get("connections") or [],
                        track=out.get("knowledge_track") or "general",
                        confidence=out.get("confidence") or 0.0,
                        maturity=out.get("maturity") or "L0",
                        evidence_status=out.get("evidence_status") or "candidate",
                        provenance={"mission_id":out["mission_id"],"claim_id":claim_id},
                        rishi_id=mission.get("lead_rishi"),
                    )
            except Exception as exc:
                self.memory.audit("cognitive_brain","claim_connect_failed",f"{claim_id}:{type(exc).__name__}:{exc}")
        self.memory.audit("brahmagyan_maturity",target,f"{claim_id}:{out['evidence_status']}:{out['confidence']}")
        return out

    def resolve_contradiction(self,claim_id,index,resolution,evidence_status=None):
        resolution=str(resolution or "").strip()
        if not resolution:raise ValueError("resolution is required")
        with self.lock:
            c=self.state["claims"].get(str(claim_id))
            if not c:raise KeyError(claim_id)
            rows=c.get("contradicting_evidence") or []
            idx=int(index)
            if idx<0 or idx>=len(rows):raise IndexError("contradiction index out of range")
            rows[idx]["resolution"]=resolution
            rows[idx]["resolved_at"]=self._now()
            if evidence_status:
                status=str(evidence_status).strip().lower()
                if status not in EVIDENCE_STATUS:raise ValueError("invalid evidence_status")
                c["evidence_status"]=status
            c["updated_at"]=self._now();c["knowledge_version"]=int(c.get("knowledge_version") or 1)+1
            self._save()
            return json.loads(json.dumps(c))

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
        unresolved=len([x for x in (c.get("contradicting_evidence") or []) if not x.get("resolved_at")])
        audit=self.evidence_audit(claim_id)
        trusted=(
            LEVEL_INDEX[c["maturity"]]>=LEVEL_INDEX["L4"]
            and c.get("verified_by")=="gautama"
            and c.get("compiled_by")=="veda-vyasa"
            and c.get("evidence_status") in {"verified","strongly_supported"}
            and unresolved==0
            and audit["retracted_support_count"]==0
            and bool(c.get("sources") or c.get("supporting_evidence"))
        )
        return {
            "claim_id":claim_id,"trusted_ready":trusted,"maturity":c["maturity"],
            "evidence_status":c["evidence_status"],"verified_by":c.get("verified_by"),
            "compiled_by":c.get("compiled_by"),"unresolved_contradictions":unresolved,
            "evidence_audit":audit,
            "rule":"trusted Gyan requires L4+, Gautama review, Vyasa compilation, strong evidence, no unresolved contradiction and no retracted supporting source",
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
        if self.gyan_qc is not None:
            qc=self.gyan_qc(
                project=c["project"],topic=c["topic"],lesson=c["claim"],evidence=evidence,
                provenance=provenance,confidence=c["confidence"],maturity=c["maturity"],
                evidence_status=c["evidence_status"],
                unresolved_contradictions=ready["unresolved_contradictions"],
                memory_kind="semantic",source="BRAHMAGYAN",
            )
            if not qc.get("candidate_passed") or not qc.get("proposal"):
                raise ValueError("BRAHMA QC rejected Gyan promotion: "+", ".join(qc.get("reasons") or ["quality gate failed"]))
            proposal=qc["proposal"]
            self.memory.audit("brahmagyan_gyan","waiting_approval",f"{claim_id}:{proposal['approval_id']}:brahma_qc")
            return {"readiness":ready,"brahma_qc":qc,"proposal":proposal}

        # Compatibility fallback for isolated unit use. Production KRISHNA binds BRAHMA QC.
        proposal=self.gyan.propose(
            c["project"],c["topic"],c["claim"],evidence,c["confidence"],
            source="BRAHMAGYAN",verified=True,memory_kind="semantic",provenance=provenance,
        )
        self.memory.audit("brahmagyan_gyan","waiting_approval",f"{claim_id}:{proposal['approval_id']}:qc_unbound")
        return {"readiness":ready,"proposal":proposal,"brahma_qc":{"bound":False}}

    def supersede_claim(self,claim_id,replacement_claim_id):
        with self.lock:
            old=self.state["claims"].get(str(claim_id));new=self.state["claims"].get(str(replacement_claim_id))
            if not old or not new:raise KeyError("claim not found")
            old["current_state"]="superseded";old["replaced_by"]=replacement_claim_id;old["valid_until"]=old.get("valid_until") or self._now()
            new["previous_state"]=claim_id;new["knowledge_version"]=max(int(new.get("knowledge_version") or 1),int(old.get("knowledge_version") or 1)+1)
            old["updated_at"]=new["updated_at"]=self._now();self._save()
            return {"previous":json.loads(json.dumps(old)),"current":json.loads(json.dumps(new))}

    def gap_questions(self,claim_id,queue=False):
        c=self.claim(claim_id)
        questions=[]
        if not c.get("sources"):
            questions.append("What is the strongest primary source for this claim?")
        if not c.get("context_summary"):
            questions.append("What source context, definitions, scope and limitations are required to understand this claim correctly?")
        if not c.get("supporting_evidence"):
            questions.append("What independent evidence supports this claim?")
        if not c.get("contradicting_evidence"):
            questions.append("What credible evidence or interpretation contradicts this claim?")
        if LEVEL_INDEX[c["maturity"]]<LEVEL_INDEX["L5"]:
            questions.append("Where can this claim be applied without assuming more than the evidence supports?")
        if not c.get("test_evidence"):
            questions.append("How could this claim be tested, benchmarked or falsified?")
        if not c.get("connections"):
            questions.append("Which related domains, causes, consequences or historical states should this claim connect to?")
        if c.get("knowledge_track") in {"modern_science","vedic_classical"}:
            other="vedic/classical" if c["knowledge_track"]=="modern_science" else "modern scientific"
            questions.append(f"What does the separate {other} track say about this topic, without forcing equivalence?")
        created=[]
        if queue:
            for q in questions:
                created.append(self.add_curiosity(c["project"],q,{"knowledge_gap":1,"relevance":1,"project":1,"duplication":0,"resource_cost":.2}))
        return {"claim_id":claim_id,"questions":questions,"queued":created}

    def propose_council_specialist(self,domain,role,reason):
        domain=str(domain or "").strip().lower();role=str(role or "").strip();reason=str(reason or "").strip()
        if not domain or not role or not reason:raise ValueError("domain, role and reason are required")
        overlaps=[]
        for profile in self.council.list():
            hits=[d for d in profile["domains"] if domain in d or d in domain]
            if hits:overlaps.append({"id":profile["id"],"display_name":profile["display_name"],"overlap":hits})
        proposal={
            "proposal_id":str(uuid.uuid4()),"domain":domain,"role":role,"reason":reason,
            "duplicate_candidates":overlaps,"status":"needs_duplication_review" if overlaps else "candidate",
            "created_at":self._now(),
            "policy":"proposal only; permanent Rishi creation requires AI-HR duplication review plus Sudarshan authorization and code/runtime registration",
        }
        with self.lock:
            self.state["council_proposals"].append(proposal)
            self.state["council_proposals"]=self.state["council_proposals"][-200:]
            self._save()
        return dict(proposal)

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

    def shishya_plan(self,mission_id,specialties=None,count=None,parent_rishi=None,assignments=None):
        m=self.mission(mission_id)
        parent=str(parent_rishi or m["lead_rishi"]).strip().lower()
        self.council.get(parent)
        specs=[str(x).strip() for x in (specialties or []) if str(x).strip()]
        requested=max(1,int(count or len(specs) or len(assignments or []) or 4))
        max_total=max(1,int(os.getenv("KRISHNA_SHISHYA_MAX_PER_REQUEST","32")))
        tree_nodes=max(1,min(int(os.getenv("KRISHNA_SHISHYA_MAX_TREE_NODES","64")),256))
        requested=min(requested,max_total,tree_nodes)
        concurrency=max(1,min(int(os.getenv("KRISHNA_SHISHYA_MAX_CONCURRENT","8")),8))
        if not specs:
            specs=[
                "Primary Source Discovery",
                "Contradiction and Negative Evidence",
                "Replication and Methods Audit",
                "Cross-Domain Hypothesis Review",
            ]
            if m.get("dual_track_required"):specs.append("Vedic/Classical Provenance Review")
        while len(specs)<requested:
            specs.append(f"Specialist Research {len(specs)+1}")
        specs=specs[:requested]
        raw_assign=list(assignments or [])
        rows=[]
        for i in range(requested):
            supplied=raw_assign[i] if i<len(raw_assign) and isinstance(raw_assign[i],dict) else {}
            rows.append({
                "index":i+1,
                "specialty":str(supplied.get("specialty") or specs[i]).strip()[:240],
                "task":str(supplied.get("task") or (
                    f"Investigate the mission from the {specs[i]} perspective. "
                    "Find evidence, contradictions, failed approaches, useful methods, unresolved questions and provenance."
                )).strip()[:6000],
            })
        waves=[rows[i:i+concurrency] for i in range(0,len(rows),concurrency)]
        tree_depth=max(1,min(int(os.getenv("KRISHNA_SHISHYA_MAX_DEPTH","3")),5))
        tree_children=max(0,min(int(os.getenv("KRISHNA_SHISHYA_MAX_CHILDREN","4")),8))
        return {
            "mission_id":mission_id,"parent_rishi":parent,"project":m["project"],
            "requested_count":requested,"specialties":specs,"assignments":rows,
            "waves":waves,"wave_count":len(waves),"max_concurrent":concurrency,
            "nested_delegation":True,
            "tree_policy":{
                "max_depth":tree_depth,
                "max_nodes":tree_nodes,
                "max_children_per_shishya":tree_children,
                "scope_inheritance":"descendants inherit parent project/privacy/permissions/safety; authority cannot expand",
                "collapse_policy":"all descendant findings collapse upward into the parent Rishi; temporary identities are destroyed",
            },
            "ephemeral":True,"approval_required":True,"authority":"Sudarshan + AI-HR + resource governor",
            "preserve_before_retirement":[
                "verified findings","supporting and contradicting evidence","successful methods","failed approaches",
                "corrections","reusable skills","evaluation results","sources","provenance","unresolved questions",
                "cross-domain relationships",
            ],
            "retention_policy":"findings_and_provenance_only",
            "destruction_policy":"retire every Shishya immediately after verified handover; keep no live worker identity/state",
            "resource_policy":(
                f"up to {concurrency} concurrent Shishyas per wave; up to {max_total} per request; "
                "Rishi may request later waves while the mission remains active and resource budgets permit"
            ),
        }

    @staticmethod
    def _parse_shishya_result(text):
        raw=str(text or "").strip()
        if not raw:return {"summary":"","findings":[],"failed_approaches":[],"unresolved_questions":[]}
        candidates=[raw]
        if "```" in raw:
            parts=raw.split("```")
            for part in parts:
                part=part.strip()
                if part.lower().startswith("json"):part=part[4:].strip()
                if part.startswith("{") and part.endswith("}"):candidates.append(part)
        if "{" in raw and "}" in raw:
            candidates.append(raw[raw.find("{"):raw.rfind("}")+1])
        data=None
        for candidate in candidates:
            try:
                value=json.loads(candidate)
                if isinstance(value,dict):
                    data=value;break
            except Exception:
                continue
        if data is None:
            return {
                "summary":raw[:6000],
                "findings":[{
                    "finding":raw[:4000],"evidence":[],"sources":[],
                    "confidence":0.0,"knowledge_track":"general","status":"provisional_unstructured",
                }],
                "failed_approaches":[],"unresolved_questions":[],
                "successful_methods":[],"corrections":[],"reusable_skills":[],
                "evaluation_results":[],"cross_domain_relationships":[],
            }
        findings=[]
        for item in data.get("findings") or []:
            if isinstance(item,str):
                item={"finding":item}
            if not isinstance(item,dict):continue
            finding=str(item.get("finding") or item.get("claim") or "").strip()
            if not finding:continue
            findings.append({
                "finding":finding[:4000],
                "evidence":[str(x).strip()[:1600] for x in (item.get("evidence") or []) if str(x).strip()],
                "sources":[str(x).strip()[:2000] for x in (item.get("sources") or []) if str(x).strip()],
                "confidence":max(0.0,min(float(item.get("confidence") or 0.0),1.0)),
                "knowledge_track":str(item.get("knowledge_track") or "general")[:80],
                "status":str(item.get("status") or "candidate")[:80],
            })
        return {
            "summary":str(data.get("summary") or "")[:6000],
            "findings":findings,
            "successful_methods":[str(x).strip()[:2000] for x in (data.get("successful_methods") or []) if str(x).strip()],
            "failed_approaches":[str(x).strip()[:2000] for x in (data.get("failed_approaches") or []) if str(x).strip()],
            "corrections":[str(x).strip()[:2000] for x in (data.get("corrections") or []) if str(x).strip()],
            "reusable_skills":[str(x).strip()[:1200] for x in (data.get("reusable_skills") or []) if str(x).strip()],
            "evaluation_results":[str(x).strip()[:2000] for x in (data.get("evaluation_results") or []) if str(x).strip()],
            "unresolved_questions":[str(x).strip()[:2000] for x in (data.get("unresolved_questions") or []) if str(x).strip()],
            "cross_domain_relationships":[str(x).strip()[:2000] for x in (data.get("cross_domain_relationships") or []) if str(x).strip()],
        }

    def absorb_shishya(self,mission_id,batch,parent_rishi=None):
        m=self.mission(mission_id)
        parent=str(parent_rishi or batch.get("parent_rishi") or m["lead_rishi"]).strip().lower()
        self.council.get(parent)
        receipt={
            "mission_id":mission_id,"parent_rishi":parent,
            "batch_id":batch.get("batch_id") or batch.get("tree_id"),
            "tree_id":batch.get("tree_id"),
            "node_count":int(batch.get("node_count") or len(batch.get("workers") or [])),
            "max_depth_reached":int(batch.get("max_depth_reached") or 1),
            "level_counts":dict(batch.get("level_counts") or {}),
            "edges":list(batch.get("edges") or []),
            "tree_budget":dict(batch.get("budget") or {}),
            "all_nodes_destroyed":bool(batch.get("all_nodes_destroyed",batch.get("destroyed"))),
            "destroyed":bool(batch.get("destroyed")),"destroyed_at":batch.get("destroyed_at"),
            "retention_policy":"findings_and_provenance_only","workers":[],
            "findings":[],"failed_approaches":[],"unresolved_questions":[],
            "retired_at":self._now(),
        }
        if not receipt["destroyed"] or not receipt["all_nodes_destroyed"]:
            raise RuntimeError("Shishya tree cannot be absorbed before every temporary worker is destroyed")
        for worker in batch.get("workers") or []:
            handover=self._parse_shishya_result(worker.get("result"))
            receipt["workers"].append({
                "worker_id_hash":worker.get("worker_id_hash"),
                "parent_worker_hash":worker.get("parent_worker_hash"),
                "tree_depth":int(worker.get("tree_depth") or 1),
                "delegation_reason":worker.get("delegation_reason"),
                "specialty":worker.get("specialty"),
                "assignment":worker.get("assignment"),
                "provider":worker.get("provider"),"model":worker.get("model"),
                "security":worker.get("security"),
                "started_at":worker.get("started_at"),"ended_at":worker.get("ended_at"),
                "handover":handover,
            })
            for finding in handover.get("findings") or []:
                receipt["findings"].append({**finding,"specialty":worker.get("specialty")})
            receipt["failed_approaches"].extend(handover.get("failed_approaches") or [])
            receipt["unresolved_questions"].extend(handover.get("unresolved_questions") or [])
        with self.lock:
            self.state["shishya_archive"].append(receipt)
            self.state["shishya_archive"]=self.state["shishya_archive"][-1000:]
            self.state["missions"][mission_id]["shishya_batches"].append(receipt["batch_id"])
            self.state["missions"][mission_id]["updated_at"]=self._now();self._save()
        self.memory.remember(m["project"],"brahmagyan_shishya_handover",m["topic"],receipt)
        return receipt

    def status(self):
        with self.lock:
            missions=len(self.state["missions"]);claims=len(self.state["claims"]);debates=len(self.state.get("debates") or {});curiosity=len([x for x in self.state["curiosity"] if x.get("status")=="queued"])
        return {
            "name":"BRAHMAGYAN","version":self.VERSION,"purpose":"autonomous universal-learning and research intelligence",
            "maturity_levels":[{"code":c,"name":n} for c,n in MATURITY],
            "research_phases":[{"code":c,"name":n} for c,n in RESEARCH_PHASES],
            "deep_learning_loop":["discover","read","understand_context","extract_claims","verify_sources","cross_check","find_contradictions","apply","test","evaluate","connect","store"],
            "missions":missions,"claims":claims,"debates":debates,"curiosity_queued":curiosity,
            "council_proposals":len(self.state.get("council_proposals") or []),
            "council":self.council.status(),
            "trusted_store":"Gyan-Bhandar","authority":"Sudarshan permissioned Action/Job architecture",
            "research_guardrails":[
                "multi-perspective retrieval is not independent evidence",
                "debate is selective and evidence-linked, not mandatory",
                "citation verification is named and auditable, not treated as infallible truth",
                "modern and Vedic/classical evidence tracks remain separately labeled",
            ],
            "resource_policy":"council profiles are inert; workers are mission-scoped and temporary; no background daemon",
        }
