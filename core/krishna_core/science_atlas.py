from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from threading import RLock


OPENALEX_COUNTS = {
    "domains": 4,
    "fields": 26,
    "subfields": 252,
    "topics": 4516,
}

FIELD_RISHI_MAP = {
    "agricultural and biological sciences": ("kashyapa","kanada","bharadvaja","gautama","veda-vyasa"),
    "arts and humanities": ("veda-vyasa","agastya","yajnavalkya","panini","gautama"),
    "biochemistry, genetics and molecular biology": ("kashyapa","sushruta","kanada","gautama","veda-vyasa"),
    "business, management and accounting": ("vashistha","bharadvaja","gautama","veda-vyasa"),
    "chemical engineering": ("kanada","vishwamitra","bharadvaja","jamadagni","gautama"),
    "chemistry": ("kanada","bharadvaja","gautama","veda-vyasa"),
    "computer science": ("vishwamitra","bharadvaja","jamadagni","panini","gautama","veda-vyasa"),
    "decision sciences": ("gautama","vashistha","bharadvaja","veda-vyasa"),
    "dentistry": ("sushruta","charaka","gautama","veda-vyasa"),
    "earth and planetary sciences": ("atri","kanada","kashyapa","gautama","veda-vyasa"),
    "economics, econometrics and finance": ("vashistha","gautama","bharadvaja","veda-vyasa"),
    "energy": ("vishwamitra","kanada","jamadagni","bharadvaja","gautama"),
    "engineering": ("bharadvaja","vishwamitra","kanada","jamadagni","gautama","veda-vyasa"),
    "environmental science": ("kashyapa","agastya","kanada","atri","gautama"),
    "health professions": ("sushruta","charaka","vashistha","gautama","veda-vyasa"),
    "immunology and microbiology": ("kashyapa","sushruta","charaka","gautama","veda-vyasa"),
    "materials science": ("kanada","vishwamitra","bharadvaja","gautama","veda-vyasa"),
    "mathematics": ("gautama","bharadvaja","kanada","veda-vyasa"),
    "medicine": ("sushruta","charaka","gautama","vashistha","veda-vyasa"),
    "neuroscience": ("kapila","sushruta","patanjali","gautama","veda-vyasa"),
    "nursing": ("sushruta","charaka","vashistha","gautama","veda-vyasa"),
    "pharmacology, toxicology and pharmaceutics": ("charaka","sushruta","kanada","gautama","veda-vyasa"),
    "physics and astronomy": ("kanada","atri","vishwamitra","bharadvaja","gautama","veda-vyasa"),
    "psychology": ("kapila","patanjali","gautama","yajnavalkya","veda-vyasa"),
    "social sciences": ("vashistha","agastya","yajnavalkya","gautama","veda-vyasa"),
    "veterinary": ("kashyapa","sushruta","charaka","gautama","veda-vyasa"),
}

KEYWORD_TEAMS = (
    (("dna","genome","genomic","genetics","gene editing","epigenetic","chromatin","telomere"),
     ("kashyapa","sushruta","kanada","gautama","bharadvaja","veda-vyasa")),
    (("cancer","oncology","tumor","tumour","metastasis"),
     ("sushruta","charaka","kashyapa","gautama","bharadvaja","veda-vyasa")),
    (("aging","ageing","longevity","senescence","geroscience","rejuvenation"),
     ("sushruta","charaka","kashyapa","kapila","gautama","veda-vyasa")),
    (("neural","brain","cognition","bci","brain-computer","neuroprosthetic"),
     ("kapila","sushruta","patanjali","bharadvaja","gautama","veda-vyasa")),
    (("artificial intelligence","machine learning","deep learning","robotics","computer vision"),
     ("vishwamitra","bharadvaja","jamadagni","gautama","veda-vyasa")),
    (("cybersecurity","malware","software security","cryptography","resilience"),
     ("jamadagni","vishwamitra","gautama","bharadvaja","veda-vyasa")),
    (("quantum","particle","nuclear","relativity","cosmology"),
     ("kanada","atri","vishwamitra","gautama","bharadvaja","veda-vyasa")),
    (("climate","ecology","biodiversity","environment","conservation"),
     ("kashyapa","agastya","atri","kanada","gautama","veda-vyasa")),
    (("language","linguistics","grammar","translation","nlp"),
     ("panini","agastya","gautama","veda-vyasa")),
    (("consciousness","philosophy of mind","self","metaphysics"),
     ("kapila","yajnavalkya","patanjali","gautama","veda-vyasa")),
)

