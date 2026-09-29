from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
from html.parser import HTMLParser
from urllib.parse import urlparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser


class _OfficialLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]

    def handle_starttag(self, tag, attrs):
        if str(tag).lower() not in {"a","link"}:
            return
        row=dict(attrs)
        href=str(row.get("href") or "").strip()
        if href:
            self.links.append(href)


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


DEFAULT_JURISDICTION={
    "country":"India",
    "state":"Odisha",
    "district":"Khordha",
    "city":"Bhubaneswar",
}
ODISHA_ONLY=True


OFFICIAL_SOURCES = {
    "odisha_law":{
        "name":"Law Department, Government of Odisha",
        "url":"https://law.odisha.gov.in/",
        "domains":("law.odisha.gov.in",),
        "scope":("Odisha acts","ordinances","rules","regulations","notifications","Odisha Gazette","Extraordinary Gazette"),
        "priority":100,"jurisdiction":"Odisha",
    },
    "orissa_high_court":{
        "name":"Orissa High Court, Cuttack",
        "url":"https://www.orissahighcourt.nic.in/",
        "domains":("orissahighcourt.nic.in","www.orissahighcourt.nic.in"),
        "scope":("Odisha High Court judgments","orders","notifications","court rules","PIL"),
        "priority":100,"jurisdiction":"Odisha",
    },
    "odisha_revenue":{
        "name":"Revenue and Disaster Management Department, Government of Odisha",
        "url":"https://revenue.odisha.gov.in/",
        "domains":("revenue.odisha.gov.in",),
        "scope":("land reforms","government land","registration","stamp","survey and settlement","minor minerals","land acquisition"),
        "priority":100,"jurisdiction":"Odisha",
    },
    "odisha_urban":{
        "name":"Housing & Urban Development Department, Government of Odisha",
        "url":"https://urban.odisha.gov.in/",
        "domains":("urban.odisha.gov.in",),
        "scope":("municipal law","planning","building standards","apartments","urban local bodies","development authorities"),
        "priority":100,"jurisdiction":"Odisha",
    },
    "bmc":{
        "name":"Bhubaneswar Municipal Corporation",
        "url":"https://www.bmc.gov.in/",
        "domains":("bmc.gov.in","www.bmc.gov.in"),
        "scope":("Bhubaneswar municipal law","trade regulation","solid waste bye-laws","municipal rules","local permissions"),
        "priority":100,"jurisdiction":"Bhubaneswar",
    },
    "bda":{
        "name":"Bhubaneswar Development Authority",
        "url":"https://www.bda.gov.in/",
        "domains":("bda.gov.in","www.bda.gov.in"),
        "scope":("Bhubaneswar planning","building standards","development authority rules","occupancy","land development"),
        "priority":100,"jurisdiction":"Bhubaneswar",
    },
    "orera":{
        "name":"Odisha Real Estate Regulatory Authority",
        "url":"https://rera.odisha.gov.in/",
        "domains":("rera.odisha.gov.in",),
        "scope":("real estate projects","promoters","agents","orders","RERA compliance","consumer protection in real estate"),
        "priority":100,"jurisdiction":"Odisha",
    },
    "odisha_police":{
        "name":"Odisha Police",
        "url":"https://police.odisha.gov.in/",
        "domains":("police.odisha.gov.in",),
        "scope":("police citizen services","FIR","cyber crime","complaints","public services","police notices"),
        "priority":100,"jurisdiction":"Odisha",
    },
    "commissionerate_police":{
        "name":"Bhubaneswar-Cuttack Police Commissionerate",
        "url":"https://bhubaneswarcuttackpolice.gov.in/",
        "domains":("bhubaneswarcuttackpolice.gov.in","www.bhubaneswarcuttackpolice.gov.in"),
        "scope":("Bhubaneswar police procedure","local FIR services","traffic","permissions","public safety"),
        "priority":100,"jurisdiction":"Bhubaneswar",
    },
    "odisha_labour":{
        "name":"Labour & ESI Department, Government of Odisha",
        "url":"https://labour.odisha.gov.in/",
        "domains":("labour.odisha.gov.in",),
        "scope":("labour rules","wages","industrial relations","social security","occupational safety","gazette notifications"),
        "priority":95,"jurisdiction":"Odisha",
    },
    "odisha_finance":{
        "name":"Finance Department, Government of Odisha",
        "url":"https://finance.odisha.gov.in/",
        "domains":("finance.odisha.gov.in",),
        "scope":("Odisha GST","tax notifications","financial rules","state finance circulars"),
        "priority":95,"jurisdiction":"Odisha",
    },
    "odisha_spcb":{
        "name":"State Pollution Control Board, Odisha",
        "url":"https://ospcboard.odisha.gov.in/",
        "domains":("ospcboard.odisha.gov.in",),
        "scope":("pollution consent","environmental authorisation","waste rules","notices","industrial environmental compliance"),
        "priority":95,"jurisdiction":"Odisha",
    },
    "constitution":{
        "name":"Legislative Department, Ministry of Law and Justice",
        "url":"https://legislative.gov.in/",
        "domains":("legislative.gov.in","www.legislative.gov.in"),
        "scope":("Constitution of India","central legislation applicable in Odisha","constitutional amendments"),
        "priority":90,"jurisdiction":"India",
    },
    "india_code":{
        "name":"India Code",
        "url":"https://www.indiacode.nic.in/",
        "domains":("indiacode.nic.in","www.indiacode.nic.in","upload.indiacode.nic.in"),
        "scope":("central acts and subordinate law applicable in Odisha"),
        "priority":90,"jurisdiction":"India",
    },
    "egazette":{
        "name":"eGazette of India",
        "url":"https://egazette.nic.in/",
        "domains":("egazette.nic.in","www.egazette.nic.in"),
        "scope":("central gazette material applicable in Odisha"),
        "priority":90,"jurisdiction":"India",
    },
    "supreme_court":{
        "name":"Supreme Court of India",
        "url":"https://www.sci.gov.in/",
        "domains":("sci.gov.in","www.sci.gov.in"),
        "scope":("binding Supreme Court judgments and orders applicable in Odisha"),
        "priority":95,"jurisdiction":"India",
    },
    "ecourts_judgments":{
        "name":"eCourts Judgments and Orders",
        "url":"https://judgments.ecourts.gov.in/",
        "domains":("judgments.ecourts.gov.in","services.ecourts.gov.in"),
        "scope":("Odisha court judgments/orders and case information"),
        "priority":95,"jurisdiction":"India/Odisha",
    },
    "mha":{
        "name":"Ministry of Home Affairs",
        "url":"https://www.mha.gov.in/",
        "domains":("mha.gov.in","www.mha.gov.in"),
        "scope":("central criminal law applicable in Odisha","BNS","BNSS","BSA"),
        "priority":90,"jurisdiction":"India",
    },
    "rbi":{
        "name":"Reserve Bank of India",
        "url":"https://www.rbi.org.in/",
        "domains":("rbi.org.in","www.rbi.org.in"),
        "scope":("banking","payments","financial regulation applicable in Odisha"),
        "priority":90,"jurisdiction":"India",
    },
    "meity":{
        "name":"Ministry of Electronics and Information Technology",
        "url":"https://www.meity.gov.in/",
        "domains":("meity.gov.in","www.meity.gov.in"),
        "scope":("data protection","information technology","digital rules applicable in Odisha"),
        "priority":90,"jurisdiction":"India",
    },
    "trai":{
        "name":"Telecom Regulatory Authority of India",
        "url":"https://www.trai.gov.in/",
        "domains":("trai.gov.in","www.trai.gov.in"),
        "scope":("telecom","commercial communications","consent and messaging rules applicable in Odisha"),
        "priority":90,"jurisdiction":"India",
    },
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
            "default_jurisdiction":dict(DEFAULT_JURISDICTION),"odisha_only":ODISHA_ONLY,
            "shishya":self.shishya(),"official_sources":self.sources(),
            "corpus_documents":len(idx.get("documents") or {}),"recorded_updates":len(idx.get("updates") or []),
            "last_sync":idx.get("last_sync"),
            "policy":{
                "modern_law_authority":"Odisha/Bhubaneswar official law first; Central Indian law only where applicable in Odisha",
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
        for required in ("legal","illegal","judge","vakeel"):
            if required not in ids:ids.append(required)
        ordered=[x.id for x in SHISHYA if x.id in ids]
        return {
            "question":text,"lead_rishi":"narada","shishya":ordered,
            "requires_current_source_check":True,"requires_jurisdiction":True,
            "evasion_language_detected":bool(SENSITIVE_EVASION.search(text)),
            "instruction":"Find the lawful path and legal risk using current official sources. If the objective requires concealment, obstruction or evasion, reject that route and propose lawful alternatives.",
        }

    def research_plan(self,question,*,state="",district="",city="",domain=""):
        requested_state=str(state or DEFAULT_JURISDICTION["state"]).strip()
        if requested_state.lower() not in {"odisha","orissa"}:
            raise PermissionError("Narada legal scope is currently restricted to Odisha; other-state law is disabled")
        requested_city=str(city or DEFAULT_JURISDICTION["city"]).strip()
        requested_district=str(district or DEFAULT_JURISDICTION["district"]).strip()
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
            "jurisdiction":{"country":"India","state":"Odisha","district":requested_district or None,"city":requested_city or None},
            "scope_policy":"Odisha law only for now; Bhubaneswar is the default local context. Central law is consulted only where it applies in Odisha.",
            "domain":str(domain or "").strip() or None,"routing":routing,"tasks":tasks,
            "source_order":[
                "Odisha Law Department / Odisha Gazette",
                "Orissa High Court / Odisha eCourts",
                "relevant Odisha department or regulator",
                "BMC / BDA / Bhubaneswar-Cuttack Commissionerate when local Bhubaneswar law or procedure applies",
                "India Code / Central eGazette / Supreme Court only for Central law binding or applicable in Odisha",
                "secondary commentary only for discovery and cross-checking",
            ],
            "github_policy":"Open-source legal/RAG repositories may inspire retrieval architecture but are never legal authority.",
            "case_research_policy":{"judge_and_vakeel_mandatory":True,"two_sided_arguments":True,"adverse_authority_required_when_available":True,"result_rule":"compare actual precedent outcomes; never guarantee the current result"},
            "final_review":["judge:precedent packet","vakeel:argument packet","gautama:evidence","narada:legal synthesis"],
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
            "jurisdiction":dict(DEFAULT_JURISDICTION),
            "odisha_only":True,
            "recommended_cadence":{
                "Odisha Law Department / Odisha Gazette":"daily",
                "Orissa High Court and Odisha-relevant eCourts judgments":"daily",
                "Revenue / Urban / BMC / BDA / ORERA / Odisha Police / Labour / Finance / SPCB":"daily",
                "Central sources":"daily only for changes applicable in Odisha",
                "source coverage audit":"weekly",
            },
            "steps":[
                "fetch Odisha/Bhubaneswar official indexes/feed/pages through approved browser or provider",
                "compare canonical URL and content hash with Narada corpus",
                "save new version while preserving the prior version",
                "classify new/amended/repealed/superseded/commenced",
                "send material changes through Constitution -> relevant shishya -> Judge/Vakeel where needed -> Gautama -> Narada",
                "do not claim corpus completeness unless source coverage is machine-verified",
            ],
            "sources":self.sources(),
        }


# Compatibility/active runtime retained from the verified Narada advisor implementation.
@dataclass(frozen=True)
class LegalShishyaProfile:
    id: str
    display_name: str
    role: str
    question: str
    duties: tuple[str, ...]
    safety_rules: tuple[str, ...] = ()
    permanent: bool = True

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["duties"] = list(self.duties)
        row["safety_rules"] = list(self.safety_rules)
        return row


@dataclass(frozen=True)
class LegalSourceProfile:
    id: str
    title: str
    url: str
    authority: str
    jurisdiction: str
    kinds: tuple[str, ...]
    priority: str = "primary"
    monitor: bool = True
    max_bytes: int = 25 * 1024 * 1024

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["kinds"] = list(self.kinds)
        return row


LEGAL_SHISHYAS = (
    LegalShishyaProfile(
        "constitution", "Constitution", "Constitution, statutes and delegated-legislation custodian",
        "What current constitutional, statutory, rule, regulation, notification, order or circular governs this issue?",
        (
            "maintain source-indexed Indian constitutional and statutory knowledge",
            "track official amendments, commencement/effective dates and subordinate legislation",
            "distinguish current text from repealed, superseded, draft or historical material",
            "preserve official-source URL, retrieval time, fingerprint and jurisdiction",
            "flag new or changed official legal material for Narada review",
        ),
        (
            "official sources outrank summaries and repositories",
            "never claim the entire Indian legal corpus is complete unless measured coverage proves it",
            "historical Dharmashastra is comparative history, not current Indian law",
        ),
    ),
    LegalShishyaProfile(
        "legal", "Legal", "Lawful-path and compliance research specialist",
        "What is the most defensible lawful way to accomplish the objective?",
        (
            "identify applicable law and regulator",
            "map permissions, licences, consent, contracts, notices, disclosures and compliance duties",
            "separate mandatory law from guidance, policy, contract terms and best practice",
            "surface uncertainty, jurisdiction and effective-date dependencies",
            "propose compliance-by-design implementation options",
        ),
        (
            "do not label conduct legal without current source support",
            "high-stakes or materially uncertain conclusions require qualified-lawyer review",
        ),
    ),
    LegalShishyaProfile(
        "illegal", "Illegal", "Prohibited-conduct and legal-risk specialist",
        "What conduct is prohibited, restricted or legally risky, and what must KRISHNA not do?",
        (
            "identify prohibited acts, restrictions, penalties and enforcement exposure",
            "check privacy, consumer, communications, cyber, financial and sector-specific restrictions",
            "detect circumvention, deception, fraud, concealment and unauthorized-access risks",
            "produce a do-not-do boundary with cited governing authority",
        ),
        (
            "never convert prohibited conduct into evasion instructions",
            "when legality is unclear, block autonomous execution until current-law research resolves it",
        ),
    ),
    LegalShishyaProfile(
        "vakeel", "Vakeel", "Lawful alternatives, remedies and defence-path specialist",
        "If the direct path is prohibited or risky, what lawful alternative, permission, remedy or defence exists?",
        (
            "find lawful exemptions, licences, permissions, consent models and compliant restructuring",
            "identify appeal, review, representation, settlement and dispute-resolution routes",
            "identify available procedural rights and legitimate defences",
            "recommend remediation and voluntary compliance where a defect is found",
            "translate legal constraints into a compliant operational path",
        ),
        (
            "never help evade police, courts, regulators, KYC, tax, sanctions or legal obligations",
            "never advise evidence destruction, concealment, bribery, witness tampering or obstruction",
            "never disguise illegal conduct as a loophole; use only genuine lawful alternatives",
        ),
    ),
    LegalShishyaProfile(
        "judge", "Judge", "Indian precedent and judicial-reasoning specialist",
        "Which Indian judgments materially match the facts and issues, and what did the court actually hold?",
        (
            "find factually and legally relevant Supreme Court and High Court decisions",
            "extract facts, issues, statutes/provisions, arguments, ratio, holding and result",
            "distinguish binding from persuasive authority and note court hierarchy",
            "check later history, overruling, distinguishing facts and statutory amendments",
            "compare both favourable and adverse precedent",
        ),
        (
            "do not infer a guaranteed court outcome from a similar case",
            "verify quotations and holdings against the judgment text",
        ),
    ),
    LegalShishyaProfile(
        "police", "Police", "Lawful operational-safety and procedure specialist",
        "What is the safest lawful action in the current situation, including reporting, evidence and procedure?",
        (
            "identify immediate lawful safety and de-escalation steps",
            "preserve evidence and chain-of-custody considerations",
            "identify appropriate reporting or complaint channels",
            "map relevant criminal-law and police-procedure sources",
            "separate urgent safety action from legal conclusions that need counsel",
        ),
        (
            "never advise evading arrest, destroying evidence or obstructing an investigation",
            "do not impersonate police or claim police powers",
            "emergency guidance prioritizes personal safety and lawful authorities",
        ),
    ),
)


ADVISOR_OFFICIAL_SOURCES = (
    LegalSourceProfile(
        "constitution_2026",
        "Constitution of India — official Legislative Department edition",
        "https://www.legislative.gov.in/static/uploads/2025/07/88cca69e868e50b217f855be2fb8bdba.pdf",
        "Legislative Department, Ministry of Law and Justice, Government of India",
        "India",
        ("constitution", "amendments"),
        max_bytes=40 * 1024 * 1024,
    ),
    LegalSourceProfile(
        "india_code",
        "India Code",
        "https://www.indiacode.nic.in/indiacode/home.jsp",
        "Legislative Department / Government of India",
        "India",
        ("acts", "rules", "regulations", "notifications", "orders", "ordinances", "statutes", "circulars"),
    ),
    LegalSourceProfile(
        "india_code_data_report",
        "India Code — official upload/notification coverage report",
        "https://upload.indiacode.nic.in/showdatareport",
        "India Code / Legislative Department, Government of India",
        "India",
        ("coverage", "acts", "rules", "regulations", "notifications", "orders", "ordinances", "statutes", "circulars"),
    ),
    LegalSourceProfile(
        "egazette",
        "eGazette of India",
        "https://egazette.gov.in/?acceptscookies=yes",
        "Department of Publication, Government of India",
        "India",
        ("gazette", "acts", "rules", "notifications", "orders", "regulations"),
    ),
    LegalSourceProfile(
        "supreme_court_constitution",
        "Supreme Court of India — Constitution",
        "https://www.sci.gov.in/constitution/",
        "Supreme Court of India",
        "India",
        ("constitution", "judicial_authority"),
    ),
    LegalSourceProfile(
        "supreme_court_verdict_finder",
        "Supreme Court of India — Verdict Finder",
        "https://verdictfinder.sci.gov.in/elk_frontend/index.php",
        "Supreme Court of India",
        "India",
        ("judgments", "precedent"),
    ),
    LegalSourceProfile(
        "ecourts_judgments",
        "eCourts Judgment Search",
        "https://judgments.ecourts.gov.in/pdfsearch/",
        "eCommittee, Supreme Court of India",
        "India",
        ("judgments", "high_courts", "precedent"),
    ),
    LegalSourceProfile(
        "mha_new_criminal_laws",
        "Ministry of Home Affairs — New Criminal Laws",
        "https://www.mha.gov.in/en/commoncontent/new-criminal-laws",
        "Ministry of Home Affairs, Government of India",
        "India",
        ("criminal_law", "BNS", "BNSS", "BSA"),
    ),
    LegalSourceProfile(
        "bprd_model_police_manual",
        "Bureau of Police Research & Development — Model Police Manual",
        "https://bprd.nic.in/page/model_police_manual",
        "Bureau of Police Research & Development, Ministry of Home Affairs",
        "India",
        ("police_procedure", "police_practice", "manuals"),
    ),
    LegalSourceProfile(
        "odisha_acts",
        "Odisha Law Department — Acts and Ordinances",
        "https://law.odisha.gov.in/en/publication/acts-and-ordinances/acts",
        "Law Department, Government of Odisha",
        "Odisha",
        ("state_acts", "ordinances"),
    ),
    LegalSourceProfile(
        "odisha_rules",
        "Odisha Law Department — Rules and Regulations",
        "https://law.odisha.gov.in/en/publication/rules-and-regulations?page=0",
        "Law Department, Government of Odisha",
        "Odisha",
        ("state_rules", "state_regulations"),
    ),
    LegalSourceProfile(
        "odisha_notifications",
        "Odisha Law Department — Notifications",
        "https://law.odisha.gov.in/en/notification/law-notification",
        "Law Department, Government of Odisha",
        "Odisha",
        ("state_notifications",),
    ),
    LegalSourceProfile(
        "orissa_high_court",
        "Orissa High Court, Cuttack",
        "https://www.orissahighcourt.nic.in/",
        "High Court of Orissa",
        "Odisha",
        ("judgments","orders","court_rules","precedent"),
    ),
    LegalSourceProfile(
        "odisha_revenue",
        "Revenue and Disaster Management Department, Odisha",
        "https://revenue.odisha.gov.in/",
        "Government of Odisha",
        "Odisha",
        ("land","registration","stamp","land_reform","settlement","acquisition"),
    ),
    LegalSourceProfile(
        "odisha_urban",
        "Housing & Urban Development Department, Odisha",
        "https://urban.odisha.gov.in/",
        "Government of Odisha",
        "Odisha",
        ("municipal","planning","building","development_authority","apartments"),
    ),
    LegalSourceProfile(
        "bmc",
        "Bhubaneswar Municipal Corporation",
        "https://www.bmc.gov.in/",
        "Bhubaneswar Municipal Corporation",
        "Bhubaneswar, Odisha",
        ("municipal","trade","local_permissions","bye_laws"),
    ),
    LegalSourceProfile(
        "bda",
        "Bhubaneswar Development Authority",
        "https://www.bda.gov.in/",
        "Bhubaneswar Development Authority",
        "Bhubaneswar, Odisha",
        ("planning","building","development","occupancy"),
    ),
    LegalSourceProfile(
        "orera",
        "Odisha Real Estate Regulatory Authority",
        "https://rera.odisha.gov.in/",
        "Odisha RERA",
        "Odisha",
        ("real_estate","projects","promoters","agents","orders"),
    ),
    LegalSourceProfile(
        "odisha_police",
        "Odisha Police",
        "https://police.odisha.gov.in/",
        "Odisha Police",
        "Odisha",
        ("police","fir","complaints","cybercrime","citizen_services"),
    ),
    LegalSourceProfile(
        "commissionerate_police",
        "Bhubaneswar-Cuttack Police Commissionerate",
        "https://bhubaneswarcuttackpolice.gov.in/",
        "Bhubaneswar-Cuttack Police Commissionerate",
        "Bhubaneswar/Cuttack, Odisha",
        ("police","permissions","traffic","public_safety"),
    ),
    LegalSourceProfile(
        "sebi_legal",
        "SEBI — Legal Framework",
        "https://www.sebi.gov.in/legal.html",
        "Securities and Exchange Board of India",
        "India",
        ("securities", "regulations", "circulars", "master_circulars", "orders"),
    ),
    LegalSourceProfile(
        "rbi_master_directions",
        "Reserve Bank of India — Master Directions",
        "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx?did=338",
        "Reserve Bank of India",
        "India",
        ("banking", "payments", "foreign_exchange", "master_directions"),
    ),
    LegalSourceProfile(
        "trai_directions",
        "TRAI — Directions",
        "https://trai.gov.in/release-publication/directions",
        "Telecom Regulatory Authority of India",
        "India",
        ("telecom", "commercial_communications", "directions"),
    ),
)


REFERENCE_REPOS = (
    {
        "name": "OpenNyAI/Opennyai",
        "url": "https://github.com/OpenNyAI/Opennyai",
        "use": "Indian judgment NLP pipeline: legal NER, rhetorical roles and extractive summarization",
        "authoritative": False,
    },
    {
        "name": "Legal-NLP-EkStep/legal_NER",
        "url": "https://github.com/Legal-NLP-EkStep/legal_NER",
        "use": "Extract courts, parties, judges, statutes, provisions, precedents and case numbers from Indian judgments",
        "authoritative": False,
    },
    {
        "name": "Legal-NLP-EkStep/judgment_extractive_summarizer",
        "url": "https://github.com/Legal-NLP-EkStep/judgment_extractive_summarizer",
        "use": "Facts/issues/arguments/analysis/decision-oriented judgment structuring",
        "authoritative": False,
    },
    {
        "name": "vanga/indian-supreme-court-judgments",
        "url": "https://github.com/vanga/indian-supreme-court-judgments",
        "use": "Bulk Supreme Court judgment corpus and metadata for retrieval/indexing experiments",
        "authoritative": False,
    },
)


_BLOCK_PATTERNS = (
    (r"\b(?:hide|destroy|delete|erase|tamper(?:\s+with)?)\b.{0,40}\bevidence\b", "evidence concealment or destruction"),
    (r"\bbrib(?:e|ery|ing)\b", "bribery"),
    (r"\b(?:evade|escape|avoid)\b.{0,25}\b(?:police|arrest|law enforcement)\b", "law-enforcement evasion"),
    (r"\bbypass\b.{0,35}\b(?:kyc|compliance|law|regulation|court order|sanction)\b", "legal or compliance bypass"),
    (r"\b(?:launder(?:ing)? money|money laundering|conceal(?:ing)? proceeds)\b", "money laundering or proceeds concealment"),
    (r"\b(?:fake|forge|forged|fabricate)\b.{0,30}\b(?:document|record|evidence|certificate|invoice|identity|id)\b", "document or evidence falsification"),
    (r"\b(?:tamper|intimidate|threaten)\b.{0,30}\b(?:witness|complainant|informant)\b", "witness interference"),
    (r"\bavoid detection\b", "detection evasion"),
    (r"\b(?:obstruct|interfere with)\b.{0,30}\b(?:investigation|police|court|regulator)\b", "investigation or authority obstruction"),
)


LEGAL_SIGNAL_TERMS = (
    "law","legal","illegal","constitution","act","section","rule","regulation","notification",
    "circular","order","ordinance","statute","court","judge","judgment","judgement","precedent",
    "police","fir","arrest","bail","criminal","civil","lawyer","advocate","vakeel","compliance",
    "licence","license","permit","permission","contract","agreement","consumer","privacy","dpdp",
    "cyber law","rera","orera","sebi","rbi","trai","gst","tax","litigation","appeal","petition",
    "writ","evidence","penalty","fine","offence","offense","rights","liability","jurisdiction",
)


class NaradaLegalAdvisor:
    """Current-law research and compliance advisor under permanent Rishi Narada.

    The six named legal Shishyas are durable *roles*, not autonomous identities.
    Ordinary research workers remain governed by KRISHNA's existing ephemeral
    Shishya lifecycle. This module never treats a GitHub repo, model response or
    historical Dharmashastra text as current Indian legal authority.
    """

    SCHEMA = "krishna.narada-legal.v1"
    PARENT_RISHI = "narada"
    AUTHORITY_POLICY = (
        "Prefer the Constitution, official statutes/amendments, official subordinate legislation, "
        "official gazettes/regulator material and authentic court judgments. Track jurisdiction, "
        "effective date and later amendments. Secondary sources and GitHub projects may aid retrieval "
        "or NLP but cannot establish what the law is."
    )
    COVERAGE_TRUTH = (
        "The local corpus is a versioned cache/index of official material actually fetched. "
        "It must never be described as a complete copy of every Indian law unless measured "
        "source/category coverage proves that claim."
    )
    ALLOWED_OFFICIAL_HOSTS = {
        "legislative.gov.in", "www.legislative.gov.in",
        "indiacode.nic.in", "www.indiacode.nic.in", "upload.indiacode.nic.in",
        "egazette.gov.in", "www.egazette.gov.in",
        "sci.gov.in", "www.sci.gov.in", "verdictfinder.sci.gov.in",
        "judgments.ecourts.gov.in", "ecourts.gov.in", "www.ecourts.gov.in",
        "mha.gov.in", "www.mha.gov.in",
        "bprd.nic.in", "www.bprd.nic.in",
        "law.odisha.gov.in",
        "orissahighcourt.nic.in", "www.orissahighcourt.nic.in",
        "revenue.odisha.gov.in",
        "urban.odisha.gov.in",
        "bmc.gov.in", "www.bmc.gov.in",
        "bda.gov.in", "www.bda.gov.in",
        "rera.odisha.gov.in",
        "police.odisha.gov.in",
        "bhubaneswarcuttackpolice.gov.in", "www.bhubaneswarcuttackpolice.gov.in",
        "sebi.gov.in", "www.sebi.gov.in",
        "rbi.org.in", "www.rbi.org.in",
        "trai.gov.in", "www.trai.gov.in",
    }

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.corpus = self.root / "corpus"
        self.corpus.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "source_state.json"
        self.crawl_state_path = self.root / "crawl_state.json"
        self._sources = {x.id: x for x in ADVISOR_OFFICIAL_SOURCES}
        self._state = self._load_state()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _jurisdiction(value: str = "") -> str:
        raw=str(value or "").strip()
        lower=raw.lower()
        other_states=("karnataka","maharashtra","west bengal","tamil nadu","telangana","andhra pradesh","kerala","gujarat","rajasthan","punjab","haryana","assam","bihar","jharkhand","chhattisgarh","madhya pradesh","uttar pradesh","uttarakhand","goa","sikkim","tripura","manipur","mizoram","nagaland","arunachal pradesh","meghalaya")
        if any(x in lower for x in other_states):
            raise PermissionError("Narada legal scope is currently restricted to Bhubaneswar/Odisha; other-state law is disabled")
        return raw or "Bhubaneswar, Khordha, Odisha, India"

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema": self.SCHEMA, "sources": {}, "updated_at": None}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Narada legal source state is unreadable: {type(exc).__name__}") from exc
        if not isinstance(raw, dict) or raw.get("schema") != self.SCHEMA:
            raise RuntimeError("unsupported Narada legal source-state schema")
        raw.setdefault("sources", {})
        return raw

    def _save_state(self) -> None:
        self._state["updated_at"] = self._now()
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_path)

    @staticmethod
    def looks_legal(text: str) -> bool:
        value=" ".join(str(text or "").lower().split())
        if not value:
            return False
        return any(
            (term in value if " " in term else re.search(r"\b"+re.escape(term)+r"\b", value))
            for term in LEGAL_SIGNAL_TERMS
        )

    def official_research_queries(self, issue: str, jurisdiction: str = "Bhubaneswar, Khordha, Odisha, India") -> dict[str, str]:
        issue=" ".join(str(issue or "").split())
        if not issue:
            raise ValueError("legal issue is required")
        state=self._jurisdiction(jurisdiction)
        state_sites=" site:law.odisha.gov.in"
        return {
            "constitution": f"{issue} Constitution India Act Rules Regulations amendment commencement site:legislative.gov.in OR site:indiacode.nic.in{state_sites}",
            "legal": f"{issue} lawful compliance licence permission consent obligations India site:indiacode.nic.in OR site:egazette.gov.in{state_sites}",
            "illegal": f"{issue} prohibited penalty offence restriction India site:indiacode.nic.in OR site:egazette.gov.in{state_sites}",
            "vakeel": f"{issue} exemption permission appeal review remedy compliance India site:indiacode.nic.in OR site:sci.gov.in{state_sites}",
            "judge": f"{issue} judgment precedent ratio holding Orissa High Court Supreme Court India site:orissahighcourt.nic.in OR site:sci.gov.in OR site:judgments.ecourts.gov.in",
            "police": f"{issue} police criminal procedure evidence BNS BNSS BSA Odisha India site:police.odisha.gov.in OR site:mha.gov.in OR site:bprd.nic.in",
        }

    def filter_official_research(self, report: dict[str, Any]) -> dict[str, Any]:
        rows=[]
        for item in report.get("web") or []:
            url=str(item.get("url") or "")
            if self._official_host(url):
                rows.append(dict(item))
        return {
            "web": rows,
            "errors": dict(report.get("errors") or {}),
            "coverage": list(report.get("coverage") or []),
            "official_only": True,
            "authority_policy": self.AUTHORITY_POLICY,
        }

    @staticmethod
    def shishyas() -> list[dict[str, Any]]:
        return [x.as_dict() for x in LEGAL_SHISHYAS]

    def sources(self) -> dict[str, Any]:
        return {
            "official": [x.as_dict() for x in ADVISOR_OFFICIAL_SOURCES],
            "reference_repositories": [dict(x) for x in REFERENCE_REPOS],
            "authority_policy": self.AUTHORITY_POLICY,
            "coverage_truth": self.COVERAGE_TRUTH,
        }

    def status(self) -> dict[str, Any]:
        cached = list(self.corpus.glob("*/*")) if self.corpus.exists() else []
        return {
            "name": "RISHI NARADA LEGAL ADVISOR",
            "parent_rishi": self.PARENT_RISHI,
            "role": "KRISHNA legal, judicial and compliance advisor",
            "permanent_shishyas": self.shishyas(),
            "permanent_shishya_count": len(LEGAL_SHISHYAS),
            "official_source_count": len(ADVISOR_OFFICIAL_SOURCES),
            "cached_snapshot_count": len([x for x in cached if x.is_file()]),
            "authority_policy": self.AUTHORITY_POLICY,
            "coverage_truth": self.COVERAGE_TRUTH,
            "evasion_policy": "prohibited; only lawful alternatives, rights, remedies and compliant restructuring are allowed",
            "state_updated_at": self._state.get("updated_at"),
        }

    @classmethod
    def _official_host(cls, url: str) -> bool:
        host = (urllib.parse.urlparse(str(url or "")).hostname or "").lower().strip(".")
        return host in cls.ALLOWED_OFFICIAL_HOSTS

    @classmethod
    def risk_gate(cls, request: str) -> dict[str, Any]:
        text = " ".join(str(request or "").lower().split())
        hits = []
        for pattern, reason in _BLOCK_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(reason)
        if hits:
            return {
                "allowed": False,
                "verdict": "blocked_illegal_evasion",
                "reasons": list(dict.fromkeys(hits)),
                "vakeel_scope": (
                    "Vakeel may identify lawful exemptions, licences, permissions, appeals, review, "
                    "settlement, legitimate defences, remediation or compliant restructuring; it may "
                    "not provide evasion, concealment, obstruction or bypass instructions."
                ),
                "lawful_alternatives": [
                    "obtain the required licence, permission or consent",
                    "change the transaction or workflow so it complies",
                    "use a statutory appeal, review, representation or dispute-resolution process",
                    "remediate the non-compliance and preserve relevant records",
                    "seek a qualified Indian lawyer where consequences are material or facts are disputed",
                ],
            }
        return {
            "allowed": True,
            "verdict": "current_law_research_required",
            "reasons": [],
            "rule": "No generic request is declared legal merely because this deterministic gate did not block it.",
        }

    def _selected_source_ids(self, topic: str, jurisdiction: str = "india") -> list[str]:
        text = f"{topic} {jurisdiction}".lower()
        ids = ["odisha_acts","odisha_rules","odisha_notifications","orissa_high_court","constitution_2026","india_code","egazette"]
        if any(x in text for x in ("case", "judgment", "judgement", "precedent", "court", "judge", "ratio")):
            ids += ["orissa_high_court","supreme_court_verdict_finder", "ecourts_judgments", "supreme_court_constitution"]
        if any(x in text for x in ("criminal", "police", "arrest", "fir", "bns", "bnss", "bsa", "evidence", "crime")):
            ids += ["mha_new_criminal_laws", "bprd_model_police_manual", "ecourts_judgments"]
        if any(x in text for x in ("odisha", "bhubaneswar", "rasulgarh", "pahala", "cuttack")):
            ids += ["odisha_acts", "odisha_rules", "odisha_notifications","orissa_high_court","odisha_revenue","odisha_urban","bmc","bda","orera","odisha_police","commissionerate_police"]
        if any(x in text for x in ("bank", "payment", "forex", "foreign exchange", "rbi", "loan", "nbfc")):
            ids += ["rbi_master_directions"]
        if any(x in text for x in ("securities", "stock", "investment", "broker", "sebi", "mutual fund")):
            ids += ["sebi_legal"]
        if any(x in text for x in ("telecom", "sms", "commercial communication", "ucc", "spam", "trai")):
            ids += ["trai_directions"]
        out = []
        for sid in ids:
            if sid in self._sources and sid not in out:
                out.append(sid)
        return out

    def source_plan(self, topic: str, jurisdiction: str = "Bhubaneswar, Khordha, Odisha, India") -> dict[str, Any]:
        jurisdiction=self._jurisdiction(jurisdiction)
        topic = str(topic or "").strip()
        if not topic:
            raise ValueError("legal research topic is required")
        ids = self._selected_source_ids(topic, jurisdiction)
        return {
            "topic": topic,
            "jurisdiction": str(jurisdiction or "India"),
            "official_sources": [self._sources[x].as_dict() for x in ids],
            "reference_repositories": [dict(x) for x in REFERENCE_REPOS],
            "authority_policy": self.AUTHORITY_POLICY,
            "verification_rules": [
                "check effective/commencement date and later amendment or repeal",
                "verify statutory text against an official source",
                "verify a case holding against the judgment text",
                "distinguish binding, persuasive, overruled, distinguished and fact-specific authority",
                "state uncertainty instead of inventing a legal conclusion",
            ],
        }

    def analysis_plan(self, issue: str, jurisdiction: str = "Bhubaneswar, Khordha, Odisha, India") -> dict[str, Any]:
        jurisdiction=self._jurisdiction(jurisdiction)
        issue = str(issue or "").strip()
        if not issue:
            raise ValueError("legal issue is required")
        gate = self.risk_gate(issue)
        roles = []
        for profile in LEGAL_SHISHYAS:
            roles.append({
                "shishya": profile.id,
                "role": profile.role,
                "question": profile.question,
                "required_output": list(profile.duties),
            })
        return {
            "parent_rishi": self.PARENT_RISHI,
            "issue": issue,
            "jurisdiction": jurisdiction,
            "risk_gate": gate,
            "workplan": roles,
            "sources": self.source_plan(issue, jurisdiction),
            "qualified_lawyer_review": {
                "required_when": [
                    "criminal exposure or police/court process is active",
                    "material financial/property rights are at stake",
                    "the law is unclear, newly changed or fact-sensitive",
                    "litigation, regulatory enforcement or binding commitments are contemplated",
                ],
                "note": "KRISHNA/Narada provides research and compliance support; it does not replace a licensed advocate.",
            },
        }

    def case_research_plan(self, issue: str, jurisdiction: str = "Bhubaneswar, Khordha, Odisha, India") -> dict[str, Any]:
        jurisdiction=self._jurisdiction(jurisdiction)
        issue = str(issue or "").strip()
        if not issue:
            raise ValueError("case research issue is required")
        return {
            "parent_rishi": self.PARENT_RISHI,
            "mandatory_shishyas": ["judge","vakeel"],
            "issue": issue,
            "jurisdiction": jurisdiction,
            "official_search_sources": [
                self._sources["orissa_high_court"].as_dict(),
                self._sources["supreme_court_verdict_finder"].as_dict(),
                self._sources["ecourts_judgments"].as_dict(),
            ],
            "judge": {
                "mission": "Find the closest verified cases and reconstruct what the courts actually decided before advocacy is drafted.",
                "extract": [
                    "court","bench","case_name","citation","case_number","decision_date","judges",
                    "material_facts","issues","statutes_and_provisions","arguments_recorded",
                    "precedents_relied","precedents_distinguished","ratio","holding","result",
                    "relief_granted_or_refused","binding_status","later_history",
                ],
                "required_search": [
                    "closest fact-match",
                    "favourable precedent",
                    "adverse precedent",
                    "higher-court authority",
                    "later cases following/distinguishing/overruling/qualifying the authority",
                ],
            },
            "vakeel": {
                "mission": "Build the strongest lawful two-sided court argument from verified statutes, evidence and precedent.",
                "argument_packet": [
                    "issues presented",
                    "our strongest argument linked to verified authority",
                    "opponent's strongest counter-argument linked to verified authority",
                    "reply/rebuttal",
                    "why favourable cases match our material facts",
                    "how adverse cases can lawfully be distinguished, if supportable",
                    "procedural objections/prerequisites",
                    "evidence required for each factual proposition",
                    "interim and final remedies",
                    "appeal/review/settlement alternatives",
                ],
                "rules": [
                    "do not hide adverse authority",
                    "do not invent facts, cases, quotations or evidence",
                    "do not advise evasion, concealment, obstruction or false evidence",
                ],
            },
            "comparison_rules": [
                "match material facts as well as legal issue",
                "prefer Supreme Court binding authority, then Orissa High Court for Odisha matters",
                "check whether the relevant statutory text changed after each precedent",
                "search adverse and distinguishing precedent, not only favourable cases",
                "separate the court's findings from party allegations and advocate submissions",
                "never convert precedent similarity into a guaranteed prediction",
            ],
            "result_analysis": {
                "purpose":"Compare what happened in verified analogous cases with our facts.",
                "report":[
                    "outcomes in closest verified cases",
                    "facts helping our position",
                    "facts hurting our position",
                    "controlling legal differences",
                    "missing evidence that could materially change the analysis",
                    "uncertainties and unresolved conflicts in authority",
                ],
                "boundary":"Explain precedent-based implications; never promise or guarantee the present court's result.",
            },
            "review_chain":["judge","vakeel","gautama","narada"],
        }


    def deep_corpus_plan(self, jurisdiction: str = "Bhubaneswar, Khordha, Odisha, India") -> dict[str, Any]:
        """Return the bounded, resumable corpus acquisition contract.

        This is intentionally a plan rather than an unbounded scraper. India Code
        states that updating state and subordinate legislation is continuous, so
        completeness must be measured against official inventories and refreshed.
        """
        state_text = str(jurisdiction or "India")
        sources = ["constitution_2026", "india_code", "india_code_data_report", "egazette"]
        if "odisha" in state_text.lower():
            sources += ["odisha_acts", "odisha_rules", "odisha_notifications"]
        return {
            "parent_rishi": self.PARENT_RISHI,
            "shishya": "constitution",
            "jurisdiction": state_text,
            "goal": "Build a versioned, provenance-backed current-law corpus without overloading official services.",
            "categories": [
                "Constitution and amendments",
                "Acts and amending Acts",
                "Rules",
                "Regulations",
                "Notifications",
                "Orders",
                "Ordinances",
                "Statutes",
                "Circulars",
                "Gazette publications",
                "binding and relevant judicial decisions",
            ],
            "official_inventory_sources": [self._sources[x].as_dict() for x in sources],
            "crawl_contract": {
                "official_hosts_only": True,
                "concurrency": 1,
                "minimum_delay_seconds": 2,
                "resume_from_checkpoint": True,
                "deduplicate_by_sha256": True,
                "preserve_original_bytes": True,
                "preserve_retrieval_metadata": True,
                "respect_robots_terms_and_rate_limits": True,
                "do_not_bypass_captcha_or_access_controls": True,
            },
            "completion_rule": (
                "Do not mark corpus complete until official inventory counts/categories have been "
                "reconciled with locally indexed documents and unresolved gaps are zero or explicitly documented."
            ),
            "coverage_truth": self.COVERAGE_TRUTH,
        }

    def monitor_plan(self) -> dict[str, Any]:
        return {
            "parent_rishi": self.PARENT_RISHI,
            "shishya": "constitution",
            "jurisdiction": "Bhubaneswar, Khordha, Odisha, India",
            "odisha_only": True,
            "operation": "legal_update",
            "recommended_interval_seconds": 21600,
            "method": "fingerprint official source pages/documents; preserve retrieval metadata; research changed sources before promoting any legal conclusion",
            "sources": [x.as_dict() for x in ADVISOR_OFFICIAL_SOURCES if x.monitor],
            "coverage_truth": self.COVERAGE_TRUTH,
        }

    def _fetch(self, source: LegalSourceProfile, timeout: int = 30) -> tuple[bytes, dict[str, str]]:
        if not self._official_host(source.url):
            raise PermissionError("Narada legal fetch is limited to allowlisted official legal hosts")
        req = urllib.request.Request(
            source.url,
            headers={
                "User-Agent": "KRISHNA-Narada-Legal/1.0 (+official-source freshness and compliance research)",
                "Accept": "text/html,application/pdf,text/plain,application/xhtml+xml,*/*;q=0.1",
            },
        )
        with urllib.request.urlopen(req, timeout=max(3, min(int(timeout), 60))) as response:
            final_url = response.geturl()
            if not self._official_host(final_url):
                raise PermissionError("official legal source redirected outside the allowlist")
            data = response.read(int(source.max_bytes) + 1)
            if len(data) > int(source.max_bytes):
                raise ValueError(f"legal source exceeds configured size cap: {source.id}")
            headers = {
                "final_url": str(final_url),
                "content_type": str(response.headers.get("Content-Type") or ""),
                "etag": str(response.headers.get("ETag") or ""),
                "last_modified": str(response.headers.get("Last-Modified") or ""),
            }
        return data, headers

    @staticmethod
    def _extension(content_type: str, url: str) -> str:
        value = str(content_type or "").lower()
        if "pdf" in value or str(url).lower().endswith(".pdf"):
            return ".pdf"
        if "html" in value or "xhtml" in value:
            return ".html"
        if "text/plain" in value:
            return ".txt"
        return ".bin"

    def _resolve_sources(self, source_ids: Iterable[str] | None) -> list[LegalSourceProfile]:
        if source_ids is None:
            return [x for x in ADVISOR_OFFICIAL_SOURCES if x.monitor]
        out = []
        for raw in source_ids:
            sid = str(raw or "").strip()
            if sid not in self._sources:
                raise KeyError(sid)
            if self._sources[sid] not in out:
                out.append(self._sources[sid])
        return out

    @staticmethod
    def _same_origin(seed_url: str, candidate_url: str) -> bool:
        seed=(urllib.parse.urlparse(seed_url).hostname or "").lower()
        candidate=(urllib.parse.urlparse(candidate_url).hostname or "").lower()
        return bool(seed and candidate and (candidate==seed or candidate.endswith("."+seed) or seed.endswith("."+candidate)))

    def _robots_allowed(self, url: str, timeout: int = 12) -> bool:
        parsed=urllib.parse.urlparse(url)
        robots=urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
        rp=urllib.robotparser.RobotFileParser()
        rp.set_url(robots)
        try:
            req=urllib.request.Request(robots,headers={"User-Agent":"KRISHNA-Narada-Legal/1.0"})
            with urllib.request.urlopen(req,timeout=max(3,min(int(timeout),20))) as response:
                text=response.read(512*1024).decode("utf-8","ignore")
            rp.parse(text.splitlines())
            return bool(rp.can_fetch("KRISHNA-Narada-Legal/1.0",url))
        except Exception:
            return False

    def _fetch_crawl_url(self, url: str, max_bytes: int, timeout: int) -> tuple[bytes, dict[str,str]]:
        if not self._official_host(url):
            raise PermissionError("legal corpus crawl is limited to allowlisted official legal hosts")
        req=urllib.request.Request(
            url,
            headers={
                "User-Agent":"KRISHNA-Narada-Legal/1.0 (+bounded public legal corpus sync)",
                "Accept":"text/html,application/pdf,text/plain,application/xhtml+xml,*/*;q=0.1",
            },
        )
        with urllib.request.urlopen(req,timeout=max(3,min(int(timeout),60))) as response:
            final_url=str(response.geturl())
            if not self._official_host(final_url):
                raise PermissionError("legal corpus source redirected outside the official allowlist")
            data=response.read(max(1,int(max_bytes))+1)
            if len(data)>max(1,int(max_bytes)):
                raise ValueError("legal corpus document exceeds configured size cap")
            headers={
                "final_url":final_url,
                "content_type":str(response.headers.get("Content-Type") or ""),
                "etag":str(response.headers.get("ETag") or ""),
                "last_modified":str(response.headers.get("Last-Modified") or ""),
            }
        return data,headers

    def _load_crawl_state(self) -> dict[str,Any]:
        if not self.crawl_state_path.exists():
            return {"schema":"krishna.narada-legal-crawl.v1","sources":{}}
        try:
            raw=json.loads(self.crawl_state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Narada crawl state is unreadable: {type(exc).__name__}") from exc
        if not isinstance(raw,dict) or raw.get("schema")!="krishna.narada-legal-crawl.v1":
            raise RuntimeError("unsupported Narada crawl-state schema")
        raw.setdefault("sources",{})
        return raw

    def _save_crawl_state(self, state: dict[str,Any]) -> None:
        state=dict(state)
        state["updated_at"]=self._now()
        tmp=self.crawl_state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
        tmp.replace(self.crawl_state_path)

    def crawl_official_source(
        self, source_id: str, *, max_documents: int = 25, max_depth: int = 1,
        delay_seconds: float = 2.0, timeout: int = 30,
    ) -> dict[str,Any]:
        """Bounded, resumable official-source discovery and snapshotting."""
        sid=str(source_id or "").strip()
        if sid not in self._sources:
            raise KeyError(sid)
        source=self._sources[sid]
        cap=max(1,min(int(max_documents),100))
        depth_cap=max(0,min(int(max_depth),3))
        delay=max(0.5,min(float(delay_seconds),10.0))
        state=self._load_crawl_state()
        prior=dict((state.get("sources") or {}).get(sid) or {})
        seen=set(str(x) for x in prior.get("seen_urls") or [])
        frontier=list(prior.get("frontier") or [])
        if not frontier:
            frontier=[{"url":source.url,"depth":0}]
        saved=[];skipped=[];errors=[];processed=0
        while frontier and processed<cap:
            item=frontier.pop(0)
            url=str(item.get("url") or "").split("#",1)[0].strip()
            depth=int(item.get("depth") or 0)
            if not url or url in seen:
                continue
            seen.add(url)
            if not self._official_host(url) or not self._same_origin(source.url,url):
                skipped.append({"url":url,"reason":"outside_source_origin"});continue
            if not self._robots_allowed(url,timeout):
                skipped.append({"url":url,"reason":"robots_policy_unverified_or_disallows"});continue
            try:
                data,headers=self._fetch_crawl_url(url,source.max_bytes,timeout)
                processed+=1
                fp=hashlib.sha256(data).hexdigest()
                folder=self.corpus/sid/"crawl";folder.mkdir(parents=True,exist_ok=True)
                ext=self._extension(headers.get("content_type",""),headers.get("final_url") or url)
                target=folder/f"{fp[:24]}{ext}"
                if not target.exists():
                    target.write_bytes(data)
                    meta={"source_id":sid,"source_title":source.title,"url":url,"retrieved_at":self._now(),"fingerprint":fp,"size_bytes":len(data),**headers}
                    target.with_suffix(target.suffix+".json").write_text(json.dumps(meta,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
                    saved.append({"url":url,"path":str(target),"fingerprint":fp})
                else:
                    skipped.append({"url":url,"reason":"identical_snapshot_exists"})
                content_type=str(headers.get("content_type") or "").lower()
                if depth<depth_cap and ("html" in content_type or ext==".html"):
                    parser=_OfficialLinkParser();parser.feed(data.decode("utf-8","ignore"))
                    for href in parser.links:
                        candidate=urllib.parse.urljoin(headers.get("final_url") or url,href).split("#",1)[0]
                        scheme=urllib.parse.urlparse(candidate).scheme.lower()
                        if scheme in {"http","https"} and candidate not in seen and self._official_host(candidate) and self._same_origin(source.url,candidate):
                            frontier.append({"url":candidate,"depth":depth+1})
            except Exception as exc:
                errors.append({"url":url,"error":f"{type(exc).__name__}: {exc}"})
            if frontier and processed<cap:
                time.sleep(delay)
        state.setdefault("sources",{})[sid]={
            "source_id":sid,"seen_urls":sorted(seen),"frontier":frontier[:5000],
            "last_run_at":self._now(),"processed_total":int(prior.get("processed_total") or 0)+processed,
            "saved_total":int(prior.get("saved_total") or 0)+len(saved),
            "complete_for_discovered_frontier":not bool(frontier),
        }
        self._save_crawl_state(state)
        return {
            "source_id":sid,"processed":processed,"saved":saved,"skipped":skipped,"errors":errors,
            "remaining_frontier":len(frontier),"complete_for_discovered_frontier":not bool(frontier),
            "coverage_truth":self.COVERAGE_TRUTH,
        }

    def check_updates(self, source_ids: Iterable[str] | None = None, timeout: int = 30) -> dict[str, Any]:
        checked = []
        changed = []
        unchanged = []
        baselined = []
        errors = []
        for source in self._resolve_sources(source_ids):
            at = self._now()
            try:
                data, headers = self._fetch(source, timeout)
                fp = hashlib.sha256(data).hexdigest()
                previous = dict((self._state.get("sources") or {}).get(source.id) or {})
                baseline = not bool(previous.get("fingerprint"))
                is_changed = bool(previous.get("fingerprint") and previous.get("fingerprint") != fp)
                row = {
                    "source_id": source.id,
                    "title": source.title,
                    "url": source.url,
                    "authority": source.authority,
                    "jurisdiction": source.jurisdiction,
                    "fingerprint": fp,
                    "size_bytes": len(data),
                    "checked_at": at,
                    **headers,
                }
                if is_changed:
                    row["previous_fingerprint"] = previous.get("fingerprint")
                    row["changed_at"] = at
                elif previous.get("changed_at"):
                    row["changed_at"] = previous.get("changed_at")
                self._state.setdefault("sources", {})[source.id] = row
                checked.append(row)
                if baseline:
                    baselined.append(source.id)
                elif is_changed:
                    changed.append(source.id)
                else:
                    unchanged.append(source.id)
            except Exception as exc:
                errors.append({
                    "source_id": source.id,
                    "url": source.url,
                    "error": f"{type(exc).__name__}: {exc}",
                    "checked_at": at,
                })
        self._save_state()
        return {
            "checked": len(checked),
            "changed": changed,
            "unchanged": unchanged,
            "baselined": baselined,
            "errors": errors,
            "at": self._now(),
            "rule": "A changed fingerprint is a research trigger, not proof that the law itself changed.",
        }

    def sync_sources(self, source_ids: Iterable[str] | None = None, timeout: int = 30) -> dict[str, Any]:
        saved = []
        skipped = []
        errors = []
        for source in self._resolve_sources(source_ids):
            try:
                data, headers = self._fetch(source, timeout)
                fp = hashlib.sha256(data).hexdigest()
                folder = self.corpus / source.id
                folder.mkdir(parents=True, exist_ok=True)
                existing = list(folder.glob(f"*_{fp[:16]}.*"))
                if existing:
                    skipped.append({"source_id": source.id, "reason": "identical_snapshot_exists", "path": str(existing[0])})
                    continue
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                ext = self._extension(headers.get("content_type", ""), headers.get("final_url") or source.url)
                target = folder / f"{stamp}_{fp[:16]}{ext}"
                target.write_bytes(data)
                meta = {
                    "source": source.as_dict(),
                    "fingerprint": fp,
                    "size_bytes": len(data),
                    "retrieved_at": self._now(),
                    **headers,
                }
                target.with_suffix(target.suffix + ".json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
                )
                self._state.setdefault("sources", {})[source.id] = {
                    **meta,
                    "source_id": source.id,
                    "cached_path": str(target),
                    "checked_at": meta["retrieved_at"],
                }
                saved.append({"source_id": source.id, "path": str(target), "fingerprint": fp})
            except Exception as exc:
                errors.append({"source_id": source.id, "error": f"{type(exc).__name__}: {exc}"})
        self._save_state()
        return {
            "saved": saved,
            "skipped": skipped,
            "errors": errors,
            "coverage_truth": self.COVERAGE_TRUTH,
        }
