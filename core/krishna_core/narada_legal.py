from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import json
import re


@dataclass(frozen=True)
class LegalShishya:
    id: str
    display_name: str
    role: str
    mission: str
    must_do: tuple[str, ...]
    must_not_do: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["must_do"] = list(self.must_do)
        row["must_not_do"] = list(self.must_not_do)
        return row


SHISHYA = (
    LegalShishya(
        "constitution", "Constitution", "Indian constitutional, legislation and regulatory corpus keeper",
        "Maintain a versioned source-faithful Indian legal corpus and detect new, amended, commenced, repealed or superseded law.",
        (
            "prefer official Government of India and State sources",
            "record jurisdiction, issuing authority, publication date, effective date and source URL",
            "track amendments, commencement, repeal and supersession",
            "preserve old versions and hash every stored document",
            "flag material legal changes for Narada review",
        ),
        ("never treat an unofficial summary as authoritative law", "never silently overwrite prior legal versions"),
    ),
    LegalShishya(
        "legal", "Legal", "Lawful-path and compliance analyst",
        "Research what can lawfully be done, which permissions or registrations are needed, and the lowest-risk compliant path.",
        (
            "identify governing law and jurisdiction",
            "separate mandatory legal duties from optional best practice",
            "identify licenses, consent, notice, filing and recordkeeping requirements",
            "state uncertainty and escalate consequential unresolved issues to a qualified Indian advocate",
        ),
        ("never invent a permission, exemption or legal conclusion",),
    ),
    LegalShishya(
        "illegal", "Illegal", "Prohibition and legal-risk analyst",
        "Identify conduct that is prohibited, restricted, criminal, fraudulent, deceptive, privacy-invasive or contrary to binding obligations.",
        (
            "name the suspected prohibition and official source supporting it",
            "distinguish illegal conduct from civil risk, contractual restriction or platform-policy violation",
            "identify a safer lawful alternative",
            "surface uncertainty instead of accusing a person of wrongdoing",
        ),
        ("never teach evasion, concealment, bribery, obstruction, witness tampering or evidence destruction",),
    ),
    LegalShishya(
        "vakeel", "Vakeel", "Lawful advocacy, defense, remedy and structuring analyst",
        "Protect rights and pursue the objective through lawful authorization, consent, licensing, exemptions, appeals, reviews, contract design, restructuring, settlement or other compliant routes.",
        (
            "look for lawful exceptions, defenses and statutory remedies",
            "identify appeal, review, representation, mediation and dispute-resolution routes",
            "propose compliant contractual and operational structures",
            "distinguish a lawful workaround from unlawful circumvention",
        ),
        (
            "never advise how to hide an offence or avoid detection",
            "never advise false statements, fake documents, bribery, obstruction, evidence destruction or witness tampering",
            "never impersonate an advocate or claim an attorney-client relationship",
        ),
    ),
    LegalShishya(
        "judge", "Judge", "Judicial precedent and case-comparison analyst",
        "Find Indian judgments matching the facts and legal issue, then explain holdings, court hierarchy, later history and material distinctions.",
        (
            "prefer Supreme Court and official eCourts/High Court sources",
            "separate holdings from observations and party allegations",
            "record court, bench, date, case number and cited provisions",
            "check whether later authority overrules, stays, distinguishes or qualifies a case",
        ),
        ("never fabricate a citation or holding", "never present a future court outcome as certain"),
    ),
    LegalShishya(
        "police", "Police", "Law-enforcement procedure, immediate-risk and evidence-preservation analyst",
        "Assess a current situation from a lawful police/procedure perspective: safety, complaint/FIR/cybercrime channels, evidence preservation, rights and duties.",
        (
            "prioritize immediate safety and official emergency/reporting channels",
            "identify the appropriate reporting route from official sources",
            "preserve original records and relevant evidence",
            "explain rights and duties without obstructing an investigation",
        ),
        ("never impersonate police", "never coach escape, resistance, obstruction or concealment/destruction of evidence", "never determine guilt"),
    ),
)


