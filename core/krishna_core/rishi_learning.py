from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import RLock


# These are KRISHNA design assignments. They are not claims that the historical
# or traditional figures practiced the listed modern sciences.
RISHI_RESEARCH_CHARTERS = {
    "veda-vyasa": {
        "primary_subjects": (
            "knowledge architecture","research synthesis","history of science","civilizations",
            "scriptures and textual traditions","literature","biography","ontology","knowledge graphs",
            "research provenance","scientific timelines","cross-domain synthesis",
        ),
        "frontier_focus": (
            "connect verified findings across fields","preserve disagreement and version history",
            "detect duplicated knowledge","build reusable knowledge maps",
        ),
        "classical_lens": (
            "four Vedas as a corpus","Brahmanas","Aranyakas","principal Upanishads",
            "textual chronology","recensions","commentarial provenance",
        ),
    },
    "vashistha": {
        "primary_subjects": (
            "ethics","governance","law","leadership","social systems","public policy",
            "organizational design","responsible technology","technology governance",
            "risk-benefit governance","civilizational studies",
        ),
        "frontier_focus": (
            "long-term consequences","rights and responsibilities","fairness and public impact",
            "governance of powerful technologies",
        ),
        "classical_lens": (
            "Vedic and Upanishadic ethical themes","dharma traditions in historical context",
            "classical governance and social thought as comparative history",
        ),
    },
    "vishwamitra": {
        "primary_subjects": (
            "artificial intelligence","robotics","space technology","quantum technology",
            "frontier engineering","energy technology","emerging materials","inventions",
            "patents","autonomous systems","human-machine interfaces","future technologies",
        ),
        "frontier_focus": (
            "what has newly become technically possible","cross-field invention",
            "new tools and repositories","high-upside emerging research",
        ),
        "classical_lens": (
            "Vedic technological and material-culture references as historical evidence only",
            "classical innovation narratives with provenance review",
        ),
    },
    "sushruta": {
        "primary_subjects": (
            "anatomy","physiology","surgery","pathology","diagnostics","medical devices",
            "biomedical engineering","biomechanics","neural engineering","medical imaging",
            "bioimaging","biomaterials","clinical engineering","radiation medicine",
            "clinical research","regenerative medicine","tissue engineering",
        ),
        "frontier_focus": (
            "repair and restoration of biological function","safer surgical and device methods",
            "diagnostic accuracy","translation from preclinical to human evidence",
        ),
        "classical_lens": (
            "Ayurvedic surgical and anatomical literature as historical medical sources",
            "Atharvavedic health-related material as historical textual evidence",
            "Upanishadic body/life concepts only as philosophical context",
        ),
    },
    "kashyapa": {
        "primary_subjects": (
            "biology","genetics","DNA","genomics","epigenetics","molecular biology",
            "reproduction","embryology","developmental biology","pediatrics","evolution",
            "zoology","botany","ecology","microbiology","biodiversity","stem-cell biology",
            "gene regulation","aging biology","systems biology",
        ),
        "frontier_focus": (
            "gene-to-phenotype mechanisms","natural variation","development and inheritance",
            "aging and regeneration","organism-environment interactions",
        ),
        "classical_lens": (
            "Vedic and Upanishadic life/reproduction themes as historical or philosophical material",
            "classical Indian life-science traditions with source chronology preserved",
        ),
    },
    "atri": {
        "primary_subjects": (
            "astronomy","astrophysics","cosmology","solar physics","planetary science",
            "earth observation","remote sensing","timekeeping","calendars","measurement science",
            "space observation","geodesy",
        ),
        "frontier_focus": (
            "new observations","measurement uncertainty","anomalous astronomical data",
            "planetary and solar dynamics","observation-model disagreement",
        ),
        "classical_lens": (
            "Vedic calendrical and astronomical references as history of observation",
            "Vedanga Jyotisha and later astronomical traditions as separate historical tracks",
        ),
    },
    "gautama": {
        "primary_subjects": (
            "logic","epistemology","statistics","probability","causality","scientific inference",
            "research methodology","replication","bias","fact checking","source independence",
            "argument analysis","evidence grading","meta-science",
        ),
        "frontier_focus": (
            "how we know","falsification","causal identification","replication failure",
            "false consensus","measurement and inferential error",
        ),
        "classical_lens": (
            "Nyaya reasoning traditions","Upanishadic dialogue as historical argumentation",
            "classical epistemic categories compared without equating them to modern statistics",
        ),
    },
    "jamadagni": {
        "primary_subjects": (
            "defensive cybersecurity","software security","AI security","system resilience",
            "failure analysis","incident response","disaster recovery","reliability engineering",
            "supply-chain security","data integrity","safety engineering","fault tolerance",
        ),
        "frontier_focus": (
            "how systems fail","adversarial testing","recovery","unexpected interaction risk",
            "security of autonomous systems",
        ),
        "classical_lens": (
            "Vedic/classical protection and resilience themes as cultural history",
            "classical statecraft only as comparative historical material",
        ),
    },
    "bharadvaja": {
        "primary_subjects": (
            "scientific method","experimental design","engineering methodology","testing",
            "benchmarking","simulation","education","learning science","knowledge transfer",
            "measurement design","research reproducibility","applied science",
        ),
        "frontier_focus": (
            "how to test a hypothesis","better experiment design","benchmark construction",
            "transfer from theory to measurable application",
        ),
        "classical_lens": (
            "Vedanga/Kalpa procedural traditions as history of structured method",
            "classical pedagogical practices as comparative learning history",
        ),
    },
    "kanada": {
        "primary_subjects": (
            "physics","chemistry","materials science","atomic physics","molecular science",
            "condensed matter","nanoscience","thermodynamics","mechanics","electromagnetism",
            "physical properties","metrology","scientific ontology","matter classification",
        ),
        "frontier_focus": (
            "new states and properties of matter","materials mechanisms","physical models",
            "measurement-model mismatch","cross-scale physics",
        ),
        "classical_lens": (
            "Vaisheshika categories and atomism as history of philosophy",
            "Vedic/Upanishadic ontology as philosophical comparison, never modern-physics evidence",
        ),
    },
    "kapila": {
        "primary_subjects": (
            "systems thinking","complex systems","cognitive science","psychology",
            "philosophy of mind","consciousness","emergence","computational cognition",
            "decision processes","systems neuroscience","human cognition",
        ),
        "frontier_focus": (
            "emergent mechanisms","mind-brain models","system-level causation",
            "multi-scale cognition","consciousness theories",
        ),
        "classical_lens": (
            "Samkhya as a classical philosophical system","Upanishadic mind/self discussions",
            "comparisons kept distinct from modern cognitive-neuroscience evidence",
        ),
    },
    "patanjali": {
        "primary_subjects": (
            "attention","meditation","cognitive control","human performance","mental discipline",
            "behavioral training","yoga research","psychophysiology","breathing practices",
            "mind-body research","language structure",
        ),
        "frontier_focus": (
            "trainability of attention","neural and physiological correlates of practice",
            "performance adaptation","mind-body mechanisms",
        ),
        "classical_lens": (
            "Yoga traditions","Katha, Prashna, Mandukya and other Upanishadic mind/practice passages",
            "traditional practice separated from psychological, neurological and clinical evidence",
        ),
    },
    "yajnavalkya": {
        "primary_subjects": (
            "epistemology","philosophy","consciousness","self","metaphysics","concept formation",
            "philosophy of science","debate","ontology","foundations of knowledge",
        ),
        "frontier_focus": (
            "hidden assumptions","definition failure","limits of explanation",
            "consciousness and self models","conceptual contradictions",
        ),
        "classical_lens": (
            "Brihadaranyaka Upanishad","Isha Upanishad","major Upanishadic dialogues",
            "self/reality/knowledge themes with textual provenance preserved",
        ),
    },
    "agastya": {
        "primary_subjects": (
            "environment","climate","ecology","knowledge transmission","regional traditions",
            "language and culture","civilizations","history of ideas","cultural exchange",
            "historical technology","environmental history","cross-domain diffusion",
        ),
        "frontier_focus": (
            "how knowledge moves between cultures","environment-civilization interaction",
            "regional evidence","cross-disciplinary transmission",
        ),
        "classical_lens": (
            "Vedic transmission traditions","regional textual traditions",
            "environmental and cultural passages with date/layer distinctions",
        ),
    },
    "charaka": {
        "primary_subjects": (
            "internal medicine","preventive medicine","physiology","nutrition","pharmacology",
            "public health","disease progression","metabolism","lifestyle research",
            "aging medicine","chronic disease","therapeutics","clinical prevention",
        ),
        "frontier_focus": (
            "disease mechanisms","prevention","systemic physiology","healthy aging",
            "drug and lifestyle evidence","risk-factor modification",
        ),
        "classical_lens": (
            "Ayurvedic medical literature as historical medical tradition",
            "Atharvavedic health material as historical source",
            "modern clinical claims remain governed by modern clinical evidence",
        ),
    },
    "panini": {
        "primary_subjects": (
            "linguistics","grammar","Sanskrit","Indian languages","phonetics","morphology",
            "syntax","semantics","NLP","language models","parsing","translation",
            "computational linguistics","textual criticism",
        ),
        "frontier_focus": (
            "formal language structure","high-precision translation","machine parsing",
            "multilingual reasoning","historical language change",
        ),
        "classical_lens": (
            "Vedic Sanskrit","Vedanga Shiksha","Vyakarana","Nirukta",
            "philology and translation quality for Vedic/Upanishadic source work",
        ),
    },
}

