from __future__ import annotations
import re, urllib.parse, urllib.request, xml.etree.ElementTree as ET, json, time, hashlib
from threading import RLock
from dataclasses import dataclass, asdict
from .content_guard import assess_untrusted_content

@dataclass
class WebCandidate:
    title:str
    url:str
    summary:str
    source:str
    relevance:int
    suspicious:bool=False
    fingerprint:str=""

class GarudaAgent:
    """Garuda research scout. It gathers evidence; KRISHNA remains the decision authority."""
    def __init__(self, github, memory):
        self.github=github; self.memory=memory
        self._lock=RLock(); self._state={"working":False,"phase":"READY","source":None,"goal":None,"project":None,"started_at":None,"updated_at":time.time(),"found":0,"last_error":None}

    def _set(self, **values):
        with self._lock:
            self._state.update(values); self._state["updated_at"]=time.time()

    def status(self):
        with self._lock:return dict(self._state)

    @staticmethod
    def _json_get(url):
        req=urllib.request.Request(url,headers={"User-Agent":"KRISHNA-Garuda/1.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode("utf-8"))

    def _arxiv(self, query, limit=10):
        url="https://export.arxiv.org/api/query?search_query=all:"+urllib.parse.quote(query)+"&start=0&max_results="+str(max(1,min(int(limit),20)))
        req=urllib.request.Request(url,headers={"User-Agent":"KRISHNA-Garuda/1.0"})
        with urllib.request.urlopen(req,timeout=20) as r:root=ET.fromstring(r.read())
        ns={"a":"http://www.w3.org/2005/Atom"}; out=[]; wanted=self._terms(query)
        for e in root.findall("a:entry",ns):
            title=" ".join((e.findtext("a:title",default="",namespaces=ns)).split()); summary=" ".join((e.findtext("a:summary",default="",namespaces=ns)).split())
            link=e.findtext("a:id",default="",namespaces=ns); guard=assess_untrusted_content(title+"\n"+summary,link).as_dict()
            out.append(WebCandidate(title[:240],link[:1500],summary[:1000],"arxiv",len(wanted & self._terms(title+" "+summary)),bool(guard["suspicious"])))
        return out

    def _npm(self, query, limit=10):
        data=self._json_get("https://registry.npmjs.org/-/v1/search?size="+str(max(1,min(int(limit),20)))+"&text="+urllib.parse.quote(query)); out=[]; wanted=self._terms(query)
        for row in data.get("objects",[]):
            p=row.get("package") or {}; title=p.get("name") or ""; summary=p.get("description") or ""; link=(p.get("links") or {}).get("repository") or (p.get("links") or {}).get("npm") or ""
            guard=assess_untrusted_content(title+"\n"+summary,link).as_dict(); out.append(WebCandidate(title[:240],link[:1500],summary[:1000],"npm",len(wanted & self._terms(title+" "+summary)),bool(guard["suspicious"])))
        return out

    def _hn(self, query, limit=10):
        data=self._json_get("https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage="+str(max(1,min(int(limit),20)))+"&query="+urllib.parse.quote(query)); out=[]; wanted=self._terms(query)
        for row in data.get("hits",[]):
            title=row.get("title") or ""; link=row.get("url") or ("https://news.ycombinator.com/item?id="+str(row.get("objectID") or "")); summary=title
            guard=assess_untrusted_content(title,link).as_dict(); out.append(WebCandidate(title[:240],link[:1500],summary[:1000],"hackernews",len(wanted & self._terms(title)),bool(guard["suspicious"])))
        return out

    def _openalex(self, query, limit=10):
        params=urllib.parse.urlencode({
            "search":str(query),
            "per_page":str(max(1,min(int(limit),20))),
            "sort":"publication_date:desc",
            "select":"id,display_name,doi,publication_year,type,primary_topic,cited_by_count",
        })
        data=self._json_get("https://api.openalex.org/works?"+params)
        wanted=self._terms(query);out=[]
        for row in data.get("results",[]):
            title=str(row.get("display_name") or "")
            topic=((row.get("primary_topic") or {}).get("display_name") or "")
            summary=f"{row.get('type') or 'work'}; year={row.get('publication_year')}; primary_topic={topic}; citations={row.get('cited_by_count') or 0}"
            link=str(row.get("doi") or row.get("id") or "")
            guard=assess_untrusted_content(title+"\n"+summary,link).as_dict()
            out.append(WebCandidate(title[:240],link[:1500],summary[:1000],"openalex",
                                    len(wanted & self._terms(title+" "+topic)),bool(guard["suspicious"])))
        return out

    def _crossref(self, query, limit=10):
        params=urllib.parse.urlencode({
            "query.bibliographic":str(query),
            "rows":str(max(1,min(int(limit),20))),
            "sort":"published",
            "order":"desc",
            "select":"DOI,title,abstract,publisher,type,URL,published-print,published-online",
        })
        data=self._json_get("https://api.crossref.org/works?"+params)
        wanted=self._terms(query);out=[]
        for row in ((data.get("message") or {}).get("items") or []):
            titles=row.get("title") or [];title=str(titles[0] if titles else "")
            abstract=re.sub(r"<[^>]+>"," ",str(row.get("abstract") or ""))
            abstract=" ".join(abstract.split())
            summary=(abstract or f"{row.get('type') or 'work'}; publisher={row.get('publisher') or ''}")[:1000]
            doi=str(row.get("DOI") or "")
            link=str(row.get("URL") or ("https://doi.org/"+doi if doi else ""))
            guard=assess_untrusted_content(title+"\n"+summary,link).as_dict()
            out.append(WebCandidate(title[:240],link[:1500],summary,"crossref",
                                    len(wanted & self._terms(title+" "+summary)),bool(guard["suspicious"])))
        return out

    def _europe_pmc(self, query, limit=10):
        params=urllib.parse.urlencode({
            "query":str(query)+" sort_date:y",
            "format":"json",
            "pageSize":str(max(1,min(int(limit),20))),
            "resultType":"core",
        })
        data=self._json_get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"+params)
        wanted=self._terms(query);out=[]
        for row in ((data.get("resultList") or {}).get("result") or []):
            title=str(row.get("title") or "")
            abstract=" ".join(str(row.get("abstractText") or "").split())
            meta=f"{row.get('journalTitle') or ''}; year={row.get('pubYear') or ''}; authors={row.get('authorString') or ''}"
            summary=(abstract or meta)[:1000]
            pmid=str(row.get("pmid") or "");pmcid=str(row.get("pmcid") or "")
            doi=str(row.get("doi") or "")
            if pmid:link="https://europepmc.org/article/MED/"+pmid
            elif pmcid:link="https://europepmc.org/article/PMC/"+pmcid
            elif doi:link="https://doi.org/"+doi
            else:link=""
            guard=assess_untrusted_content(title+"\n"+summary,link).as_dict()
            out.append(WebCandidate(title[:240],link[:1500],summary,"europepmc",
                                    len(wanted & self._terms(title+" "+summary)),bool(guard["suspicious"])))
        return out

    def _clinical_trials(self, query, limit=10):
        params=urllib.parse.urlencode({
            "query.term":str(query),
            "pageSize":str(max(1,min(int(limit),20))),
            "format":"json",
        })
        data=self._json_get("https://clinicaltrials.gov/api/v2/studies?"+params)
        wanted=self._terms(query);out=[]
        for study in data.get("studies",[]):
            protocol=study.get("protocolSection") or {}
            ident=protocol.get("identificationModule") or {}
            desc=protocol.get("descriptionModule") or {}
            status=protocol.get("statusModule") or {}
            design=protocol.get("designModule") or {}
            nct=str(ident.get("nctId") or "")
            title=str(ident.get("briefTitle") or ident.get("officialTitle") or "")
            phases=design.get("phases") or []
            summary=" ".join(str(desc.get("briefSummary") or "").split())
            meta=f"status={status.get('overallStatus') or ''}; phases={','.join(str(x) for x in phases)}"
            evidence=(summary+" "+meta).strip()[:1000]
            link=("https://clinicaltrials.gov/study/"+nct) if nct else ""
            guard=assess_untrusted_content(title+"\n"+evidence,link).as_dict()
            out.append(WebCandidate(title[:240],link[:1500],evidence,"clinicaltrials",
                                    len(wanted & self._terms(title+" "+evidence)),bool(guard["suspicious"])))
        return out

    @staticmethod
    def _looks_biomedical(text):
        terms={
            "medicine","medical","clinical","health","disease","cancer","oncology","dna","genetic","genome",
            "aging","ageing","drug","therapy","treatment","patient","neural","brain","immunology","microbiology",
            "surgery","diagnostic","biomedical","pharmacology","cell","protein","rna",
        }
        return bool(GarudaAgent._terms(text) & terms)

    def science_scout(self, project, goal, limit=10):
        report=self.scout(project,goal,limit)
        candidates=[]
        for row in report.get("web") or []:
            candidates.append(WebCandidate(
                str(row.get("title") or ""),str(row.get("url") or ""),str(row.get("summary") or ""),
                str(row.get("source") or "web"),int(row.get("relevance") or 0),
                bool(row.get("suspicious",False)),str(row.get("fingerprint") or ""),
            ))
        errors=dict(report.get("errors") or {})
        sources=[("openalex",self._openalex),("crossref",self._crossref)]
        if self._looks_biomedical(goal):
            sources.extend([("europepmc",self._europe_pmc),("clinicaltrials",self._clinical_trials)])
        for name,fn in sources:
            self._set(working=True,phase="SCIENCE_SCOUTING",source=name)
            try:candidates.extend(fn(goal,limit))
            except Exception as exc:errors[name]=f"{type(exc).__name__}: {exc}"
        ranked=self._dedupe_and_rank(candidates)
        report["web"]=[asdict(x) for x in ranked]
        report["errors"]=errors
        report["coverage"]=list(dict.fromkeys(list(report.get("coverage") or [])+[name for name,_ in sources]))
        report["science_protocol"]={
            "scholarly_indexes":["OpenAlex","Crossref"]+
                (["Europe PMC","ClinicalTrials.gov"] if self._looks_biomedical(goal) else []),
            "source_independence_required":True,
            "negative_and_counter_evidence_required":True,
            "preprint_not_equivalent_to_peer_review":True,
            "clinical_trial_registration_not_equivalent_to_positive_result":True,
        }
        self.memory.remember(project,"garuda_science_research",goal,{"report":report})
        self.memory.audit("garuda_science_scout","completed",f"{project}:{len(report['web'])} scholarly candidates")
        self._set(working=False,phase="HANDED_TO_KRISHNA",source=None,found=len(report["web"])+len(report.get("github") or []))
        return report

    @staticmethod
    def _terms(text):
        return {x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}",str(text).lower()) if len(x)>2}

    def _web(self, query, limit=10):
        url="https://www.bing.com/search?format=rss&q="+urllib.parse.quote(query)
        req=urllib.request.Request(url,headers={"User-Agent":"KRISHNA-Garuda/1.0"})
        with urllib.request.urlopen(req,timeout=20) as r:
            root=ET.fromstring(r.read())
        wanted=self._terms(query); out=[]
        for item in root.findall(".//item")[:max(1,min(int(limit),20))]:
            title=item.findtext("title") or ""; link=item.findtext("link") or ""
            summary=item.findtext("description") or ""
            guard=assess_untrusted_content(title+"\n"+summary,link).as_dict()
            hay=self._terms(title+" "+summary)
            score=len(wanted & hay)
            out.append(WebCandidate(title[:240],link[:1500],summary[:1000],"web",score,bool(guard["suspicious"])))
        return out

    @staticmethod
    def _fingerprint(url, title=""):
        raw=(str(url).strip().lower()+"|"+str(title).strip().lower()).encode("utf-8","ignore")
        return hashlib.sha256(raw).hexdigest()[:16]

    @staticmethod
    def _source_weight(source):
        return {
            "clinicaltrials":7,"europepmc":7,"openalex":6,"crossref":6,
            "arxiv":5,"github":4,"npm":3,"web":2,"hackernews":1,
        }.get(source,1)

    def _dedupe_and_rank(self, rows):
        seen={}; ranked=[]
        for x in rows:
            fp=self._fingerprint(x.url,x.title); x.fingerprint=fp
            if fp in seen: continue
            seen[fp]=True
            ranked.append(x)
        ranked.sort(key=lambda x:(x.suspicious is False,x.relevance,self._source_weight(x.source)),reverse=True)
        return ranked

    def scout(self, project, goal, limit=10):
        goal=str(goal or "").strip()
        if not goal: raise ValueError("Garuda requires a research goal")
        self._set(working=True,phase="TAKEOFF",source=None,goal=goal,project=project,started_at=time.time(),found=0,last_error=None)
        errors={}; web=[]; repos=[]
        try:
            for source,fn in (("public_web",self._web),("research_papers",self._arxiv),("npm_registry",self._npm),("technical_discussions",self._hn)):
                self._set(phase="SCOUTING",source=source)
                try:web.extend(fn(goal,limit))
                except Exception as exc:errors[source]=f"{type(exc).__name__}: {exc}"
                self._set(found=len(web)+len(repos))
            self._set(phase="SCOUTING",source="github")
            try:repos=(self.github.search(goal,limit).get("candidates") or [])
            except Exception as exc:errors["github"]=f"{type(exc).__name__}: {exc}"
            self._set(found=len(web)+len(repos))
        except Exception as exc:
            self._set(last_error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            if errors:self._set(last_error="; ".join(f"{k}: {v}" for k,v in errors.items()))
            self._set(working=False,source=None)
        wanted=self._terms(goal)
        for r in repos:
            r["fit_terms"]=len(wanted & self._terms((r.get("full_name") or "")+" "+(r.get("description") or "")))
        repos.sort(key=lambda x:(x.get("fit_terms",0),x.get("score",0),x.get("stars",0)),reverse=True)
        web=self._dedupe_and_rank(web)
        report={
            "agent":"Garuda","role":"research_and_evidence","project":project,"goal":goal,
            "web":[asdict(x) for x in web],"github":repos,
            "errors":errors,
            "coverage":["public_web","github","research_papers","npm_registry","technical_discussions"],
            "research_protocol":{"planner":"goal terms + source adapters","parallelizable":True,"deduplication":"sha256 URL/title fingerprint","ranking":"relevance + source weight + suspicious-content penalty","provenance":True,"counter_evidence_required":True,"resume_ready":True},
            "darkweb_policy":{"enabled":False,"reason":"No unrestricted dark-web crawling. Optional Tor research must be explicitly allowlisted to legitimate technical/research sources; illicit markets, stolen data, credentials and harmful services are excluded."},
            "handover":{
                "to":"KRISHNA","decision_authority":"KRISHNA",
                "auto_implementation":False,
                "required_before_implementation":["source review","license review","security review","dependency review","shadow integration","tests","browser/backend verification"]
            }
        }
        self.memory.remember(project,"garuda_research",goal,{"report":report})
        self.memory.audit("garuda_scout","completed",f"{project}:{len(web)} discovery:{len(repos)} github")
        self._set(working=False,phase="HANDED_TO_KRISHNA",source=None,found=len(web)+len(repos))
        return report