OFFICIAL_SOURCES = {
    "constitution":{"name":"Legislative Department, Ministry of Law and Justice","url":"https://legislative.gov.in/","domains":("legislative.gov.in","www.legislative.gov.in"),"scope":("constitution","central legislation","amendments"),"priority":100},
    "india_code":{"name":"India Code","url":"https://www.indiacode.nic.in/","domains":("indiacode.nic.in","www.indiacode.nic.in","upload.indiacode.nic.in"),"scope":("acts","sections","rules","regulations","notifications","orders","ordinances","statutes","circulars"),"priority":100},
    "egazette":{"name":"eGazette of India","url":"https://egazette.nic.in/","domains":("egazette.nic.in","www.egazette.nic.in"),"scope":("gazette","notifications","rules","commencement","appointments"),"priority":100},
    "supreme_court":{"name":"Supreme Court of India","url":"https://www.sci.gov.in/","domains":("sci.gov.in","www.sci.gov.in"),"scope":("supreme court judgments","orders","constitutional interpretation"),"priority":100},
    "ecourts_judgments":{"name":"eCourts Judgments and Orders","url":"https://judgments.ecourts.gov.in/","domains":("judgments.ecourts.gov.in","services.ecourts.gov.in"),"scope":("high court judgments","district court case information","orders"),"priority":95},
    "mha":{"name":"Ministry of Home Affairs","url":"https://www.mha.gov.in/","domains":("mha.gov.in","www.mha.gov.in"),"scope":("criminal law","BNS","BNSS","BSA","internal security notifications"),"priority":95},
    "bprd":{"name":"Bureau of Police Research and Development","url":"https://bprd.nic.in/","domains":("bprd.nic.in","www.bprd.nic.in"),"scope":("police manuals","police procedure research"),"priority":90},
    "nalsa":{"name":"National Legal Services Authority","url":"https://nalsa.gov.in/","domains":("nalsa.gov.in","www.nalsa.gov.in"),"scope":("legal aid","access to justice","lok adalat","legal services"),"priority":90},
    "rbi":{"name":"Reserve Bank of India","url":"https://www.rbi.org.in/","domains":("rbi.org.in","www.rbi.org.in"),"scope":("payments","banking","financial regulation","payment aggregators"),"priority":95},
    "meity":{"name":"Ministry of Electronics and Information Technology","url":"https://www.meity.gov.in/","domains":("meity.gov.in","www.meity.gov.in"),"scope":("data protection","information technology","digital rules"),"priority":95},
    "trai":{"name":"Telecom Regulatory Authority of India","url":"https://www.trai.gov.in/","domains":("trai.gov.in","www.trai.gov.in"),"scope":("telecom","commercial communications","consent","messaging regulation"),"priority":95},
    "consumer_affairs":{"name":"Department of Consumer Affairs","url":"https://consumeraffairs.nic.in/","domains":("consumeraffairs.nic.in","www.consumeraffairs.nic.in"),"scope":("consumer protection","e-commerce","dark patterns","direct selling"),"priority":95},
}


SENSITIVE_EVASION = re.compile(
    r"\b(evade|escape police|avoid detection|hide evidence|destroy evidence|bribe|fake document|bypass law|bypass police|tamper witness|launder|conceal offence|conceal offense)\b",
    re.I,
)


