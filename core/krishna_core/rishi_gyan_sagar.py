from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum
import hashlib
import time
from typing import Iterable
from urllib.parse import quote_plus, urlencode

from .rishi_council import RishiCouncil


class AccessMode(IntEnum):
    READ = 1
    INDEX = 2
    ARCHIVE = 3
    TRAIN = 4


MODE_NAME = {
    AccessMode.READ: "read",
    AccessMode.INDEX: "index",
    AccessMode.ARCHIVE: "archive",
    AccessMode.TRAIN: "train",
}


@dataclass(frozen=True)
class SourcePolicy:
    id: str
    name: str
    family: str
    kinds: tuple[str, ...]
    priority: str
    adapter: str
    base_url: str
    docs_url: str
    free_core: bool
    machine_access: bool
    auth: str
    default_max_mode: str
    per_item_rights_required: bool
    metadata_rights: str
    bulk_policy: str
    rishis: tuple[str, ...]
    domains: tuple[str, ...]
    evidence_role: str
    notes: str = ""

    def public(self) -> dict:
        row = asdict(self)
        row["kinds"] = list(self.kinds)
        row["rishis"] = list(self.rishis)
        row["domains"] = list(self.domains)
        return row


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    requested_mode: str
    reason: str
    attribution_required: bool = False
    share_alike: bool = False
    commercial_allowed: bool | None = None
    redistribution_allowed: bool | None = None
    training_allowed: bool | None = None
    review_required: bool = False

    def public(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeRecord:
    record_id: str
    title: str
    source_id: str
    source_url: str
    source_type: str
    identifier: str
    authors: tuple[str, ...]
    publication_date: str
    language: str
    license_id: str
    rights: dict
    checksum: str
    retrieved_at: float
    peer_reviewed: bool | None
    retracted: bool | None
    primary: bool
    rishi_owner: str
    knowledge_track: str
    local_path: str
    notes: str

    def public(self) -> dict:
        row = asdict(self)
        row["authors"] = list(self.authors)
        return row


def _source(
    id: str,
    name: str,
    family: str,
    kinds: Iterable[str],
    priority: str,
    adapter: str,
    base_url: str,
    docs_url: str,
    *,
    free_core: bool = True,
    machine_access: bool = True,
    auth: str = "none",
    default_max_mode: str = "index",
    per_item_rights_required: bool = True,
    metadata_rights: str = "source-terms",
    bulk_policy: str = "bounded",
    rishis: Iterable[str] = (),
    domains: Iterable[str] = (),
    evidence_role: str = "discovery",
    notes: str = "",
) -> SourcePolicy:
    return SourcePolicy(
        id=id,
        name=name,
        family=family,
        kinds=tuple(kinds),
        priority=priority,
        adapter=adapter,
        base_url=base_url,
        docs_url=docs_url,
        free_core=free_core,
        machine_access=machine_access,
        auth=auth,
        default_max_mode=default_max_mode,
        per_item_rights_required=per_item_rights_required,
        metadata_rights=metadata_rights,
        bulk_policy=bulk_policy,
        rishis=tuple(rishis),
        domains=tuple(domains),
        evidence_role=evidence_role,
        notes=notes,
    )


SOURCE_CATALOG: tuple[SourcePolicy, ...] = (
    _source(
        "openalex", "OpenAlex", "scholarly-graph", ("paper", "author", "institution", "topic"), "P0",
        "rest-json", "https://api.openalex.org/works", "https://help.openalex.org/api/",
        auth="optional-free-api-key", metadata_rights="open-metadata", bulk_policy="cursor-or-snapshot",
        rishis=("veda-vyasa", "gautama", "bharadvaja", "vishwamitra"),
        domains=("research", "science", "engineering", "medicine", "citations"), evidence_role="discovery",
        notes="Primary scholarly discovery engine. Unpaywall search is retired; OpenAlex is the successor search path.",
    ),
    _source(
        "crossref", "Crossref", "doi-metadata", ("paper", "book", "chapter", "dataset", "metadata"), "P0",
        "rest-json", "https://api.crossref.org/works", "https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
        auth="none-polite-mailto", metadata_rights="mostly-open-metadata", bulk_policy="polite-rate-or-public-data-file",
        rishis=("veda-vyasa", "gautama", "bharadvaja"), domains=("doi", "metadata", "retractions", "funding", "citations"),
        evidence_role="metadata-verification", notes="Prefer polite requests with contact mailto; abstracts can have separate copyright.",
    ),
    _source(
        "unpaywall", "Unpaywall", "oa-resolver", ("paper", "open-access-location"), "P0",
        "rest-json-doi", "https://api.unpaywall.org/v2", "https://data.unpaywall.org/products/api",
        auth="email-required", metadata_rights="open-metadata", bulk_policy="100k-calls-day-or-snapshot",
        rishis=("veda-vyasa", "gautama", "bharadvaja"), domains=("open access", "doi", "full text"),
        evidence_role="full-text-resolver", notes="DOI resolver only. Search endpoint retired 2026-09-18.",
    ),
    _source(
        "core", "CORE", "open-research", ("paper", "repository", "full-text"), "P0",
        "rest-json-api-key", "https://api.core.ac.uk/", "https://core.ac.uk/services/api",
        auth="free-api-key", metadata_rights="source-terms", bulk_policy="api-quota",
        rishis=("veda-vyasa", "gautama", "bharadvaja"), domains=("research", "repositories", "open access", "full text"),
        evidence_role="full-text-resolver",
    ),
    _source(
        "doaj", "Directory of Open Access Journals", "oa-journals", ("journal", "paper", "metadata"), "P0",
        "oai-pmh", "https://doaj.org/oai.article", "https://doaj.org/docs/oai-pmh/",
        default_max_mode="index", per_item_rights_required=True, metadata_rights="CC0-1.0", bulk_policy="oai-or-data-dump",
        rishis=("veda-vyasa", "gautama", "bharadvaja"), domains=("open access", "journals", "peer review"),
        evidence_role="quality-filter",
    ),
    _source(
        "doab", "Directory of Open Access Books", "oa-books", ("book", "chapter", "metadata"), "P0",
        "oai-pmh", "https://directory.doabooks.org/oai/request", "https://www.doabooks.org/en/article/metadata",
        metadata_rights="CC0-1.0", bulk_policy="oai-or-export", rishis=("veda-vyasa", "bharadvaja", "agastya"),
        domains=("books", "monographs", "humanities", "science"), evidence_role="book-discovery",
        notes="Metadata is CC0; each linked book retains its own licence and must pass item rights review.",
    ),
    _source(
        "oapen", "OAPEN Library", "oa-books", ("book", "chapter", "full-text", "metadata"), "P0",
        "oai-pmh", "https://library.oapen.org/oai/request", "https://www.oapen.org/article/metadata",
        metadata_rights="open-metadata", bulk_policy="oai-json-csv-onix", rishis=("veda-vyasa", "bharadvaja", "agastya"),
        domains=("books", "monographs", "humanities", "social science"), evidence_role="book-full-text-resolver",
    ),
    _source(
        "europe-pmc", "Europe PMC", "biomedical", ("paper", "preprint", "full-text", "citation"), "P0",
        "rest-json-xml", "https://www.ebi.ac.uk/europepmc/webservices/rest/search", "https://dev.europepmc.org/RestfulWebService",
        metadata_rights="source-terms", bulk_policy="api-bounded", rishis=("sushruta", "charaka", "kashyapa", "gautama"),
        domains=("medicine", "biology", "clinical", "preprints", "citations"), evidence_role="biomedical-discovery",
    ),
    _source(
        "pmc", "PubMed Central", "biomedical-fulltext", ("paper", "full-text", "metadata"), "P0",
        "oai-pmh-bioc", "https://pmc.ncbi.nlm.nih.gov/tools/oai/", "https://pmc.ncbi.nlm.nih.gov/tools/oai/",
        default_max_mode="index", per_item_rights_required=True, metadata_rights="source-terms", bulk_policy="official-oai-bioc-cloud-only",
        rishis=("sushruta", "charaka", "kashyapa", "gautama"), domains=("medicine", "biology", "clinical", "full text"),
        evidence_role="biomedical-full-text", notes="Not every PMC article is reusable. Full-text automation must use official PMC retrieval services and item licences.",
    ),
    _source(
        "shodhganga", "Shodhganga", "india-theses", ("thesis", "dissertation", "repository"), "P0",
        "browser-repository", "https://shodhganga.inflibnet.ac.in/", "https://shodhganga.inflibnet.ac.in/",
        machine_access=False, default_max_mode="read", metadata_rights="repository-terms", bulk_policy="no-unverified-harvest",
        rishis=("veda-vyasa", "bharadvaja", "gautama"), domains=("india", "theses", "doctoral research", "literature review"),
        evidence_role="thesis-discovery", notes="Use repository browsing until an official machine endpoint is verified in runtime configuration.",
    ),
    _source(
        "sarit", "SARIT", "indic-classical", ("classical-text", "tei", "book"), "P0",
        "tei-xml", "https://sarit.indology.info/", "https://sarit.indology.info/apps/sarit-pm/docs/welcome.html",
        default_max_mode="index", per_item_rights_required=True, metadata_rights="creative-commons-per-item", bulk_policy="download-per-text",
        rishis=("veda-vyasa", "panini", "agastya", "sushruta", "yajnavalkya"),
        domains=("sanskrit", "classical india", "ayurveda", "law", "philosophy", "tei"), evidence_role="primary-classical-text",
        notes="Texts are typically Creative Commons but the exact licence is encoded per edition and must be preserved.",
    ),
    _source(
        "dcs", "Digital Corpus of Sanskrit", "indic-linguistics", ("corpus", "classical-text", "linguistic-analysis"), "P0",
        "browser-corpus", "https://www.sanskrit-linguistics.org/dcs/index.php", "https://www.sanskrit-linguistics.org/dcs/index.php",
        machine_access=False, default_max_mode="read", metadata_rights="source-terms", bulk_policy="use-published-downloads-only",
        rishis=("panini", "veda-vyasa", "agastya", "patanjali"), domains=("sanskrit", "morphology", "lexicon", "philology"),
        evidence_role="linguistic-corpus", notes="Large parts of annotations are published for download; do not scrape dynamic detail pages.",
    ),
    _source(
        "ndli", "National Digital Library of India", "india-library", ("book", "paper", "course", "catalog"), "P1",
        "browser-library", "https://ndl.iitkgp.ac.in/", "https://ndl.iitkgp.ac.in/",
        machine_access=False, default_max_mode="read", metadata_rights="source-terms", bulk_policy="no-unverified-harvest",
        rishis=("veda-vyasa", "bharadvaja", "agastya"), domains=("india", "books", "education", "licensed access"),
        evidence_role="library-discovery",
    ),
    _source(
        "nptel", "NPTEL", "india-courses", ("course", "lecture", "reading"), "P0",
        "browser-course", "https://www.swayam.gov.in/nc_details/NPTEL", "https://www.swayam.gov.in/nc_details/NPTEL",
        machine_access=False, default_max_mode="read", metadata_rights="source-terms", bulk_policy="course-access-not-bulk-copy",
        rishis=("bharadvaja", "vishwamitra", "kanada", "sushruta"), domains=("engineering", "science", "technology", "education"),
        evidence_role="curriculum",
    ),
    _source(
        "swayam", "SWAYAM", "india-courses", ("course", "lecture", "reading", "assessment"), "P0",
        "browser-course", "https://swayam.gov.in/search_courses", "https://www.swayam.gov.in/about",
        machine_access=False, default_max_mode="read", metadata_rights="source-terms", bulk_policy="course-access-not-bulk-copy",
        rishis=("bharadvaja", "veda-vyasa"), domains=("education", "engineering", "humanities", "management", "science"),
        evidence_role="curriculum",
    ),
    _source(
        "arxiv", "arXiv", "preprints", ("preprint", "paper", "metadata"), "P1",
        "atom-api", "https://export.arxiv.org/api/query", "https://github.com/arXiv/arxiv-docs/blob/develop/source/help/api/user-manual.md",
        metadata_rights="source-terms", bulk_policy="api-terms-and-throttle", rishis=("vishwamitra", "kanada", "atri", "bharadvaja", "gautama"),
        domains=("physics", "mathematics", "computer science", "ai", "quantitative research"), evidence_role="frontier-preprint",
        notes="Preprint status must remain explicit; never promote preprints as consensus evidence automatically.",
    ),
    _source(
        "openreview", "OpenReview", "peer-review", ("paper", "review", "discussion", "preprint"), "P1",
        "rest-json", "https://api2.openreview.net", "https://docs.openreview.net/getting-started/using-the-api",
        metadata_rights="source-terms", bulk_policy="api-bounded", rishis=("vishwamitra", "gautama", "bharadvaja"),
        domains=("ai", "machine learning", "peer review", "conference"), evidence_role="review-context",
    ),
    _source(
        "epo-ops", "EPO Open Patent Services", "patents", ("patent", "legal-status", "claims", "bibliography"), "P1",
        "rest-xml-oauth", "https://ops.epo.org/3.2/rest-services/", "https://www.epo.org/en/searching-for-patents/data/web-services/ops",
        auth="registration-oauth", metadata_rights="epo-ops-terms", bulk_policy="free-up-to-4gb-week-fair-use",
        rishis=("vishwamitra", "kanada", "vishvakarma", "gautama"), domains=("patents", "inventions", "prior art", "technology"),
        evidence_role="patent-prior-art", notes="Free threshold is bounded; never cross into paid usage under KRISHNA zero-spend policy.",
    ),
    _source(
        "rfc-editor", "RFC Editor", "internet-standards", ("standard", "rfc", "protocol"), "P0",
        "rsync-feed", "rsync.rfc-editor.org::rfcs-text-only", "https://www.rfc-editor.org/series/rfc-download/",
        default_max_mode="archive", per_item_rights_required=False, metadata_rights="ietf-rfc-publication-terms", bulk_policy="official-rsync-mirror",
        rishis=("vishwamitra", "jamadagni", "bharadvaja"), domains=("networking", "internet", "protocol", "security"),
        evidence_role="normative-standard",
    ),
    _source(
        "ietf-datatracker", "IETF Datatracker", "internet-drafts", ("standard", "draft", "working-group", "metadata"), "P1",
        "rest-json", "https://datatracker.ietf.org/api/v1/", "https://datatracker.ietf.org/api/",
        metadata_rights="source-terms", bulk_policy="api-bounded", rishis=("vishwamitra", "jamadagni", "bharadvaja"),
        domains=("networking", "internet", "protocol", "standards development"), evidence_role="emerging-standard",
    ),
    _source(
        "w3c", "W3C Technical Reports", "web-standards", ("standard", "draft", "note", "registry"), "P0",
        "web-standard-index", "https://www.w3.org/TR/", "https://www.w3.org/TR/",
        default_max_mode="index", per_item_rights_required=True, metadata_rights="w3c-document-terms", bulk_policy="bounded-crawl-or-direct-doc",
        rishis=("vishvakarma", "vishwamitra", "jamadagni", "bharadvaja"), domains=("web", "accessibility", "html", "css", "privacy", "security"),
        evidence_role="normative-standard",
    ),
    _source(
        "nist", "NIST", "government-technical", ("standard", "guideline", "dataset", "publication"), "P0",
        "api-and-publications", "https://data.nist.gov/", "https://www.nist.gov/open/information-developers",
        default_max_mode="index", per_item_rights_required=True, metadata_rights="us-government-and-item-terms", bulk_policy="official-api",
        rishis=("jamadagni", "kanada", "vishwamitra", "gautama"), domains=("cybersecurity", "materials", "measurement", "science", "standards"),
        evidence_role="government-technical-authority",
    ),
    _source(
        "github", "GitHub", "source-code", ("code", "repository", "issue", "release"), "P0",
        "connected-github", "https://api.github.com/", "https://docs.github.com/en/rest",
        auth="authorized-connector", default_max_mode="read", per_item_rights_required=True, metadata_rights="service-terms", bulk_policy="connector-rate-limits",
        rishis=("vishwamitra", "vishvakarma", "jamadagni", "bharadvaja"), domains=("code", "software", "implementation", "engineering"),
        evidence_role="implementation-evidence", notes="Repository licence governs code reuse. Absence of a licence means no reuse grant.",
    ),
    _source(
        "software-heritage", "Software Heritage", "source-code-archive", ("code", "repository", "revision", "release"), "P0",
        "rest-json", "https://archive.softwareheritage.org/api/1/", "https://docs.softwareheritage.org/",
        default_max_mode="read", per_item_rights_required=True, metadata_rights="factual-metadata", bulk_policy="pointwise-api-no-mass-extraction",
        rishis=("vishwamitra", "vishvakarma", "jamadagni", "bharadvaja"), domains=("code", "software history", "provenance"),
        evidence_role="implementation-provenance",
    ),
    _source(
        "huggingface", "Hugging Face Hub", "ai-artifacts", ("model", "dataset", "code", "model-card", "dataset-card"), "P1",
        "rest-json", "https://huggingface.co/api/models", "https://huggingface.co/docs/hub/api",
        default_max_mode="read", per_item_rights_required=True, metadata_rights="service-and-repo-terms", bulk_policy="api-bounded",
        rishis=("vishwamitra", "bharadvaja", "jamadagni", "gautama"), domains=("ai", "models", "datasets", "machine learning"),
        evidence_role="ai-artifact-discovery", notes="Model/dataset card metadata and repository licence must be inspected before any download or execution.",
    ),
    _source(
        "gutenberg", "Project Gutenberg", "public-domain-books", ("book", "ebook", "catalog"), "P1",
        "opds", "https://www.gutenberg.org/ebooks/search.opds/", "https://www.gutenberg.org/ebooks/offline_catalogs.html",
        default_max_mode="index", per_item_rights_required=True, metadata_rights="catalog-terms", bulk_policy="opds-or-mirror",
        rishis=("veda-vyasa", "agastya", "bharadvaja"), domains=("books", "literature", "history", "public domain"),
        evidence_role="book-full-text", notes="Public-domain status can vary by jurisdiction; preserve item provenance and do not assume worldwide status.",
    ),
    _source(
        "openlibrary", "Open Library", "book-catalog", ("book", "author", "edition", "catalog"), "P1",
        "rest-json", "https://openlibrary.org/search.json", "https://openlibrary.org/developers/api",
        default_max_mode="index", per_item_rights_required=True, metadata_rights="open-library-terms", bulk_policy="low-volume-api-or-monthly-dumps",
        rishis=("veda-vyasa", "agastya", "bharadvaja"), domains=("books", "authors", "editions", "borrowing"),
        evidence_role="book-discovery", notes="Do not use the web API as a high-volume backend. Identify requests and use monthly dumps for bulk metadata.",
    ),
    _source(
        "google-books", "Google Books", "book-discovery", ("book", "preview", "metadata"), "P2",
        "rest-json", "https://www.googleapis.com/books/v1/volumes", "https://developers.google.com/books/docs/v1/using",
        default_max_mode="read", per_item_rights_required=True, metadata_rights="service-terms", bulk_policy="api-bounded",
        rishis=("veda-vyasa", "bharadvaja"), domains=("books", "metadata", "preview", "availability"), evidence_role="availability-resolver",
    ),
    _source(
        "internet-archive", "Internet Archive", "digital-archive", ("book", "audio", "video", "software", "web"), "P1",
        "rest-json", "https://archive.org/advancedsearch.php", "https://archive.org/developers/",
        default_max_mode="read", per_item_rights_required=True, metadata_rights="item-and-service-terms", bulk_policy="api-and-item-policies",
        rishis=("veda-vyasa", "agastya", "bharadvaja"), domains=("archive", "books", "history", "media", "software"), evidence_role="archive-discovery",
    ),
    _source(
        "wayback", "Wayback Machine", "web-history", ("web", "snapshot", "historical-source"), "P1",
        "cdx-browser", "https://web.archive.org/", "https://web.archive.org/",
        default_max_mode="read", per_item_rights_required=True, metadata_rights="archived-content-rights-vary", bulk_policy="bounded-historical-retrieval",
        rishis=("agastya", "gautama", "veda-vyasa"), domains=("history", "web evidence", "provenance"), evidence_role="historical-web-evidence",
    ),
    _source(
        "mit-ocw", "MIT OpenCourseWare", "open-courses", ("course", "lecture", "reading", "assessment"), "P2",
        "browser-course", "https://ocw.mit.edu/search/", "https://ocw.mit.edu/pages/get-started/",
        machine_access=False, default_max_mode="read", per_item_rights_required=True, metadata_rights="course-license", bulk_policy="respect-course-license",
        rishis=("bharadvaja", "vishwamitra", "kanada"), domains=("education", "engineering", "science", "mathematics"), evidence_role="curriculum",
    ),
    _source(
        "muktabodha", "Muktabodha Digital Library", "indic-classical", ("classical-text", "manuscript", "etext"), "P1",
        "browser-library", "https://muktabodha.org/digital-library/", "https://muktabodha.org/digital-library/",
        machine_access=False, default_max_mode="read", metadata_rights="source-terms", bulk_policy="no-unverified-harvest",
        rishis=("veda-vyasa", "agastya", "patanjali", "yajnavalkya"), domains=("sanskrit", "shaiva", "shakta", "yoga", "traditions"), evidence_role="primary-classical-text",
    ),
    _source(
        "gretil", "GRETIL", "indic-classical", ("classical-text", "etext", "corpus"), "P1",
        "browser-corpus", "https://gretil.sub.uni-goettingen.de/", "https://gretil.sub.uni-goettingen.de/gretil.html",
        machine_access=False, default_max_mode="read", metadata_rights="collection-specific", bulk_policy="scholarly-reference-only-where-stated",
        rishis=("veda-vyasa", "panini", "agastya", "yajnavalkya"), domains=("sanskrit", "pali", "prakrit", "indic texts"), evidence_role="primary-classical-text",
    ),
    _source(
        "iitk-gita", "IIT Kanpur Gita Supersite", "indic-classical", ("classical-text", "commentary", "translation"), "P1",
        "browser-library", "https://www.gitasupersite.iitk.ac.in/", "https://www.gitasupersite.iitk.ac.in/",
        machine_access=False, default_max_mode="read", metadata_rights="commentary-specific", bulk_policy="no-unverified-harvest",
        rishis=("veda-vyasa", "yajnavalkya", "patanjali", "agastya"), domains=("gita", "upanishads", "yoga", "ramayana", "commentary"),
        evidence_role="classical-commentary",
    ),
)

SOURCE_BY_ID = {source.id: source for source in SOURCE_CATALOG}

_BLOCKED_SOURCE_IDS = {"sci-hub", "temp-mail", "10-minute-mail"}

_DOMAIN_HINTS = {
    "medicine": {"medicine", "medical", "clinical", "surgery", "health", "disease", "pharmacology", "diagnosis"},
    "sanskrit": {"sanskrit", "veda", "vedic", "upanishad", "gita", "ayurveda", "shastra", "classical indian"},
    "technology": {"technology", "engineering", "software", "ai", "robotics", "network", "cyber", "computer", "protocol"},
    "books": {"book", "books", "textbook", "monograph", "edition", "author"},
    "patents": {"patent", "invention", "prior art", "claims"},
    "india": {"india", "indian", "iit", "iisc", "thesis", "doctoral"},
}


def _license_key(value: str) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def _mode(value: AccessMode | str) -> AccessMode:
    if isinstance(value, AccessMode):
        return value
    text = str(value or "").strip().lower()
    for key, name in MODE_NAME.items():
        if text == name:
            return key
    raise ValueError("invalid access mode")


class RishiGyanSagar:
    """Rights-aware knowledge-source fabric for BRAHMAGYAN and the Rishi Council.

    This class does not make network calls by itself. It defines verified source
    contracts, routing, request plans, and conservative reuse decisions. Actual
    HTTP/browser execution remains behind KRISHNA's browser/connector/action gates.
    """

    VERSION = "rishi-gyan-sagar-v1"

    def __init__(self, council: RishiCouncil | None = None):
        self.council = council or RishiCouncil()

    def source(self, source_id: str) -> dict:
        sid = str(source_id or "").strip().lower()
        if sid in _BLOCKED_SOURCE_IDS:
            raise PermissionError(f"{sid} is not an approved KRISHNA knowledge source")
        source = SOURCE_BY_ID.get(sid)
        if not source:
            raise KeyError(source_id)
        return source.public()

    def list_sources(self, priority: str | None = None, machine_only: bool = False) -> list[dict]:
        rows = SOURCE_CATALOG
        if priority:
            rows = tuple(x for x in rows if x.priority == str(priority).upper())
        if machine_only:
            rows = tuple(x for x in rows if x.machine_access)
        return [x.public() for x in rows]

    def source_status(self) -> dict:
        priorities: dict[str, int] = {}
        adapters: dict[str, int] = {}
        for source in SOURCE_CATALOG:
            priorities[source.priority] = priorities.get(source.priority, 0) + 1
            adapters[source.adapter] = adapters.get(source.adapter, 0) + 1
        return {
            "version": self.VERSION,
            "source_count": len(SOURCE_CATALOG),
            "machine_access_sources": len([x for x in SOURCE_CATALOG if x.machine_access]),
            "priorities": priorities,
            "adapters": adapters,
            "policy": "read, index, archive and train are separate rights; unknown content rights never auto-upgrade to archive/train",
        }

    def research_plan(
        self,
        topic: str,
        rishi_id: str | None = None,
        kinds: Iterable[str] | None = None,
        max_sources: int = 12,
    ) -> dict:
        text = str(topic or "").strip().lower()
        if not text:
            raise ValueError("topic is required")
        profile = self.council.get(rishi_id) if rishi_id else self.council.select(topic, 1)[0]
        wanted_kinds = {str(x).strip().lower() for x in (kinds or ()) if str(x).strip()}
        tokens = {x for x in text.replace("/", " ").replace("-", " ").split() if len(x) > 2}
        expanded = set(tokens)
        for hints in _DOMAIN_HINTS.values():
            if hints & tokens:
                expanded |= hints
        scored = []
        for source in SOURCE_CATALOG:
            score = 0
            if source.priority == "P0": score += 40
            elif source.priority == "P1": score += 25
            elif source.priority == "P2": score += 10
            if source.machine_access: score += 5
            if profile["id"] in source.rishis: score += 35
            source_terms = set(source.domains) | set(source.kinds)
            for term in source_terms:
                lowered = term.lower()
                if lowered in text or any(tok in lowered for tok in expanded):
                    score += 9
            if wanted_kinds and wanted_kinds & set(source.kinds):
                score += 20
            if source.evidence_role in {"normative-standard", "metadata-verification", "quality-filter", "primary-classical-text"}:
                score += 4
            if score > 0:
                scored.append((score, source))
        scored.sort(key=lambda row: (-row[0], row[1].priority, row[1].name.lower()))
        selected = [source.public() | {"score": score} for score, source in scored[:max(1, min(int(max_sources), 30))]]
        return {
            "topic": topic,
            "lead_rishi": profile["id"],
            "lead_rishi_name": profile["display_name"],
            "rishi_evidence_rules": list(profile.get("evidence_rules") or []),
            "sources": selected,
            "mandatory_reviewers": ["gautama", "veda-vyasa"],
            "policy": "discover broadly, resolve lawful full text, preserve source type, challenge claims, then promote through BRAHMAGYAN/Gyan-Bhandar",
        }

    @staticmethod
    def request_plan(source_id: str, query: str, *, email: str = "", api_key_ref: str = "") -> dict:
        sid = str(source_id or "").strip().lower()
        if sid in _BLOCKED_SOURCE_IDS:
            raise PermissionError(f"{sid} is blocked")
        source = SOURCE_BY_ID.get(sid)
        if not source:
            raise KeyError(source_id)
        q = str(query or "").strip()
        if not q:
            raise ValueError("query is required")
        url = source.base_url
        headers = {"Accept": "application/json, application/xml;q=0.8, text/plain;q=0.5"}
        requires_browser = not source.machine_access
        secret_required = source.auth in {"free-api-key", "registration-oauth", "authorized-connector"}
        if sid == "openalex":
            url = f"{source.base_url}?{urlencode({'search': q, 'per_page': 25})}"
        elif sid == "crossref":
            params = {"query.bibliographic": q, "rows": 20}
            if email:
                params["mailto"] = email
            url = f"{source.base_url}?{urlencode(params)}"
        elif sid == "europe-pmc":
            url = f"{source.base_url}?{urlencode({'query': q, 'format': 'json', 'pageSize': 25})}"
        elif sid == "openlibrary":
            url = f"{source.base_url}?{urlencode({'q': q, 'limit': 25})}"
        elif sid == "google-books":
            url = f"{source.base_url}?{urlencode({'q': q, 'maxResults': 25})}"
        elif sid == "arxiv":
            url = f"{source.base_url}?{urlencode({'search_query': 'all:' + q, 'start': 0, 'max_results': 25})}"
        elif sid == "huggingface":
            url = f"{source.base_url}?{urlencode({'search': q, 'limit': 25})}"
        elif sid == "internet-archive":
            params = [("q", q), ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "creator"), ("fl[]", "date"), ("rows", 25), ("output", "json")]
            url = f"{source.base_url}?{urlencode(params)}"
        elif sid == "gutenberg":
            url = f"{source.base_url}?query={quote_plus(q)}"
        return {
            "source_id": sid,
            "adapter": source.adapter,
            "url": url,
            "headers": headers,
            "requires_browser": requires_browser,
            "auth": source.auth,
            "secret_required": secret_required,
            "api_key_ref": str(api_key_ref or ""),
            "free_core": source.free_core,
            "bulk_policy": source.bulk_policy,
            "zero_spend_rule": "never upgrade to a paid tier or exceed a free threshold automatically",
        }

    @staticmethod
    def doi_resolution_plan(doi: str, email: str) -> list[dict]:
        clean = str(doi or "").strip()
        if not clean or "/" not in clean:
            raise ValueError("valid DOI is required")
        mail = str(email or "").strip()
        if not mail or "@" not in mail:
            raise ValueError("contact email is required for Unpaywall")
        return [
            {
                "source_id": "crossref",
                "purpose": "metadata and retraction/licence context",
                "url": f"https://api.crossref.org/works/{quote_plus(clean)}?{urlencode({'mailto': mail})}",
            },
            {
                "source_id": "unpaywall",
                "purpose": "lawful open-access location resolver",
                "url": f"https://api.unpaywall.org/v2/{quote_plus(clean)}?{urlencode({'email': mail})}",
            },
        ]

    @staticmethod
    def rights_decision(
        requested_mode: AccessMode | str,
        *,
        license_id: str = "",
        source_default_max_mode: str = "read",
        commercial_context: bool = True,
        explicit_permission: bool = False,
    ) -> RightsDecision:
        requested = _mode(requested_mode)
        max_default = _mode(source_default_max_mode)
        key = _license_key(license_id)

        if explicit_permission:
            return RightsDecision(
                True, MODE_NAME[requested], "explicit permission recorded",
                commercial_allowed=True, redistribution_allowed=True,
                training_allowed=True, review_required=False,
            )

        if requested <= max_default and requested <= AccessMode.INDEX:
            return RightsDecision(
                True, MODE_NAME[requested], "allowed by source-level read/index policy",
                commercial_allowed=None, redistribution_allowed=False,
                training_allowed=False,
            )

        public = {"cc0", "cc0-1.0", "public-domain", "publicdomain", "pd"}
        attribution = {"cc-by", "cc-by-3.0", "cc-by-4.0"}
        share_alike = {"cc-by-sa", "cc-by-sa-3.0", "cc-by-sa-4.0"}
        noncommercial = {"cc-by-nc", "cc-by-nc-3.0", "cc-by-nc-4.0", "cc-by-nc-sa", "cc-by-nc-sa-4.0"}
        no_derivatives = {"cc-by-nd", "cc-by-nd-4.0", "cc-by-nc-nd", "cc-by-nc-nd-4.0"}
        permissive_code = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc"}

        if key in public:
            return RightsDecision(True, MODE_NAME[requested], "public-domain/CC0 licence permits reuse", commercial_allowed=True,
                                  redistribution_allowed=True, training_allowed=True)
        if key in attribution:
            return RightsDecision(True, MODE_NAME[requested], "CC BY permits reuse with attribution", attribution_required=True,
                                  commercial_allowed=True, redistribution_allowed=True, training_allowed=True)
        if key in share_alike:
            return RightsDecision(True, MODE_NAME[requested], "CC BY-SA permits reuse with attribution/share-alike obligations",
                                  attribution_required=True, share_alike=True, commercial_allowed=True,
                                  redistribution_allowed=True, training_allowed=True, review_required=requested == AccessMode.TRAIN)
        if key in noncommercial:
            if commercial_context and requested >= AccessMode.ARCHIVE:
                return RightsDecision(False, MODE_NAME[requested], "non-commercial licence is incompatible with automatic commercial-context reuse",
                                      attribution_required=True, commercial_allowed=False, redistribution_allowed=None,
                                      training_allowed=False, review_required=True)
            return RightsDecision(requested <= AccessMode.ARCHIVE, MODE_NAME[requested], "non-commercial licence requires non-commercial handling",
                                  attribution_required=True, commercial_allowed=False, redistribution_allowed=True,
                                  training_allowed=False, review_required=True)
        if key in no_derivatives:
            if requested == AccessMode.TRAIN:
                return RightsDecision(False, "train", "no-derivatives content is never auto-approved for training",
                                      attribution_required=True, commercial_allowed=None, redistribution_allowed=True,
                                      training_allowed=False, review_required=True)
            return RightsDecision(requested <= AccessMode.ARCHIVE, MODE_NAME[requested], "verbatim archive can be allowed; adaptations require review",
                                  attribution_required=True, commercial_allowed=None, redistribution_allowed=True,
                                  training_allowed=False, review_required=True)
        if key in permissive_code:
            if requested == AccessMode.TRAIN:
                return RightsDecision(False, "train", "software licence alone does not auto-authorize model-training treatment in KRISHNA",
                                      attribution_required=True, commercial_allowed=True, redistribution_allowed=True,
                                      training_allowed=None, review_required=True)
            return RightsDecision(requested <= AccessMode.ARCHIVE, MODE_NAME[requested], "permissive software licence allows code reuse subject to notice terms",
                                  attribution_required=True, commercial_allowed=True, redistribution_allowed=True,
                                  training_allowed=None, review_required=requested == AccessMode.ARCHIVE)

        if requested <= max_default:
            return RightsDecision(True, MODE_NAME[requested], "within source default access ceiling", redistribution_allowed=False,
                                  training_allowed=False)
        return RightsDecision(False, MODE_NAME[requested], "unknown or item-specific rights cannot be auto-upgraded beyond the source default",
                              commercial_allowed=None, redistribution_allowed=None, training_allowed=False, review_required=True)

    def make_record(
        self,
        *,
        title: str,
        source_id: str,
        source_url: str = "",
        source_type: str = "unknown",
        identifier: str = "",
        authors: Iterable[str] = (),
        publication_date: str = "",
        language: str = "",
        license_id: str = "",
        checksum: str = "",
        peer_reviewed: bool | None = None,
        retracted: bool | None = None,
        primary: bool = False,
        rishi_owner: str = "veda-vyasa",
        knowledge_track: str = "general",
        local_path: str = "",
        notes: str = "",
    ) -> dict:
        source = SOURCE_BY_ID.get(str(source_id or "").strip().lower())
        if not source:
            raise KeyError(source_id)
        self.council.get(rishi_owner)
        identity = "|".join((source.id, identifier, source_url, title)).lower()
        record_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        rights = {
            mode: self.rights_decision(mode, license_id=license_id, source_default_max_mode=source.default_max_mode).public()
            for mode in ("read", "index", "archive", "train")
        }
        row = KnowledgeRecord(
            record_id=record_id,
            title=str(title or "").strip()[:1000],
            source_id=source.id,
            source_url=str(source_url or "").strip()[:3000],
            source_type=str(source_type or "unknown").strip().lower()[:100],
            identifier=str(identifier or "").strip()[:500],
            authors=tuple(str(x).strip()[:300] for x in authors if str(x).strip()),
            publication_date=str(publication_date or "").strip()[:100],
            language=str(language or "").strip().lower()[:80],
            license_id=str(license_id or "").strip()[:200],
            rights=rights,
            checksum=str(checksum or "").strip().lower()[:200],
            retrieved_at=time.time(),
            peer_reviewed=peer_reviewed,
            retracted=retracted,
            primary=bool(primary),
            rishi_owner=rishi_owner,
            knowledge_track=str(knowledge_track or "general").strip().lower()[:100],
            local_path=str(local_path or "").strip()[:2000],
            notes=str(notes or "").strip()[:2000],
        )
        return row.public()

    def ingestion_gate(self, record: dict, requested_mode: AccessMode | str) -> dict:
        sid = str(record.get("source_id") or "").strip().lower()
        source = SOURCE_BY_ID.get(sid)
        if not source:
            raise KeyError(sid)
        mode = _mode(requested_mode)
        decision = self.rights_decision(
            mode,
            license_id=str(record.get("license_id") or ""),
            source_default_max_mode=source.default_max_mode,
        )
        problems = []
        if record.get("retracted") and mode >= AccessMode.ARCHIVE:
            problems.append("retracted source may be archived only as explicitly labelled contradiction/history evidence")
        if mode >= AccessMode.ARCHIVE and source.per_item_rights_required and not record.get("license_id"):
            problems.append("item licence/rights statement is required before archival")
        if mode == AccessMode.TRAIN and not record.get("checksum"):
            problems.append("training candidates require an immutable content checksum")
        allowed = decision.allowed and not problems
        return {
            "allowed": allowed,
            "requested_mode": MODE_NAME[mode],
            "source_id": sid,
            "rights": decision.public(),
            "problems": problems,
            "next_action": "execute through Shared Action Bus" if allowed else "collect licence/provenance or keep as read-only evidence",
        }