CLASSICAL_SOURCE_REGISTRY = {
    "source_authority": "Vedic Heritage Portal, IGNCA / Ministry of Culture, Government of India",
    "base_url": "https://vedicheritage.gov.in/",
    "layers": (
        "Rigveda","Yajurveda","Samaveda","Atharvaveda",
        "Brahmanas","Aranyakas","Upanishads","Vedangas",
    ),
    "principal_upanishads": (
        "Isha","Kena","Katha","Prashna","Mundaka","Mandukya",
        "Taittiriya","Aitareya","Chandogya","Brihadaranyaka",
        "Shvetashvatara","Kaushitaki","Maitrayaniya",
    ),
    "policy": (
        "classical material is a separately labeled textual/historical/philosophical evidence track; "
        "symbolic, metaphysical or traditional passages never count as experimental proof of a modern scientific claim"
    ),
}


class RishiLearningLedger:
    VERSION = "rishi-learning-v1"

    def __init__(self,state_root,council,memory=None):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"rishi-learning.json"
        self.council=council
        self.memory=memory
        self.lock=RLock()
        self.state={"version":self.VERSION,"rishis":{},"collaborations":{},"created_at":time.time()}
        self._load()
        self._ensure_profiles()

    def _load(self):
        if not self.path.is_file():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw,dict):
                self.state.update(raw)
                self.state.setdefault("rishis",{})
                self.state.setdefault("collaborations",{})
        except Exception as exc:
            if self.memory:self.memory.audit("rishi_learning","load_failed",f"{type(exc).__name__}: {exc}")

    def _save(self):
        tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,self.path)

    def _ensure_profiles(self):
        changed=False
        with self.lock:
            for profile in self.council.list():
                rid=profile["id"]
                row=self.state["rishis"].setdefault(rid,{
                    "rishi_id":rid,
                    "display_name":profile["display_name"],
                    "role":profile["role"],
                    "topics":{},
                    "findings":[],
                    "open_questions":[],
                    "missions":[],
                    "collaborations":[],
                    "last_learned_at":None,
                    "created_at":time.time(),
                })
                row["display_name"]=profile["display_name"]
                row["role"]=profile["role"]
                charter=RISHI_RESEARCH_CHARTERS.get(rid,{})
                row["charter"]={
                    "primary_subjects":list(charter.get("primary_subjects") or profile.get("domains") or []),
                    "frontier_focus":list(charter.get("frontier_focus") or []),
                    "classical_lens":list(charter.get("classical_lens") or []),
                }
                changed=True
            if changed:self._save()

    @staticmethod
    def _terms(text):
        return {x.strip(".,:;()[]{}!?").lower() for x in str(text or "").split() if len(x.strip(".,:;()[]{}!?"))>=4}

    def charter(self,rishi_id):
        rid=str(rishi_id or "").strip().lower()
        self.council.get(rid)
        return json.loads(json.dumps(self.state["rishis"][rid]["charter"]))

    def topic_matrix(self):
        rows=[]
        for profile in self.council.list():
            rid=profile["id"];charter=self.charter(rid)
            rows.append({
                "rishi_id":rid,
                "display_name":profile["display_name"],
                "role":profile["role"],
                "primary_subjects":charter["primary_subjects"],
                "frontier_focus":charter["frontier_focus"],
                "classical_lens":charter["classical_lens"],
            })
        return {
            "rishis":rows,
            "classical_sources":dict(CLASSICAL_SOURCE_REGISTRY),
            "policy":"subject ownership means KRISHNA research responsibility, not historical authorship of modern fields",
        }

    def record_finding(self,rishi_id,topic,claim,*,claim_id=None,mission_id=None,track="general",
                       maturity="L0",evidence_status="unknown",confidence=0.0,source_count=0,
                       unresolved=False,role="researcher"):
        rid=str(rishi_id or "").strip().lower()
        self.council.get(rid)
        topic=str(topic or "").strip()
        claim=str(claim or "").strip()
        if not topic or not claim:raise ValueError("topic and claim are required")
        finding={
            "finding_id":str(uuid.uuid4()),
            "topic":topic,
            "claim":claim[:4000],
            "claim_id":str(claim_id or "") or None,
            "mission_id":str(mission_id or "") or None,
            "knowledge_track":str(track or "general"),
            "maturity":str(maturity or "L0"),
            "evidence_status":str(evidence_status or "unknown"),
            "confidence":max(0.0,min(float(confidence or 0.0),1.0)),
            "source_count":max(0,int(source_count or 0)),
            "unresolved":bool(unresolved),
            "role":str(role or "researcher"),
            "learned_at":time.time(),
        }
        with self.lock:
            row=self.state["rishis"][rid]
            key=topic.lower()
            t=row["topics"].setdefault(key,{
                "topic":topic,"research_count":0,"finding_ids":[],"mission_ids":[],
                "last_researched_at":None,
            })
            t["research_count"]=int(t.get("research_count") or 0)+1
            t["last_researched_at"]=finding["learned_at"]
            t["finding_ids"].append(finding["finding_id"]);t["finding_ids"]=t["finding_ids"][-300:]
            if mission_id and str(mission_id) not in t["mission_ids"]:
                t["mission_ids"].append(str(mission_id));t["mission_ids"]=t["mission_ids"][-100:]
            row["findings"].append(finding);row["findings"]=row["findings"][-2000:]
            if mission_id and str(mission_id) not in row["missions"]:
                row["missions"].append(str(mission_id));row["missions"]=row["missions"][-500:]
            row["last_learned_at"]=finding["learned_at"]
            self._save()
        return dict(finding)

    def add_open_question(self,rishi_id,topic,question,mission_id=None):
        rid=str(rishi_id or "").strip().lower();self.council.get(rid)
        q=str(question or "").strip()
        if not q:raise ValueError("question is required")
        item={"id":str(uuid.uuid4()),"topic":str(topic or ""),"question":q[:2000],
              "mission_id":str(mission_id or "") or None,"status":"open","created_at":time.time()}
        with self.lock:
            self.state["rishis"][rid]["open_questions"].append(item)
            self.state["rishis"][rid]["open_questions"]=self.state["rishis"][rid]["open_questions"][-1000:]
            self._save()
        return dict(item)

    def knowledge_packet(self,rishi_id,topic,limit=12):
        rid=str(rishi_id or "").strip().lower();self.council.get(rid)
        topic_terms=self._terms(topic)
        with self.lock:
            row=json.loads(json.dumps(self.state["rishis"][rid]))
        scored=[]
        for finding in row.get("findings") or []:
            overlap=len(topic_terms & self._terms(f"{finding.get('topic')} {finding.get('claim')}"))
            if overlap:scored.append((overlap,float(finding.get("confidence") or 0.0),finding))
        scored.sort(key=lambda x:(-x[0],-x[1],-float(x[2].get("learned_at") or 0)))
        findings=[x[2] for x in scored[:max(1,min(int(limit),50))]]
        questions=[]
        for item in row.get("open_questions") or []:
            if item.get("status")!="open":continue
            if topic_terms & self._terms(f"{item.get('topic')} {item.get('question')}"):
                questions.append(item)
        return {
            "rishi_id":rid,
            "display_name":row["display_name"],
            "role":row["role"],
            "charter":row["charter"],
            "matching_findings":findings,
            "open_questions":questions[:20],
            "classical_lens":row["charter"].get("classical_lens") or [],
        }

    def ingest_mission(self,brahmagyan,mission_id,synthesis=None,all_council=True):
        mission=brahmagyan.mission(mission_id)
        claims=[brahmagyan.claim(x) for x in mission.get("claim_ids") or []]
        participants={mission["lead_rishi"]}
        participants.update(x.get("rishi_id") for x in mission.get("perspectives") or [] if x.get("rishi_id"))
        if all_council:participants.update(x["id"] for x in self.council.list())
        learned=[]
        for rid in participants:
            if not rid:continue
            is_direct=(rid==mission["lead_rishi"] or any(x.get("rishi_id")==rid for x in mission.get("perspectives") or []))
            role="lead" if rid==mission["lead_rishi"] else ("active_collaborator" if is_direct else "council_knowledge_support")
            if claims:
                for claim in claims:
                    all_evidence=(list(claim.get("sources") or [])+list(claim.get("supporting_evidence") or [])+
                                  list(claim.get("qualifying_evidence") or [])+list(claim.get("contradicting_evidence") or []))
                    finding=self.record_finding(
                        rid,mission["topic"],claim["claim"],claim_id=claim["claim_id"],
                        mission_id=mission_id,track=claim.get("knowledge_track"),
                        maturity=claim.get("maturity"),evidence_status=claim.get("evidence_status"),
                        confidence=claim.get("confidence"),source_count=len(all_evidence),
                        unresolved=bool([x for x in claim.get("contradicting_evidence") or [] if not x.get("resolved_at")]),
                        role=role,
                    )
                    learned.append(finding)
            if synthesis and not claims:
                learned.append(self.record_finding(
                    rid,mission["topic"],str(synthesis),mission_id=mission_id,
                    maturity=mission.get("maturity","L0"),role=role,
                ))
        return {"mission_id":mission_id,"participants":sorted(participants),"findings_recorded":len(learned)}

    def profile(self,rishi_id,topic=None,limit=50):
        rid=str(rishi_id or "").strip().lower();self.council.get(rid)
        with self.lock:row=json.loads(json.dumps(self.state["rishis"][rid]))
        if topic:
            packet=self.knowledge_packet(rid,topic,limit)
            row["matching_findings"]=packet["matching_findings"]
            row["matching_open_questions"]=packet["open_questions"]
        row["finding_count"]=len(row.get("findings") or [])
        row["topic_count"]=len(row.get("topics") or {})
        row["mission_count"]=len(row.get("missions") or [])
        row["findings"]=(row.get("findings") or [])[-max(1,min(int(limit),200)):]
        return row

    def next_learning_assignment(self):
        """Balance autonomous learning across the permanent council first."""
        with self.lock:
            snapshot=json.loads(json.dumps(self.state["rishis"]))
        candidates=[]
        for profile in self.council.list():
            rid=profile["id"];row=snapshot[rid]
            subjects=list((row.get("charter") or {}).get("primary_subjects") or profile.get("domains") or [])
            if not subjects:continue
            topic_rows=row.get("topics") or {}
            best_subject=min(
                subjects,
                key=lambda s:(
                    int((topic_rows.get(str(s).lower()) or {}).get("research_count") or 0),
                    float((topic_rows.get(str(s).lower()) or {}).get("last_researched_at") or 0),
                    str(s),
                ),
            )
            candidates.append((
                len(row.get("findings") or []),
                len(topic_rows),
                float(row.get("last_learned_at") or 0),
                rid,
                best_subject,
            ))
        if not candidates:return None
        candidates.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
        _,_,_,rid,subject=candidates[0]
        row=snapshot[rid]
        return {
            "rishi_id":rid,
            "display_name":row["display_name"],
            "role":row["role"],
            "subject":subject,
            "finding_count":len(row.get("findings") or []),
            "topic_count":len(row.get("topics") or {}),
            "bootstrap_complete":all(len(x.get("findings") or [])>0 for x in snapshot.values()),
            "policy":"least-trained Rishi and least-researched charter subject are prioritized before repeating well-covered subjects",
        }

    def bootstrap_status(self):
        with self.lock:snapshot=json.loads(json.dumps(self.state["rishis"]))
        rows=[]
        for profile in self.council.list():
            row=snapshot[profile["id"]]
            rows.append({
                "rishi_id":profile["id"],"display_name":profile["display_name"],
                "finding_count":len(row.get("findings") or []),
                "topic_count":len(row.get("topics") or {}),
                "last_learned_at":row.get("last_learned_at"),
                "ready":len(row.get("findings") or [])>0,
            })
        return {
            "complete":all(x["ready"] for x in rows),
            "ready_count":len([x for x in rows if x["ready"]]),
            "total_rishis":len(rows),
            "rishis":rows,
            "next_assignment":self.next_learning_assignment(),
        }

    def dashboard(self,limit_findings=8):
        rows=[]
        with self.lock:
            snapshot=json.loads(json.dumps(self.state["rishis"]))
        for profile in self.council.list():
            row=snapshot[profile["id"]]
            rows.append({
                "rishi_id":profile["id"],"display_name":profile["display_name"],"role":profile["role"],
                "primary_subjects":row["charter"].get("primary_subjects") or [],
                "topic_count":len(row.get("topics") or {}),
                "finding_count":len(row.get("findings") or []),
                "open_question_count":len([x for x in row.get("open_questions") or [] if x.get("status")=="open"]),
                "mission_count":len(row.get("missions") or []),
                "last_learned_at":row.get("last_learned_at"),
                "recent_findings":(row.get("findings") or [])[-max(1,min(int(limit_findings),20)):],
            })
        return {
            "version":self.VERSION,
            "rishis":rows,
            "bootstrap":self.bootstrap_status(),
            "classical_source_registry":dict(CLASSICAL_SOURCE_REGISTRY),
            "policy":"show learned findings with evidence state and maturity; unresolved or low-maturity material remains visibly provisional",
        }

    def record_collaboration(self,mission_id,lead_rishi,topic,packets,active_rishis,classical_plan=None):
        cid=str(uuid.uuid4())
        row={
            "collaboration_id":cid,"mission_id":str(mission_id),"lead_rishi":str(lead_rishi),
            "topic":str(topic),"all_rishis":[x["rishi_id"] for x in packets],
            "active_rishis":list(active_rishis or []),
            "knowledge_packets":packets,
            "classical_plan":classical_plan or {},
            "created_at":time.time(),
        }
        with self.lock:
            self.state["collaborations"][cid]=row
            for packet in packets:
                rid=packet["rishi_id"]
                self.state["rishis"][rid]["collaborations"].append(cid)
                self.state["rishis"][rid]["collaborations"]=self.state["rishis"][rid]["collaborations"][-500:]
            self._save()
        return json.loads(json.dumps(row))

    def collaboration(self,collaboration_id):
        with self.lock:
            row=self.state["collaborations"].get(str(collaboration_id))
            if not row:raise KeyError(collaboration_id)
            return json.loads(json.dumps(row))


