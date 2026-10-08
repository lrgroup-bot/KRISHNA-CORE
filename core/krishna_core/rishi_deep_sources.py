from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable
from urllib.parse import urlencode


@dataclass(frozen=True)
class DeepSource:
    id: str
    name: str
    family: str
    kinds: tuple[str, ...]
    priority: str
    adapter: str
    base_url: str
    docs_url: str
    machine_access: bool
    auth: str
    default_max_mode: str
    per_item_rights_required: bool
    bulk_policy: str
    rishis: tuple[str, ...]
    domains: tuple[str, ...]
    evidence_role: str
    notes: str = ""

    def public(self) -> dict:
        row=asdict(self)
        row["kinds"]=list(self.kinds)
        row["rishis"]=list(self.rishis)
        row["domains"]=list(self.domains)
        row["free_core"]=True
        return row


def _source(id,name,family,kinds,priority,adapter,base_url,docs_url,*,machine_access=True,
            auth="none",default_max_mode="index",per_item_rights_required=True,
            bulk_policy="bounded",rishis=(),domains=(),evidence_role="discovery",notes=""):
    return DeepSource(
        id,name,family,tuple(kinds),priority,adapter,base_url,docs_url,bool(machine_access),auth,
        default_max_mode,bool(per_item_rights_required),bulk_policy,tuple(rishis),tuple(domains),
        evidence_role,notes,
    )