SENSITIVE_BIO_TERMS = (
    "dna","genome","genomic","gene editing","genetic engineering","crispr","synthetic biology",
    "pathogen","virus","viral","bacteria","microbe","toxin","virulence","oncogene","cancer",
    "stem cell","embryo","germline","reprogramming","gain of function",
)

BIOSECURITY_TERMS = (
    "pathogen","virulence","gain of function","toxin","weapon","bioweapon",
    "pandemic strain","immune evasion","antimicrobial resistance engineering",
)


class ScienceAtlas:
    """Dynamic research taxonomy and Rishi routing for BRAHMAGYAN.

    OpenAlex is used as an optional CC0 taxonomy source. Taxonomy rows are data,
    never authority. Scientific conclusions still require the BRAHMAGYAN evidence
    pipeline and Gautama/Vyasa gates.
    """

    VERSION = "science-atlas-v1"
    OPENALEX = "https://api.openalex.org"

    def __init__(self,state_root,council,memory=None):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"science-atlas.json"
        self.council=council
        self.memory=memory
        self.lock=RLock()
        self.state={
            "version":self.VERSION,
            "taxonomy":{"domains":[],"fields":[],"subfields":[],"topics":[]},
            "research":{},
            "last_sync_at":None,
            "sync_source":"OpenAlex CC0",
        }
        self._load()

    def _load(self):
        if not self.path.is_file():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw,dict):
                self.state.update(raw)
                self.state.setdefault("taxonomy",{"domains":[],"fields":[],"subfields":[],"topics":[]})
                self.state.setdefault("research",{})
        except Exception as exc:
            if self.memory:self.memory.audit("science_atlas","load_failed",f"{type(exc).__name__}: {exc}")

    def _save(self):
        tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state,ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,self.path)

    @staticmethod
    def _json_get(url):
        req=urllib.request.Request(url,headers={
            "User-Agent":"KRISHNA-ScienceAtlas/1.0",
            "Accept":"application/json",
        })
        with urllib.request.urlopen(req,timeout=45) as r:
            return json.loads(r.read().decode("utf-8"))

    def _list_endpoint(self,name,select=None,max_rows=None):
        rows=[]
        cursor="*"
        while cursor:
            query={"per_page":"100","cursor":cursor}
            if select:query["select"]=select
            url=f"{self.OPENALEX}/{name}?"+urllib.parse.urlencode(query)
            data=self._json_get(url)
            batch=data.get("results") or []
            rows.extend(batch)
            if max_rows and len(rows)>=int(max_rows):
                rows=rows[:int(max_rows)]
                break
            cursor=(data.get("meta") or {}).get("next_cursor")
            if not batch:break
        return rows

    @staticmethod
    def _compact(row,kind):
        out={
            "id":str(row.get("id") or ""),
            "display_name":str(row.get("display_name") or ""),
            "description":str(row.get("description") or ""),
            "works_count":int(row.get("works_count") or 0),
            "cited_by_count":int(row.get("cited_by_count") or 0),
            "updated_date":row.get("updated_date"),
            "kind":kind,
        }
        for key in ("domain","field","subfield"):
            ref=row.get(key)
            if isinstance(ref,dict):
                out[key]={"id":str(ref.get("id") or ""),"display_name":str(ref.get("display_name") or "")}
        if kind=="topic":
            out["keywords"]=[str(x) for x in (row.get("keywords") or []) if str(x).strip()][:20]
        return out

    def sync_openalex(self,include_topics=True,topic_limit=None):
        taxonomy={}
        taxonomy["domains"]=[
            self._compact(x,"domain")
            for x in self._list_endpoint("domains","id,display_name,description,works_count,cited_by_count,updated_date")
        ]
        taxonomy["fields"]=[
            self._compact(x,"field")
            for x in self._list_endpoint("fields","id,display_name,description,domain,works_count,cited_by_count,updated_date")
        ]
        taxonomy["subfields"]=[
            self._compact(x,"subfield")
            for x in self._list_endpoint("subfields","id,display_name,description,domain,field,works_count,cited_by_count,updated_date")
        ]
        if include_topics:
            taxonomy["topics"]=[
                self._compact(x,"topic")
                for x in self._list_endpoint(
                    "topics",
                    "id,display_name,description,keywords,domain,field,subfield,works_count,cited_by_count,updated_date",
                    max_rows=topic_limit,
                )
            ]
        else:
            taxonomy["topics"]=list(self.state.get("taxonomy",{}).get("topics") or [])
        with self.lock:
            self.state["taxonomy"]=taxonomy
            self.state["last_sync_at"]=time.time()
            self._save()
        if self.memory:
            self.memory.audit(
                "science_atlas","synced",
                f"domains={len(taxonomy['domains'])} fields={len(taxonomy['fields'])} "
                f"subfields={len(taxonomy['subfields'])} topics={len(taxonomy['topics'])}",
            )
        return self.status()

    @staticmethod
    def safety_mode(subject):
        text=str(subject or "").lower()
        if any(x in text for x in BIOSECURITY_TERMS):
            return {
                "mode":"biosecurity_high_level_only",
                "allowed":"mechanisms, epidemiology, detection, prevention, treatment, risk analysis, non-operational literature synthesis",
                "blocked":"procedural pathogen enhancement, virulence optimization, immune-evasion engineering, weaponization or operational wet-lab instructions",
            }
        if any(x in text for x in SENSITIVE_BIO_TERMS):
            return {
                "mode":"biomedical_conceptual_research",
                "allowed":"mechanisms, naturally occurring variation, disease associations, intervention hypotheses, preclinical/clinical evidence, failure modes, reversibility and safety",
                "blocked":"step-by-step wet-lab genome editing, experimental sequences, construct design, dosing/protocol optimization or human germline implementation instructions",
            }
        return {
            "mode":"standard_frontier_research",
            "allowed":"mechanisms, counterfactuals, experiments, simulations, failure analysis, cross-domain synthesis",
            "blocked":"unsafe operational instructions where a subject-specific safety policy applies",
        }

    def route(self,subject,field=None,domain=None,limit=6):
        text=" ".join(str(x or "") for x in (subject,field,domain)).lower()
        ids=[]
        for terms,team in KEYWORD_TEAMS:
            if any(t in text for t in terms):
                for rid in team:
                    if rid not in ids:ids.append(rid)
        fkey=str(field or "").strip().lower()
        for rid in FIELD_RISHI_MAP.get(fkey,()):
            if rid not in ids:ids.append(rid)
        try:
            medical=self.council.specialist_team(subject,limit=8)
            for member in medical.get("members") or []:
                rid=member["id"]
                if rid not in ids:ids.append(rid)
        except Exception:
            pass
        if not ids:
            ids=["bharadvaja","gautama","veda-vyasa"]
        if "gautama" not in ids:ids.append("gautama")
        if "veda-vyasa" not in ids:ids.append("veda-vyasa")
        ids=ids[:max(1,min(int(limit),8))]
        return {
            "subject":str(subject or ""),
            "field":field,
            "domain":domain,
            "rishis":[self.council.get(x) for x in ids],
            "safety":self.safety_mode(subject),
            "policy":"routing assigns modern KRISHNA research roles; it does not claim historical figures practiced these modern sciences",
        }

    def frontier_questions(self,subject,field=None,domain=None,limit=12):
        subject=str(subject or "").strip()
        if not subject:raise ValueError("subject is required")
        safety=self.safety_mode(subject)
        questions=[
            f"What are the strongest causal mechanisms currently proposed for {subject}, and which observations would falsify each mechanism?",
            f"Which naturally occurring variations, boundary conditions or perturbations of {subject} produce unexpectedly beneficial or harmful outcomes?",
            f"If one component of {subject} is increased, decreased, inhibited or restored, what downstream systems are predicted to change and what evidence supports that prediction?",
            f"Which effects attributed to {subject} are reversible, which appear persistent, and what determines the difference?",
            f"What are the most important negative results, failed replications and contradictory findings in {subject}?",
            f"Which measurements or biomarkers best distinguish correlation from causation in {subject}?",
            f"What hidden trade-offs or failure modes appear when an intervention in {subject} improves one outcome but worsens another?",
            f"Which adjacent scientific fields contain mechanisms or tools that could change how {subject} is understood?",
            f"What result in the last three years most strongly challenges the standard model of {subject}?",
            f"What is technically possible in {subject} today, what is only preclinical or simulated, and what remains speculative?",
            f"What safe experiment, simulation or observational test would most efficiently discriminate between competing explanations of {subject}?",
            f"What important question about {subject} has high potential impact but weak current evidence, and what evidence would be required to resolve it?",
        ]
        text=subject.lower()
        if any(x in text for x in ("dna","genome","genetic","epigenetic","aging","ageing","cancer","oncology")):
            questions=[
                f"Which molecular pathways connect {subject} to cell state, tissue function, aging or disease, and which links are causal rather than correlational?",
                f"Which naturally occurring human genetic or epigenetic variants related to {subject} are associated with healthier or harmful phenotypes?",
                f"Could a reversible regulatory intervention affecting {subject} reproduce a desired phenotype without permanent genome alteration?",
                f"What evidence separates cell-culture, animal-model and human effects for hypotheses involving {subject}?",
                f"Which mechanisms involving {subject} could reduce disease while simultaneously increasing cancer, genomic-instability or other long-term risks?",
                f"For aging-related hypotheses involving {subject}, which changes appear to reset molecular age markers and which have evidence for improved organism-level function?",
                f"For cancer-related hypotheses involving {subject}, which alterations affect tumor initiation, progression, immune surveillance, resistance or metastasis, and how context-dependent are they?",
                f"Which intervention points downstream of {subject} might achieve the desired effect with less irreversible risk?",
                f"What off-target, pleiotropic, mosaic, immune, developmental or tissue-specific consequences are reported for interventions involving {subject}?",
                f"What findings contradict the idea that changing {subject} alone would be sufficient to reverse aging or resolve cancer?",
                f"What non-invasive or computational evidence could test a hypothesis about {subject} before any experimental intervention is considered?",
                f"What clinical evidence would be required before a hypothesis involving {subject} could reasonably move from preclinical research toward human use?",
            ]
        return {
            "subject":subject,
            "field":field,
            "domain":domain,
            "questions":questions[:max(1,min(int(limit),20))],
            "team":self.route(subject,field,domain,limit=8),
            "safety":safety,
            "research_standard":"mechanism → counterfactual → evidence → contradiction → predicted outcome → failure modes → safe test → translation limits",
        }

    def research_program(self,subject,field=None,domain=None,question_limit=8):
        frontier=self.frontier_questions(subject,field,domain,question_limit)
        return {
            "subject":subject,
            "field":field,
            "domain":domain,
            "team":frontier["team"],
            "safety":frontier["safety"],
            "questions":frontier["questions"],
            "phases":[
                "map current consensus and unresolved mechanisms",
                "collect primary and recent evidence",
                "generate bounded counterfactual hypotheses",
                "search contradictory and negative evidence",
                "compare natural variation with intervention evidence",
                "identify reversibility, trade-offs and failure modes",
                "design safe discriminating tests or simulations",
                "separate preclinical, clinical and speculative conclusions",
                "Gautama evidence audit",
                "Veda Vyasa synthesis and Gyan-Bhandar proposal",
            ],
        }

    def seed_curiosity(self,brahmagyan,subject,field=None,domain=None,project="KRISHNA",limit=8):
        program=self.research_program(subject,field,domain,limit)
        rows=[]
        for i,q in enumerate(program["questions"]):
            rows.append(brahmagyan.add_curiosity(project,q,{
                "knowledge_gap":1.0,
                "importance":max(.65,1.0-(i*.04)),
                "cross_domain":.8,
                "discovery":.9,
                "freshness":.8,
                "source_availability":.8,
                "resource_cost":.35,
                "science_atlas":1.0,
            }))
        return {"program":program,"queued":rows}

    def _node_key(self,row):
        return str(row.get("id") or row.get("display_name") or "")

    def next_subject(self,kind="topic"):
        with self.lock:
            rows=list(self.state.get("taxonomy",{}).get(kind+"s") or [])
            research=dict(self.state.get("research") or {})
        if not rows:return None
        def score(row):
            key=self._node_key(row)
            meta=research.get(key) or {}
            count=int(meta.get("research_count") or 0)
            last=float(meta.get("last_researched_at") or 0)
            impact=max(0,int(row.get("works_count") or 0))
            return (count,last,-impact,str(row.get("display_name") or ""))
        row=sorted(rows,key=score)[0]
        field=(row.get("field") or {}).get("display_name") if isinstance(row.get("field"),dict) else None
        domain=(row.get("domain") or {}).get("display_name") if isinstance(row.get("domain"),dict) else None
        return {
            "id":self._node_key(row),
            "kind":kind,
            "subject":row.get("display_name"),
            "description":row.get("description"),
            "field":field,
            "domain":domain,
            "works_count":row.get("works_count",0),
            "research":research.get(self._node_key(row)) or {},
        }

    def record_research(self,node_id,mission_id,run_id=None,maturity=None,unresolved=0):
        key=str(node_id or "").strip()
        if not key:raise ValueError("node_id is required")
        with self.lock:
            row=dict(self.state.setdefault("research",{}).get(key) or {})
            row["research_count"]=int(row.get("research_count") or 0)+1
            row["last_researched_at"]=time.time()
            row.setdefault("mission_ids",[]).append(str(mission_id))
            row["mission_ids"]=row["mission_ids"][-50:]
            if run_id:
                row.setdefault("run_ids",[]).append(str(run_id))
                row["run_ids"]=row["run_ids"][-50:]
            if maturity:row["last_maturity"]=str(maturity)
            row["last_unresolved"]=int(unresolved or 0)
            self.state["research"][key]=row
            self._save()
            return dict(row)

    def search(self,query,kind=None,limit=50):
        q=str(query or "").strip().lower()
        if not q:return []
        kinds=[kind] if kind else ["domains","fields","subfields","topics"]
        out=[]
        with self.lock:
            taxonomy=self.state.get("taxonomy") or {}
        for name in kinds:
            rows=taxonomy.get(name) or []
            for row in rows:
                hay=" ".join([
                    str(row.get("display_name") or ""),
                    str(row.get("description") or ""),
                    " ".join(row.get("keywords") or []),
                ]).lower()
                if q in hay:
                    out.append(dict(row))
                    if len(out)>=int(limit):return out
        return out

    def status(self):
        with self.lock:
            tax=self.state.get("taxonomy") or {}
            researched=self.state.get("research") or {}
            last_sync=self.state.get("last_sync_at")
        return {
            "name":"BRAHMAGYAN Science Atlas",
            "version":self.VERSION,
            "source":"OpenAlex CC0 taxonomy + KRISHNA Rishi routing",
            "reference_counts":dict(OPENALEX_COUNTS),
            "loaded_counts":{k:len(tax.get(k) or []) for k in ("domains","fields","subfields","topics")},
            "researched_subjects":len(researched),
            "last_sync_at":last_sync,
            "frontier_policy":"research mechanism and counterfactuals, not just definitions; preserve evidence limits and safety boundaries",
        }


class ScienceFrontierScheduler:
    """Resource-aware scheduler for one bounded frontier mission at a time."""

    def __init__(self,tick,interval_seconds=1800):
        self.tick=tick
        self.interval_seconds=max(300,int(interval_seconds))
        self._stop=threading.Event()
        self._thread=None
        self.run_count=0
        self.last_result=None
        self.last_error=None

    def start(self):
        if self._thread and self._thread.is_alive():return self.status()
        self._stop.clear()
        self._thread=threading.Thread(target=self._loop,name="rishi-science-frontier",daemon=True)
        self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=2)
        return self.status()

    def _loop(self):
        while not self._stop.wait(self.interval_seconds):
            try:
                self.last_result=self.tick()
                self.run_count+=1
                self.last_error=None
            except Exception as exc:
                self.last_error=f"{type(exc).__name__}: {exc}"

    def status(self):
        return {
            "running":bool(self._thread and self._thread.is_alive()),
            "interval_seconds":self.interval_seconds,
            "run_count":self.run_count,
            "last_result":self.last_result,
            "last_error":self.last_error,
        }
