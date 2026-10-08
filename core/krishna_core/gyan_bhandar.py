from __future__ import annotations
from collections import Counter
from urllib.parse import urlparse
import re, time, uuid, hashlib, json, zlib
from pathlib import Path

from .rishi_gyan_sagar import RishiGyanSagar
from .rishi_deep_sources import RishiDeepSourceExpansion


class GyanBhandarAgent:
    """Evidence-backed knowledge curator. Stores and strengthens theory; KRISHNA remains decision authority."""
    def __init__(self, memory, garuda):
        self.memory=memory; self.garuda=garuda
        state=Path(self.memory.db.execute("PRAGMA database_list").fetchone()[2]).resolve().parent/".krishna_state"
        self.archive_root=state/"gyan_archive"; self.archive_root.mkdir(parents=True,exist_ok=True)
        self.archive_index=self.archive_root/"index.jsonl"
        self.rights_index=self.archive_root/"rights.jsonl"
        self.knowledge_rights=RishiGyanSagar()
        self.deep_sources=RishiDeepSourceExpansion()

    def archive_file(self, project, source_path, topic="", remove_original=False):
        src=Path(source_path).resolve()
        if not src.is_file():raise FileNotFoundError(str(src))
        raw=src.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
        target=self.archive_root/(digest+".zlib")
        deduplicated=target.exists()
        if not deduplicated:target.write_bytes(zlib.compress(raw,9))
        record={"sha256":digest,"project":project,"topic":str(topic or src.name)[:240],"name":src.name,
            "original_bytes":len(raw),"archive_bytes":target.stat().st_size,"archive":str(target),
            "compression":"zlib-9","created_at":time.time(),"deduplicated":deduplicated}
        with self.archive_index.open("a",encoding="utf-8") as h:h.write(json.dumps(record,separators=(",",":"))+"\n")
        if remove_original:src.unlink()
        self.memory.audit("gyan_file_archive","completed",f"{project}:{digest}:{record['original_bytes']}->{record['archive_bytes']}")
        return {k:v for k,v in record.items() if k!="archive"}

    def _knowledge_source_policy(self,source_id,source_default_max_mode="read"):
        sid=str(source_id or "").strip().lower()
        if not sid:
            return {"id":"unknown","default_max_mode":str(source_default_max_mode or "read"),
                    "per_item_rights_required":True,"family":"unknown"}
        try:return self.knowledge_rights.source(sid)
        except KeyError:
            try:return self.deep_sources.source(sid)
            except KeyError:
                return {"id":sid,"default_max_mode":str(source_default_max_mode or "read"),
                        "per_item_rights_required":True,"family":"unregistered"}

    def knowledge_rights_gate(self,requested_mode,*,source_id="",license_id="",source_default_max_mode="read",
                              commercial_context=True,explicit_permission=False):
        policy=self._knowledge_source_policy(source_id,source_default_max_mode)
        decision=self.knowledge_rights.rights_decision(
            requested_mode,
            license_id=str(license_id or ""),
            source_default_max_mode=str(policy.get("default_max_mode") or source_default_max_mode or "read"),
            commercial_context=bool(commercial_context),
            explicit_permission=bool(explicit_permission),
        )
        problems=[]
        mode=str(requested_mode or "").strip().lower()
        if mode in {"archive","train"} and bool(policy.get("per_item_rights_required",True)) and not str(license_id or "").strip() and not explicit_permission:
            problems.append("item licence/rights statement is required before full-content archival or training")
        allowed=bool(decision.allowed) and not problems
        return {"allowed":allowed,"source_id":policy.get("id") or source_id,"source_policy":policy,
                "rights":decision.public(),"problems":problems,
                "policy":"external Rishi corpus content must pass this gate before full-content archive/train promotion"}

    def archive_knowledge_file(self,project,source_path,*,topic="",source_id="",license_id="",
                               source_default_max_mode="read",source_url="",identifier="",authors=None,
                               commercial_context=True,explicit_permission=False,remove_original=False,provenance=None):
        gate=self.knowledge_rights_gate(
            "archive",source_id=source_id,license_id=license_id,
            source_default_max_mode=source_default_max_mode,
            commercial_context=commercial_context,explicit_permission=explicit_permission,
        )
        if not gate["allowed"]:
            self.memory.audit("gyan_knowledge_archive","rights_blocked",
                              f"{project}:{gate['source_id']}:{gate['rights'].get('reason')}:{'; '.join(gate['problems'])}")
            raise PermissionError("knowledge archive blocked by rights gate: "+
                                  "; ".join(gate["problems"] or [gate["rights"].get("reason") or "rights not verified"]))
        archived=self.archive_file(project,source_path,topic,remove_original=remove_original)
        rights_record={
            "sha256":archived["sha256"],"project":str(project),"topic":str(topic or archived.get("name") or "")[:240],
            "source_id":gate["source_id"],"source_url":str(source_url or "")[:2000],
            "identifier":str(identifier or "")[:500],"authors":[str(x)[:300] for x in (authors or [])],
            "license_id":str(license_id or "")[:200],"requested_mode":"archive","rights":gate["rights"],
            "source_policy":{"id":gate["source_policy"].get("id"),"family":gate["source_policy"].get("family"),
                             "default_max_mode":gate["source_policy"].get("default_max_mode"),
                             "per_item_rights_required":gate["source_policy"].get("per_item_rights_required")},
            "provenance":dict(provenance or {}),"created_at":time.time(),
        }
        with self.rights_index.open("a",encoding="utf-8") as h:
            h.write(json.dumps(rights_record,ensure_ascii=False,separators=(",",":"))+"\n")
        self.memory.audit("gyan_knowledge_archive","completed",f"{project}:{gate['source_id']}:{archived['sha256']}")
        return {**archived,"knowledge_source":rights_record,"rights_verified":True}

    def training_candidate_gate(self,source_path,*,source_id="",license_id="",source_default_max_mode="read",
                                commercial_context=True,explicit_permission=False):
        src=Path(source_path).resolve()
        if not src.is_file():raise FileNotFoundError(str(src))
        digest=hashlib.sha256(src.read_bytes()).hexdigest()
        gate=self.knowledge_rights_gate(
            "train",source_id=source_id,license_id=license_id,
            source_default_max_mode=source_default_max_mode,
            commercial_context=commercial_context,explicit_permission=explicit_permission,
        )
        result={**gate,"sha256":digest,"bytes":src.stat().st_size,
                "training_allowed":bool(gate["allowed"] and gate["rights"].get("training_allowed") is True),
                "next_action":"candidate may enter a separately approved training corpus" if gate["allowed"] and gate["rights"].get("training_allowed") is True else "keep out of training corpus"}
        self.memory.audit("gyan_training_candidate","allowed" if result["training_allowed"] else "blocked",
                          f"{gate['source_id']}:{digest}:{gate['rights'].get('reason')}")
        return result

    def restore_file(self, sha256, destination):
        digest=str(sha256).lower().strip()
        if not re.fullmatch(r"[0-9a-f]{64}",digest):raise ValueError("invalid sha256")
        src=self.archive_root/(digest+".zlib")
        if not src.is_file():raise FileNotFoundError(digest)
        raw=zlib.decompress(src.read_bytes())
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("archive integrity check failed")
        dst=Path(destination).resolve(); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(raw)
        return {"sha256":digest,"destination":str(dst),"bytes":len(raw),"verified":True}

    def archive_status(self):
        files=list(self.archive_root.glob("*.zlib"))
        rights_records=0
        if self.rights_index.is_file():
            try:
                with self.rights_index.open("r",encoding="utf-8") as h:rights_records=sum(1 for line in h if line.strip())
            except OSError:rights_records=0
        return {"agent":"Gyan-Bhandar","files":len(files),"compressed_bytes":sum(x.stat().st_size for x in files),
            "rights_verified_knowledge_records":rights_records,
            "policy":"content-addressed SHA-256 archive; external Rishi corpus content uses a separate rights gate/index; duplicate files stored once; originals are retained unless explicit removal is requested"}

    @staticmethod
    def _terms(text):
        return {x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}",str(text).lower()) if len(x)>2}

    def store(self, project, topic, lesson, evidence=None, confidence=0.0, source="sudarshan", verified=False,
              memory_kind="semantic", provenance=None, supersedes=None):
        item=self.memory.learn(project,topic,lesson,evidence or [],confidence,source,verified,memory_kind,provenance,supersedes)
        self.memory.audit("gyan_bhandar_store","verified" if verified else "candidate",
            f"{project}:{item['fingerprint']}:{memory_kind}")
        return item

    def propose(self, project, topic, lesson, evidence=None, confidence=0.0, source="research", verified=False,
                memory_kind="semantic", provenance=None, supersedes=None):
        approval_id=str(uuid.uuid4())
        item=self.memory.create_gyan_pending(approval_id,project,topic,lesson,evidence or [],confidence,source,verified,
                                             memory_kind,provenance,supersedes)
        self.memory.audit("gyan_bhandar_proposal","waiting_approval",f"{project}:{approval_id}:{topic}:{memory_kind}")
        return {**item,"stored":False,"requires_user_approval":True,
            "question":"Save these findings to Gyan-Bhandar?"}

    def pending(self, project=None, limit=100):
        return self.memory.list_gyan_pending(project,"pending",limit)

    def decide(self, approval_id, approved):
        item=self.memory.gyan_pending(approval_id)
        if not item or item.get("status")!="pending":raise KeyError(approval_id)
        if not approved:
            out=self.memory.decide_gyan_pending(approval_id,"rejected")
            self.memory.audit("gyan_bhandar_proposal","rejected",approval_id)
            return {**out,"stored":False}
        stored=self.store(item["project"],item["topic"],item["lesson"],item["evidence"],item["confidence"],item["source"],item["verified"],
                          item.get("memory_kind","semantic"),item.get("provenance") or {},item.get("supersedes"))
        out=self.memory.decide_gyan_pending(approval_id,"approved")
        self.memory.audit("gyan_bhandar_proposal","approved",approval_id)
        return {**out,"stored":True,"learning":stored}

    def compact_storage(self):
        result=self.memory.compact_gyan_storage()
        self.memory.audit("gyan_bhandar_compact","completed",f"{result['records_compacted']} records; {result['bytes_saved']} bytes saved")
        return {"agent":"Gyan-Bhandar",**result}

    def recall(self, project, topic=None, limit=50, verified_only=False, memory_kind=None, include_superseded=False):
        rows=self.memory.learnings(project,limit,verified_only,memory_kind,include_superseded)
        if topic:
            wanted=self._terms(topic)
            rows.sort(key=lambda x:len(wanted & self._terms(x["topic"]+" "+x["lesson"])),reverse=True)
        return rows

    def inventory(self, project):
        out=self.memory.learning_inventory(project)
        out["agent"]="Gyan-Bhandar"
        out["policy"]="working / episodic / semantic / graph / skill / evidence with provenance and supersession"
        return out

    def supersede(self, project, fingerprint, topic, lesson, evidence=None, confidence=0.0, source="krishna",
                  verified=False, memory_kind="semantic", provenance=None):
        old=[x for x in self.memory.learnings(project,500,False,None,True) if x.get("fingerprint")==fingerprint]
        if not old: raise KeyError(fingerprint)
        proposal=self.propose(project,topic,lesson,evidence or [],confidence,source,verified,memory_kind,provenance,fingerprint)
        self.memory.audit("gyan_bhandar_supersession","waiting_approval",f"{project}:{fingerprint}->{proposal['approval_id']}")
        return proposal

    def theory(self, project, topic, limit=25):
        rows=self.recall(project,topic,limit=limit)
        verified=[x for x in rows if x.get("status")=="verified"]
        candidates=[x for x in rows if x.get("status")!="verified"]
        evidence=[]; domains=Counter()
        for row in rows:
            for ev in row.get("evidence") or []:
                if isinstance(ev,dict):
                    u=str(ev.get("url") or "")
                    if u:
                        domains[urlparse(u).netloc or "local"]+=1
                    evidence.append(ev)
        return {"agent":"Gyan-Bhandar","project":project,"topic":topic,
            "theory":{"verified_lessons":[x["lesson"] for x in verified[:8]],"candidate_lessons":[x["lesson"] for x in candidates[:8]],
                "implementation_rule":"Verified lessons may inform KRISHNA decisions; candidate lessons require evidence or tests before promotion.",
                "evidence_count":len(evidence),"independent_domains":len(domains),"domains":dict(domains)},
            "decision_authority":"KRISHNA","implementation_executor":"Sudarshan"}

    def strengthen(self, project, topic, use_garuda=True, limit=10):
        existing=self.recall(project,topic,limit=50)
        research=None
        if use_garuda:
            research=self.garuda.scout(project,f"{topic} architecture implementation theory evidence alternatives risks",limit)
        source_counts=Counter()
        evidence=[]
        if research:
            for row in research.get("web",[]):
                if not row.get("suspicious"):
                    source_counts[row.get("source","web")]+=1
                    evidence.append({"title":row.get("title"),"url":row.get("url"),"source":row.get("source"),"fingerprint":row.get("fingerprint")})
            for row in research.get("github",[]):
                source_counts["github"]+=1
                evidence.append({"repository":row.get("full_name"),"url":row.get("html_url") or row.get("url"),"source":"github"})
        result={
            "agent":"Gyan-Bhandar","project":project,"topic":topic,
            "existing_learnings":existing,
            "current_theory":self.theory(project,topic,limit=50),
            "new_evidence":evidence[:max(10,limit*3)],
            "source_diversity":dict(source_counts),
            "theory_status":"evidence_collected" if evidence else "memory_only",
            "handover":{
                "to":"KRISHNA","decision_authority":"KRISHNA","auto_implementation":False,
                "implementation_executor":"Sudarshan",
                "required_before_use":["compare existing learning","inspect evidence","identify contradictions","form implementation theory","verify in shadow/tests"]
            },
            "created_at":time.time()
        }
        self.memory.remember(project,"gyan_bhandar_analysis",topic,{"analysis":result})
        self.memory.audit("gyan_bhandar_strengthen","completed",f"{project}:{topic}:{len(evidence)} evidence")
        return result