DEEP_SOURCES: tuple[DeepSource,...]=(
    _source(
        "datacite","DataCite","research-object-doi",
        ("dataset","software","paper","doi","metadata"),"P0","rest-json",
        "https://api.datacite.org/dois","https://support.datacite.org/docs/rest-api",
        auth="none-public-api",bulk_policy="public-api-oai-or-public-data-files",
        rishis=("veda-vyasa","gautama","bharadvaja","vishwamitra","kashyapa","atri"),
        domains=("datasets","software","doi","research objects","metadata","provenance"),
        evidence_role="research-object-metadata",
        notes="Public metadata retrieval/search needs no authentication; scripts should identify themselves with a User-Agent/contact.",
    ),
    _source(
        "openaire","OpenAIRE Graph","open-science-graph",
        ("paper","dataset","software","project","organization","funding","metadata"),"P0","rest-json-v3",
        "https://api.openaire.eu/graph/v3/research-products","https://graph.openaire.eu/docs/apis/graph-api/overview/",
        auth="none-public-api",bulk_policy="public-api-or-open-graph-dump",
        rishis=("veda-vyasa","gautama","bharadvaja","vishwamitra"),
        domains=("open science","papers","datasets","software","projects","funding","research graph"),
        evidence_role="linked-research-graph",
        notes="Links research products to projects, organisations, funders and trusted data sources; use V3 for new integrations.",
    ),
    _source(
        "zenodo","Zenodo","research-repository",
        ("paper","dataset","software","presentation","report","file","metadata"),"P1","rest-json",
        "https://zenodo.org/api/records","https://developers.zenodo.org/",
        auth="none-for-published-search",bulk_policy="api-bounded",
        rishis=("bharadvaja","vishwamitra","gautama","veda-vyasa"),
        domains=("research outputs","datasets","software","files","open science"),
        evidence_role="research-artifact-resolver",
        notes="Published-record search and file retrieval are useful; each record/file licence must be preserved before archive/reuse.",
    ),
    _source(
        "ncbi-bookshelf","NCBI Bookshelf","biomedical-books",
        ("book","chapter","guideline","report","full-text","metadata"),"P0","oai-pmh-and-ftp",
        "https://www.ncbi.nlm.nih.gov/books/NBK554843/","https://www.ncbi.nlm.nih.gov/books/about/",
        auth="none",default_max_mode="index",bulk_policy="official-oai-or-open-access-ftp-only",
        rishis=("sushruta","charaka","kashyapa","bharadvaja","gautama"),
        domains=("medicine","biology","health","guidelines","books","methods"),
        evidence_role="biomedical-book-source",
        notes="Bookshelf mixes OA and copyrighted books. No systematic crawling; use NLM OAI/FTP only for eligible OA content.",
    ),
    _source(
        "standard-ebooks","Standard Ebooks","public-domain-books",
        ("book","ebook","xhtml","epub"),"P1","browser-download",
        "https://standardebooks.org/ebooks","https://standardebooks.org/about",
        machine_access=False,auth="none",default_max_mode="read",bulk_policy="item-downloads-and-published-project-files",
        rishis=("veda-vyasa","agastya","panini","bharadvaja"),
        domains=("books","literature","public domain","epub","xhtml"),
        evidence_role="curated-public-domain-book",
        notes="Standard Ebooks dedicates its own work to CC0 and believes source text/art to be US public domain; jurisdiction still matters outside the US.",
    ),
    _source(
        "openstax","OpenStax","open-textbooks",
        ("textbook","book","course-reading"),"P1","browser-book",
        "https://openstax.org/subjects","https://help.openstax.org/s/article/Licensing-information-of-OpenStax-textbooks",
        machine_access=False,auth="none",default_max_mode="read",bulk_policy="noncommercial-educational-use-only",
        rishis=("bharadvaja","kanada","kashyapa","sushruta","vishwamitra"),
        domains=("textbooks","science","mathematics","medicine","engineering","education"),
        evidence_role="curriculum-textbook",
        notes="Current OpenStax books are CC BY-NC-SA. LR commercial-context archive/training must remain blocked unless separate permission exists.",
    ),
    _source(
        "nasa-ntrs","NASA Technical Reports Server","aerospace-technical",
        ("technical-report","paper","patent","presentation","image","video","metadata"),"P0","browser-repository",
        "https://ntrs.nasa.gov/search","https://ntrs.nasa.gov/",
        machine_access=False,auth="none-for-public",default_max_mode="read",bulk_policy="public-search-no-unverified-harvest",
        rishis=("atri","vishwamitra","kanada","bharadvaja","gautama"),
        domains=("aerospace","space","earth science","engineering","patents","technical reports"),
        evidence_role="government-technical-repository",
        notes="Public NTRS exposes NASA-created/funded STI; individual distribution/copyright statements must be preserved. Registered NTRS content is not public.",
    ),
    _source(
        "nasa-ads","NASA ADS / SciX","astronomy-bibliography",
        ("paper","citation","dataset","bibliography","metrics"),"P1","rest-json-token",
        "https://api.adsabs.harvard.edu/v1/search/query","https://ui.adsabs.harvard.edu/help/api/",
        auth="free-api-token",default_max_mode="index",bulk_policy="token-rate-limits-no-circumvention",
        rishis=("atri","gautama","bharadvaja","veda-vyasa"),
        domains=("astronomy","astrophysics","planetary science","heliophysics","citations","datasets"),
        evidence_role="astronomy-discovery",
        notes="ADS API supports search/metrics/export. Current service is preparing transition to SciX on 2026-11-16; endpoint/status must be reverified after migration.",
    ),
    _source(
        "etsi","ETSI Standards","telecom-standards",
        ("standard","technical-specification","guide","report"),"P0","browser-standard-index",
        "https://www.etsi.org/standards/","https://www.etsi.org/standards/what-are-standards",
        machine_access=False,auth="none",default_max_mode="read",bulk_policy="free-individual-downloads-no-redistribution",
        rishis=("vishwamitra","jamadagni","bharadvaja","vishvakarma"),
        domains=("telecom","wireless","cybersecurity","iot","ai","interoperability"),
        evidence_role="normative-standard",
        notes="ETSI provides standards downloads free of charge, but website/standards copyright restricts reproduction and redistribution. Treat as read-only unless separately licensed.",
    ),
    _source(
        "3gpp","3GPP Specifications","mobile-standards",
        ("technical-specification","technical-report","standard","change-request"),"P0","public-ftp-and-portal",
        "https://www.3gpp.org/FTP/Specs","https://portal.3gpp.org/",
        machine_access=True,auth="none-for-public-specs",default_max_mode="read",bulk_policy="public-ftp-bounded-rights-reviewed",
        rishis=("vishwamitra","jamadagni","bharadvaja","vishvakarma"),
        domains=("5g","6g","mobile","radio","core network","telecom","security"),
        evidence_role="normative-telecom-specification",
        notes="Public FTP/portal exposes current and archived specification releases. Content rights are not assumed to permit redistribution/training.",
    ),
    _source(
        "khronos","Khronos Registries","graphics-compute-standards",
        ("standard","api-registry","xml","headers","conformance"),"P0","registry-and-github",
        "https://registry.khronos.org/","https://registry.khronos.org/vulkan/specs/latest/registry.html",
        auth="none",default_max_mode="read",bulk_policy="official-registry-and-public-source-repositories",
        rishis=("vishvakarma","vishwamitra","bharadvaja","jamadagni"),
        domains=("vulkan","opengl","openxr","spir-v","graphics","compute","api","gpu"),
        evidence_role="normative-api-standard",
        notes="Canonical API registries are machine-readable XML. Published specifications use Khronos-specific terms; spec source files are generally CC BY 4.0 and code-like tools commonly Apache-2.0, so preserve per-file licence.",
    ),
    _source(
        "whatwg","WHATWG Living Standards","web-living-standards",
        ("standard","living-standard","web-platform","source"),"P0","web-and-github",
        "https://html.spec.whatwg.org/","https://whatwg.org/ipr-policy",
        auth="none",default_max_mode="index",bulk_policy="living-standard-source-and-web",
        rishis=("vishvakarma","vishwamitra","jamadagni","bharadvaja"),
        domains=("html","dom","fetch","url","web","browser","web platform"),
        evidence_role="normative-living-standard",
        notes="Use current Living Standards and preserve WHATWG IPR/source licensing terms rather than copying stale snapshots from third parties.",
    ),
)