class NaradaLegalCouncil:
    """Permanent six-shishya legal advisory layer under Rishi Narada."""

    SCHEMA="krishna.narada-legal.v1"

    def __init__(self,root:str|Path):
        self.root=Path(root).resolve()
        self.corpus=self.root/"corpus"
        self.root.mkdir(parents=True,exist_ok=True)
        self.corpus.mkdir(parents=True,exist_ok=True)
        self.index_path=self.root/"index.json"
        if not self.index_path.exists():
            self._write_index({"schema":self.SCHEMA,"documents":{},"updates":[],"last_sync":None})

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _read_index(self):
        try:raw=json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception as exc:raise RuntimeError(f"Narada legal index unreadable: {type(exc).__name__}: {exc}") from exc
        if not isinstance(raw,dict) or raw.get("schema")!=self.SCHEMA:raise RuntimeError("Narada legal index schema mismatch")
        raw.setdefault("documents",{});raw.setdefault("updates",[])
        return raw

    def _write_index(self,data):
        tmp=self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
        tmp.replace(self.index_path)

    @staticmethod
    def shishya():
        return [x.as_dict() for x in SHISHYA]

    @staticmethod
    def sources():
        return {k:{**v,"domains":list(v["domains"]),"scope":list(v["scope"])} for k,v in OFFICIAL_SOURCES.items()}

    @staticmethod
    def _source_for_url(url):
        host=(urlparse(str(url or "")).hostname or "").lower()
        for sid,row in OFFICIAL_SOURCES.items():
            if host in row["domains"]:return sid
        return None

    def status(self):
        idx=self._read_index()
        return {
            "name":"Rishi Narada Legal Council","advisor":"narada","permanent":True,
            "shishya":self.shishya(),"official_sources":self.sources(),
            "corpus_documents":len(idx.get("documents") or {}),"recorded_updates":len(idx.get("updates") or []),
            "last_sync":idx.get("last_sync"),
            "policy":{
                "modern_law_authority":"current official Indian law and authentic judgments",
                "classical_texts":"historical jurisprudence only; never current law",
                "unofficial_sources":"discovery/context only until verified against authoritative material",
                "high_consequence":"qualified Indian advocate review required when unresolved or consequential",
                "evasion":"prohibited; only lawful alternatives, defenses, remedies and compliant structuring",
            },
        }

    def route(self,question):
        text=str(question or "").strip()
        if not text:raise ValueError("legal question is required")
        lower=text.lower();ids=[]
        if any(x in lower for x in ("constitution","article ","fundamental right","amendment","rule","regulation","notification","circular","act ")):ids.append("constitution")
        if any(x in lower for x in ("case","judgment","judgement","precedent","court","judge","supreme court","high court")):ids.append("judge")
        if any(x in lower for x in ("police","fir","complaint","arrest","cybercrime","investigation","evidence")):ids.append("police")
        if any(x in lower for x in ("illegal","crime","offence","offense","prohibited","fraud","penalty")):ids.append("illegal")
        if any(x in lower for x in ("appeal","defense","defence","exemption","license","licence","permission","contract","settlement","review","remedy","workaround")):ids.append("vakeel")
        for required in ("legal","illegal","vakeel"):
            if required not in ids:ids.append(required)
        ordered=[x.id for x in SHISHYA if x.id in ids]
        return {
            "question":text,"lead_rishi":"narada","shishya":ordered,
            "requires_current_source_check":True,"requires_jurisdiction":True,
            "evasion_language_detected":bool(SENSITIVE_EVASION.search(text)),
            "instruction":"Find the lawful path and legal risk using current official sources. If the objective requires concealment, obstruction or evasion, reject that route and propose lawful alternatives.",
        }

    def research_plan(self,question,*,state="",domain=""):
        routing=self.route(question);profiles={x.id:x for x in SHISHYA};tasks=[]
        outputs={
            "constitution":["governing_sources","current_status","changes","effective_dates","superseded_material"],
            "judge":["matching_cases","court_hierarchy","holding","fact_match","later_history","distinctions"],
            "vakeel":["lawful_options","permissions","defenses","remedies","risk_reduction"],
            "illegal":["prohibitions","risk_level","official_basis","lawful_alternative"],
            "police":["immediate_risk","reporting_route","evidence_preservation","rights_and_duties"],
            "legal":["governing_law","compliance_steps","permissions","uncertainties"],
        }
        for sid in routing["shishya"]:
            p=profiles[sid]
            tasks.append({"shishya":sid,"role":p.role,"task":p.mission,"required_output":outputs[sid]})
        return {
            "lead_rishi":"narada","question":str(question).strip(),
            "jurisdiction":{"country":"India","state":str(state or "").strip() or None},
            "domain":str(domain or "").strip() or None,"routing":routing,"tasks":tasks,
            "source_order":[
                "Legislative Department / India Code / eGazette",
                "Supreme Court / official eCourts",
                "issuing regulator or ministry",
                "State government / State regulator official source",
                "secondary commentary only for discovery and cross-checking",
            ],
            "github_policy":"Open-source legal/RAG repositories may inspire retrieval architecture but are never legal authority.",
            "final_review":["gautama:evidence","narada:legal synthesis"],
        }

    def ingest_official_document(self,*,title,url,text,document_type,jurisdiction="India",published_at="",effective_at="",authority="",metadata=None):
        title=str(title or "").strip();url=str(url or "").strip();body=str(text or "")
        if not title or not url or not body.strip():raise ValueError("title, url and document text are required")
        source_id=self._source_for_url(url)
        if not source_id:raise PermissionError("only allowlisted official legal sources may enter the authoritative Narada corpus")
        digest=sha256(body.encode("utf-8")).hexdigest();canonical=sha256(url.encode("utf-8")).hexdigest()
        doc_id=f"{source_id}-{digest[:20]}";idx=self._read_index();old=idx["documents"].get(canonical)
        row={
            "document_id":doc_id,"canonical_id":canonical,"title":title,"url":url,"source_id":source_id,
            "document_type":str(document_type or "unknown").strip().lower(),"jurisdiction":str(jurisdiction or "India").strip(),
            "authority":str(authority or OFFICIAL_SOURCES[source_id]["name"]).strip(),
            "published_at":str(published_at or "").strip() or None,"effective_at":str(effective_at or "").strip() or None,
            "sha256":digest,"ingested_at":self._now(),"metadata":dict(metadata or {}),
            "supersedes":old.get("document_id") if old and old.get("sha256")!=digest else None,
        }
        (self.corpus/f"{doc_id}.json").write_text(json.dumps({**row,"text":body},ensure_ascii=False,indent=2),encoding="utf-8")
        changed=old is None or old.get("sha256")!=digest
        idx["documents"][canonical]=row
        if changed:
            idx["updates"].append({"at":self._now(),"url":url,"old_document_id":old.get("document_id") if old else None,"new_document_id":doc_id,"kind":"new" if old is None else "changed"})
            idx["updates"]=idx["updates"][-5000:]
        idx["last_sync"]=self._now();self._write_index(idx)
        return {"stored":True,"changed":changed,**row}

    def search_corpus(self,query,limit=20):
        terms=[x for x in re.findall(r"[a-zA-Z0-9]+",str(query or "").lower()) if len(x)>2]
        if not terms:raise ValueError("search query is required")
        idx=self._read_index();scored=[]
        for row in idx.get("documents",{}).values():
            path=self.corpus/f"{row['document_id']}.json"
            if not path.exists():continue
            try:doc=json.loads(path.read_text(encoding="utf-8"))
            except Exception:continue
            hay=(str(doc.get("title") or "")+"\n"+str(doc.get("text") or "")).lower()
            score=sum(hay.count(t) for t in terms)
            if score:scored.append((score,{k:v for k,v in doc.items() if k!="text"}))
        scored.sort(key=lambda x:(-x[0],str(x[1].get("title") or "")))
        rows=[{**row,"score":score} for score,row in scored[:max(1,min(int(limit),100))]]
        return {"query":str(query),"results":rows,"count":len(rows)}

    def update_watch_plan(self):
        return {
            "owner":"constitution","purpose":"detect new or changed law without silently replacing prior versions",
            "recommended_cadence":{
                "eGazette / India Code / key ministries and regulators":"daily",
                "Supreme Court / eCourts relevant judgments":"daily",
                "broader State/local-law source inventory":"weekly and event-driven",
            },
            "steps":[
                "fetch official indexes/feed/pages through approved browser or provider",
                "compare canonical URL and content hash with Narada corpus",
                "save new version while preserving the prior version",
                "classify new/amended/repealed/superseded/commenced",
                "send material changes through Constitution -> relevant shishya -> Gautama -> Narada",
                "do not claim corpus completeness unless source coverage is machine-verified",
            ],
            "sources":self.sources(),
        }