class CouncilCollaborationEngine:
    VERSION="council-collaboration-v1"

    def __init__(self,ledger,council,model_call=None,memory=None):
        self.ledger=ledger
        self.council=council
        self.model_call=model_call
        self.memory=memory

    def classical_plan(self,topic):
        rows=[]
        for profile in self.council.list():
            charter=self.ledger.charter(profile["id"])
            rows.append({
                "rishi_id":profile["id"],
                "lens":charter.get("classical_lens") or [],
                "instruction":(
                    "Search relevant Vedic/Upanishadic/classical material for textual, historical or philosophical context. "
                    "Preserve exact source provenance and never use resemblance as scientific validation."
                ),
            })
        return {
            "topic":str(topic),
            "source_registry":dict(CLASSICAL_SOURCE_REGISTRY),
            "rishi_lenses":rows,
            "dual_track_rule":"classical and modern scientific claims remain separate until compared at synthesis",
        }

    def prepare(self,mission,active_rishis=None,packet_limit=10):
        active=[]
        for rid in active_rishis or []:
            rid=str(rid or "").strip().lower()
            if rid and rid not in active:
                self.council.get(rid);active.append(rid)
        if mission["lead_rishi"] not in active:active.insert(0,mission["lead_rishi"])
        for rid in ("gautama","veda-vyasa"):
            if rid not in active:active.append(rid)
        packets=[]
        for profile in self.council.list():
            packet=self.ledger.knowledge_packet(profile["id"],mission["topic"],packet_limit)
            packet["contribution_mode"]="active_live_support" if profile["id"] in active else "stored_knowledge_support"
            packet["mission_question"]=mission["question"]
            packets.append(packet)
        classical=self.classical_plan(mission["topic"])
        row=self.ledger.record_collaboration(
            mission["mission_id"],mission["lead_rishi"],mission["topic"],packets,active,classical,
        )
        if self.memory:
            self.memory.audit(
                "rishi_council_collaboration","prepared",
                f"{mission['mission_id']}:lead={mission['lead_rishi']}:all={len(packets)}:active={len(active)}",
            )
        return row

    def synthesis_context(self,collaboration,per_rishi_findings=5):
        parts=[]
        for packet in collaboration.get("knowledge_packets") or []:
            findings=(packet.get("matching_findings") or [])[:max(1,min(int(per_rishi_findings),10))]
            if not findings and packet.get("contribution_mode")!="active_live_support":
                continue
            lines=[
                f"RISHI: {packet.get('display_name')} ({packet.get('rishi_id')})",
                f"MODE: {packet.get('contribution_mode')}",
                f"ROLE: {packet.get('role')}",
                "CLASSICAL LENS: "+("; ".join(packet.get("classical_lens") or []) or "none"),
            ]
            for finding in findings:
                lines.append(
                    f"- STORED FINDING [{finding.get('maturity')}/{finding.get('evidence_status')} "
                    f"conf={finding.get('confidence')}]: {finding.get('claim')}"
                )
            parts.append("\n".join(lines))
        return "\n\n".join(parts)

    def status(self):
        return {
            "name":"BRAHMAGYAN Council Collaboration",
            "version":self.VERSION,
            "members":len(self.council.list()),
            "policy":"all Rishis contribute stored knowledge; relevant Rishis perform fresh live work; Gautama audits and Veda Vyasa synthesizes",
        }