DEEP_BY_ID={x.id:x for x in DEEP_SOURCES}


class RishiDeepSourceExpansion:
    VERSION="rishi-deep-sources-v1"

    def source(self,source_id):
        row=DEEP_BY_ID.get(str(source_id or "").strip().lower())
        if not row:raise KeyError(source_id)
        return row.public()

    def list_sources(self):
        return [x.public() for x in DEEP_SOURCES]

    def status(self):
        return {
            "version":self.VERSION,
            "source_count":len(DEEP_SOURCES),
            "machine_access_sources":len([x for x in DEEP_SOURCES if x.machine_access]),
            "policy":"supplemental datasets/books/aerospace/standards sources; conservative rights ceilings remain in force",
        }

    def research_plan(self,topic,rishi_id=None,kinds:Iterable[str]=(),max_sources=10):
        text=str(topic or "").strip().lower()
        if not text:raise ValueError("topic is required")
        tokens={x for x in text.replace("/"," ").replace("-"," ").split() if len(x)>2}
        wanted={str(x).strip().lower() for x in kinds if str(x).strip()}
        scored=[]
        for source in DEEP_SOURCES:
            score=40 if source.priority=="P0" else (25 if source.priority=="P1" else 10)
            if source.machine_access:score+=5
            if rishi_id and str(rishi_id).strip().lower() in source.rishis:score+=35
            for term in set(source.domains)|set(source.kinds):
                t=term.lower()
                if t in text or any(token in t for token in tokens):score+=9
            if wanted and wanted & set(source.kinds):score+=20
            if score>0:scored.append((score,source))
        scored.sort(key=lambda row:(-row[0],row[1].priority,row[1].name.lower()))
        return [source.public()|{"score":score} for score,source in scored[:max(1,min(int(max_sources),25))]]

    def request_plan(self,source_id,query,*,api_key_ref="",email=""):
        source=DEEP_BY_ID.get(str(source_id or "").strip().lower())
        if not source:raise KeyError(source_id)
        q=str(query or "").strip()
        if not q:raise ValueError("query is required")
        url=source.base_url
        requires_browser=not source.machine_access
        secret_required=source.auth in {"free-api-token"}
        sid=source.id
        if sid=="datacite":
            url=f"{source.base_url}?{urlencode({'query':q,'page[size]':25})}"
        elif sid=="openaire":
            url=f"{source.base_url}?{urlencode({'search':q,'pageSize':25})}"
        elif sid=="zenodo":
            url=f"{source.base_url}?{urlencode({'q':q,'size':25})}"
        elif sid=="nasa-ads":
            url=f"{source.base_url}?{urlencode({'q':q,'fl':'bibcode,title,author,year,doi,citation_count','rows':25})}"
        return {
            "source_id":sid,"adapter":source.adapter,"url":url,
            "requires_browser":requires_browser,"auth":source.auth,
            "secret_required":secret_required,"api_key_ref":str(api_key_ref or ""),
            "contact":str(email or ""),"bulk_policy":source.bulk_policy,
            "source_default_max_mode":source.default_max_mode,
            "per_item_rights_required":source.per_item_rights_required,
            "zero_spend_rule":"do not purchase subscriptions, standards, API quota or paid access automatically",
        }
