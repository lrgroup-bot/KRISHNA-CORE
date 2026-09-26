from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import re
import urllib.parse
import urllib.request


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


OFFICIAL_SOURCES = (
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
        "indiacode.nic.in", "www.indiacode.nic.in",
        "egazette.gov.in", "www.egazette.gov.in",
        "sci.gov.in", "www.sci.gov.in", "verdictfinder.sci.gov.in",
        "judgments.ecourts.gov.in", "ecourts.gov.in", "www.ecourts.gov.in",
        "mha.gov.in", "www.mha.gov.in",
        "bprd.nic.in", "www.bprd.nic.in",
        "law.odisha.gov.in",
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
        self._sources = {x.id: x for x in OFFICIAL_SOURCES}
        self._state = self._load_state()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

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
    def shishyas() -> list[dict[str, Any]]:
        return [x.as_dict() for x in LEGAL_SHISHYAS]

    def sources(self) -> dict[str, Any]:
        return {
            "official": [x.as_dict() for x in OFFICIAL_SOURCES],
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
            "official_source_count": len(OFFICIAL_SOURCES),
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
        ids = ["constitution_2026", "india_code", "egazette"]
        if any(x in text for x in ("case", "judgment", "judgement", "precedent", "court", "judge", "ratio")):
            ids += ["supreme_court_verdict_finder", "ecourts_judgments", "supreme_court_constitution"]
        if any(x in text for x in ("criminal", "police", "arrest", "fir", "bns", "bnss", "bsa", "evidence", "crime")):
            ids += ["mha_new_criminal_laws", "bprd_model_police_manual", "ecourts_judgments"]
        if any(x in text for x in ("odisha", "bhubaneswar", "rasulgarh", "pahala", "cuttack")):
            ids += ["odisha_acts", "odisha_rules", "odisha_notifications"]
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

    def source_plan(self, topic: str, jurisdiction: str = "India") -> dict[str, Any]:
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

    def analysis_plan(self, issue: str, jurisdiction: str = "India") -> dict[str, Any]:
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

    def case_research_plan(self, issue: str, jurisdiction: str = "India") -> dict[str, Any]:
        issue = str(issue or "").strip()
        if not issue:
            raise ValueError("case research issue is required")
        return {
            "parent_rishi": self.PARENT_RISHI,
            "shishya": "judge",
            "issue": issue,
            "jurisdiction": jurisdiction,
            "official_search_sources": [
                self._sources["supreme_court_verdict_finder"].as_dict(),
                self._sources["ecourts_judgments"].as_dict(),
            ],
            "extract": [
                "court", "case_name", "citation", "case_number", "decision_date",
                "judges", "material_facts", "issues", "statutes_and_provisions",
                "precedents_relied", "precedents_not_relied", "ratio",
                "holding", "result", "binding_status", "later_history",
            ],
            "comparison_rules": [
                "match material facts as well as legal issue",
                "prefer higher and constitutionally binding authority where applicable",
                "check whether the relevant statutory text later changed",
                "search adverse and distinguishing precedent, not only favourable cases",
                "never convert precedent similarity into a guaranteed prediction",
            ],
        }

    def monitor_plan(self) -> dict[str, Any]:
        return {
            "parent_rishi": self.PARENT_RISHI,
            "shishya": "constitution",
            "operation": "legal_update",
            "recommended_interval_seconds": 21600,
            "method": "fingerprint official source pages/documents; preserve retrieval metadata; research changed sources before promoting any legal conclusion",
            "sources": [x.as_dict() for x in OFFICIAL_SOURCES if x.monitor],
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
            return [x for x in OFFICIAL_SOURCES if x.monitor]
        out = []
        for raw in source_ids:
            sid = str(raw or "").strip()
            if sid not in self._sources:
                raise KeyError(sid)
            if self._sources[sid] not in out:
                out.append(self._sources[sid])
        return out

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
