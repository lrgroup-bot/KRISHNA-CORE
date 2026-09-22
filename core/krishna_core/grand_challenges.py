from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import RLock


BUILTIN_GRAND_CHALLENGES={
    "amrita":{
        "name":"Project AMRITA","mission":"Healthy longevity and prevention of age-associated disease.",
        "subjects":("aging biology","senescence","epigenetic aging","DNA repair","proteostasis","mitochondria","stem cells","immune aging","geroscience","frailty"),
        "leads":("kashyapa","charaka","dhanvantari"),"support":("sushruta","gautama","bharadvaja","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "sanjeevani":{
        "name":"Project SANJEEVANI","mission":"Regenerative medicine, tissue repair and restoration of lost biological function.",
        "subjects":("regenerative medicine","tissue engineering","stem cells","wound healing","organ repair","biomaterials","biofabrication","rehabilitation"),
        "leads":("sushruta","kashyapa","dhanvantari"),"support":("kanada","bharadvaja","gautama","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "anuvansh":{
        "name":"Project ANUVANSH","mission":"Genomics, epigenetics, rare disease and gene-to-phenotype mechanisms.",
        "subjects":("genomics","genetics","epigenetics","DNA repair","gene regulation","rare disease","functional genomics","population genetics","multi-omics"),
        "leads":("kashyapa","gautama"),"support":("sushruta","dhanvantari","kanada","bharadvaja","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "karkata":{
        "name":"Project KARKATA","mission":"Cancer prevention, early detection, tumor biology, treatment response and resistance.",
        "subjects":("oncology","cancer genomics","tumor microenvironment","metastasis","immune oncology","early detection","drug resistance","radiation oncology"),
        "leads":("sushruta","dhanvantari","kashyapa"),"support":("charaka","gautama","bharadvaja","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "manas":{
        "name":"Project MANAS","mission":"Brain health, neuroscience, cognition, mental health and neural engineering.",
        "subjects":("neuroscience","brain disorders","mental health","cognition","neural engineering","brain-computer interfaces","neuroplasticity","neurodegeneration"),
        "leads":("kapila","sushruta","patanjali"),"support":("kashyapa","bharadvaja","gautama","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "jeevan":{
        "name":"Project JEEVAN","mission":"Prevent chronic disease through precision prevention and systems-level health research.",
        "subjects":("cardiovascular disease","diabetes","metabolic disease","obesity","kidney disease","liver disease","preventive medicine","public health"),
        "leads":("charaka","dhanvantari","sushruta"),"support":("gautama","chanakya","bharadvaja","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "aushadhi":{
        "name":"Project AUSHADHI","mission":"Drug discovery, target validation, repurposing, delivery and toxicology.",
        "subjects":("drug discovery","pharmacology","toxicology","drug repurposing","pharmacokinetics","pharmacodynamics","drug delivery","medicinal chemistry"),
        "leads":("dhanvantari","charaka","nagarjuna"),"support":("sushruta","kanada","gautama","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "raksha_bio":{
        "name":"Project RAKSHA-BIO","mission":"Defensive infectious-disease preparedness, diagnostics, surveillance and antimicrobial resistance research.",
        "subjects":("infectious disease","epidemiology","antimicrobial resistance","diagnostics","vaccines","outbreak preparedness","zoonoses","public health surveillance"),
        "leads":("kashyapa","shalihotra","charaka"),"support":("sushruta","jamadagni","gautama","veda-vyasa"),
        "safety":"biosecurity_high_level_only",
    },
    "drishti":{
        "name":"Project DRISHTI","mission":"Earlier and more accurate diagnosis through imaging, biosensors and multimodal clinical data.",
        "subjects":("medical imaging","bioimaging","biosensors","pathology imaging","radiomics","diagnostic AI","screening","medical signal processing"),
        "leads":("sushruta","madhava","kanada"),"support":("vishwamitra","gautama","bharadvaja","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "prana":{
        "name":"Project PRANA","mission":"Cardiorespiratory physiology, critical care, rehabilitation and human performance.",
        "subjects":("cardiology","pulmonology","critical care","respiratory physiology","circulation","rehabilitation","exercise physiology","wearables"),
        "leads":("charaka","sushruta","dhanvantari"),"support":("patanjali","madhava","gautama","veda-vyasa"),
        "safety":"biomedical_conceptual_research",
    },
    "vajra":{
        "name":"Project VAJRA","mission":"Semiconductors, photonics, quantum materials and next-generation electronics.",
        "subjects":("semiconductors","microelectronics","photonics","quantum materials","electronic materials","sensors","device physics","nanoelectronics"),
        "leads":("kanada","vishwamitra","nagarjuna"),"support":("aryabhata","madhava","bharadvaja","gautama"),
        "safety":"standard_frontier_research",
    },
    "agni":{
        "name":"Project AGNI","mission":"Clean, reliable and scalable energy systems.",
        "subjects":("batteries","hydrogen","solar energy","wind energy","nuclear energy","fusion","power electronics","grid storage","thermal systems"),
        "leads":("vishwamitra","kanada","nagarjuna"),"support":("bhaskaracharya","chanakya","jamadagni","gautama"),
        "safety":"standard_frontier_research",
    },
    "akash":{
        "name":"Project AKASH","mission":"Space science, exploration, orbital systems and planetary protection.",
        "subjects":("astronomy","astrophysics","spacecraft","orbital mechanics","planetary science","space weather","remote sensing","planetary defense"),
        "leads":("atri","aryabhata","vishwamitra"),"support":("bhaskaracharya","kanada","gautama","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "prithvi":{
        "name":"Project PRITHVI","mission":"Understand Earth materials, geology, resources and natural hazards.",
        "subjects":("geology","geophysics","mineral science","seismology","natural hazards","geochemistry","resource geology","earth observation"),
        "leads":("varahamihira","kanada","atri"),"support":("nagarjuna","agastya","gautama","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "varsha":{
        "name":"Project VARSHA","mission":"Climate, atmosphere, hydrology, extreme weather and water security.",
        "subjects":("climate science","meteorology","hydrology","extreme weather","floods","drought","air quality","water security"),
        "leads":("varahamihira","agastya","parashara"),"support":("atri","chanakya","gautama","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "sagara":{
        "name":"Project SAGARA","mission":"Ocean science, marine ecosystems, coastal risk and blue-economy knowledge.",
        "subjects":("oceanography","marine biology","coastal systems","marine ecology","fisheries","ocean climate","marine pollution","coastal hazards"),
        "leads":("agastya","kashyapa","varahamihira"),"support":("parashara","shalihotra","gautama","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "anna":{
        "name":"Project ANNA","mission":"Food security, soil health, climate-resilient crops and sustainable agriculture.",
        "subjects":("agronomy","soil science","crop science","plant disease","precision agriculture","irrigation","food systems","crop resilience"),
        "leads":("parashara","kashyapa"),"support":("shalihotra","varahamihira","vishwamitra","gautama","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "yantra":{
        "name":"Project YANTRA","mission":"Robotics, autonomy, manufacturing and human-machine collaboration.",
        "subjects":("robotics","autonomous systems","industrial automation","controls","mechatronics","human-robot interaction","manufacturing robotics","embodied AI"),
        "leads":("vishwamitra","bhaskaracharya","bharadvaja"),"support":("pingala","jamadagni","gautama","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "setu":{
        "name":"Project SETU","mission":"Safe, resilient and intelligent infrastructure and transport systems.",
        "subjects":("civil engineering","structural engineering","transportation","geotechnical engineering","smart infrastructure","construction","disaster resilience","urban systems"),
        "leads":("baudhayana","bharadvaja","bhaskaracharya"),"support":("varahamihira","jamadagni","chanakya","gautama"),
        "safety":"standard_frontier_research",
    },
    "bodhi":{
        "name":"Project BODHI","mission":"AI for scientific discovery, trustworthy reasoning and machine-assisted knowledge creation.",
        "subjects":("artificial intelligence","machine learning","scientific AI","foundation models","AI agents","reasoning","AI evaluation","knowledge systems"),
        "leads":("vishwamitra","pingala","madhava"),"support":("gautama","jamadagni","bharadvaja","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "shunya":{
        "name":"Project SHUNYA","mission":"Mathematics, computation, optimization and formal methods for hard scientific problems.",
        "subjects":("mathematics","algebra","number theory","optimization","numerical analysis","differential equations","discrete math","formal methods"),
        "leads":("aryabhata","brahmagupta","bhaskaracharya","madhava"),"support":("pingala","gautama","bharadvaja","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "satya":{
        "name":"Project SATYA","mission":"Improve scientific reliability through replication, causal inference and evidence auditing.",
        "subjects":("meta-science","replication","causal inference","statistics","publication bias","research integrity","benchmarking","evidence synthesis"),
        "leads":("gautama","bharadvaja"),"support":("veda-vyasa","madhava","vashistha"),
        "safety":"standard_frontier_research",
    },
    "artha":{
        "name":"Project ARTHA","mission":"Economics, supply chains, resource allocation and resilient public systems.",
        "subjects":("economics","operations research","logistics","supply chains","resource allocation","industrial organization","risk economics","public systems"),
        "leads":("chanakya","bhaskaracharya"),"support":("gautama","vashistha","jamadagni","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
    "saraswati":{
        "name":"Project SARASWATI","mission":"Language, education, knowledge preservation and high-fidelity translation.",
        "subjects":("education","linguistics","translation","knowledge preservation","digital humanities","Sanskrit","NLP","learning science"),
        "leads":("panini","veda-vyasa","bharadvaja"),"support":("agastya","pingala","gautama"),
        "safety":"standard_frontier_research",
    },
    "nirmana":{
        "name":"Project NIRMANA","mission":"Advanced manufacturing, industrial processes and resilient production.",
        "subjects":("advanced manufacturing","industrial engineering","process engineering","additive manufacturing","quality engineering","metrology","industrial automation","production systems"),
        "leads":("nagarjuna","bharadvaja","vishwamitra"),"support":("chanakya","bhaskaracharya","jamadagni","gautama"),
        "safety":"standard_frontier_research",
    },
    "suraksha":{
        "name":"Project SURAKSHA","mission":"Defensive cybersecurity, critical-infrastructure resilience and trustworthy autonomous systems.",
        "subjects":("cybersecurity","AI security","critical infrastructure","software assurance","resilience","incident response","supply-chain security","fault tolerance"),
        "leads":("jamadagni","vishwamitra"),"support":("pingala","gautama","bharadvaja","chanakya"),
        "safety":"defensive_security_only",
    },
    "vasudha":{
        "name":"Project VASUDHA","mission":"Biodiversity, conservation, ecosystem restoration and planetary health.",
        "subjects":("biodiversity","conservation","ecosystem restoration","ecology","wildlife","planetary health","habitat","environmental genomics"),
        "leads":("kashyapa","agastya","parashara"),"support":("shalihotra","varahamihira","gautama","veda-vyasa"),
        "safety":"standard_frontier_research",
    },
}


class GrandChallengeRegistry:
    VERSION="grand-challenges-v1"

    def __init__(self,state_root,council):
        self.root=Path(state_root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"grand-challenges.json"
        self.council=council
        self.lock=RLock()
        self.custom={}
        self._load()
        self._validate_builtin()

    def _load(self):
        if not self.path.is_file():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw,dict) and isinstance(raw.get("custom"),dict):
                self.custom=raw["custom"]
        except Exception:
            self.custom={}

    def _save(self):
        tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version":self.VERSION,"custom":self.custom},ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(tmp,self.path)

    def _validate_builtin(self):
        valid={x["id"] for x in self.council.list()}
        for pid,row in BUILTIN_GRAND_CHALLENGES.items():
            missing=[x for x in tuple(row["leads"])+tuple(row["support"]) if x not in valid]
            if missing:raise ValueError(f"{pid} references unknown Rishis: {missing}")

    @staticmethod
    def _normalize(row,project_id):
        return {
            "project_id":str(project_id),
            "name":str(row.get("name") or project_id),
            "mission":str(row.get("mission") or ""),
            "subjects":list(row.get("subjects") or []),
            "leads":list(row.get("leads") or []),
            "support":list(row.get("support") or []),
            "safety":str(row.get("safety") or "standard_frontier_research"),
            "builtin":project_id in BUILTIN_GRAND_CHALLENGES,
        }

    def list(self):
        rows=[self._normalize(v,k) for k,v in BUILTIN_GRAND_CHALLENGES.items()]
        rows.extend(self._normalize(v,k) for k,v in self.custom.items())
        return sorted(rows,key=lambda x:x["project_id"])

    def get(self,project_id):
        pid=str(project_id or "").strip().lower()
        row=BUILTIN_GRAND_CHALLENGES.get(pid) or self.custom.get(pid)
        if not row:raise KeyError(project_id)
        return self._normalize(row,pid)

    def create_custom(self,project_id,name,mission,subjects,leads,support=None,safety="standard_frontier_research"):
        pid=str(project_id or "").strip().lower().replace(" ","_")
        if not pid or pid in BUILTIN_GRAND_CHALLENGES:raise ValueError("custom project_id is invalid or reserved")
        valid={x["id"] for x in self.council.list()}
        lead_ids=[str(x).strip().lower() for x in leads or []]
        support_ids=[str(x).strip().lower() for x in support or []]
        unknown=[x for x in lead_ids+support_ids if x not in valid]
        if unknown:raise ValueError(f"unknown Rishi IDs: {unknown}")
        if not lead_ids:raise ValueError("at least one lead Rishi is required")
        row={
            "name":str(name or pid).strip(),
            "mission":str(mission or "").strip(),
            "subjects":[str(x).strip() for x in subjects or [] if str(x).strip()],
            "leads":lead_ids,
            "support":support_ids,
            "safety":str(safety or "standard_frontier_research"),
            "created_at":time.time(),
            "custom_id":str(uuid.uuid4()),
        }
        with self.lock:
            self.custom[pid]=row;self._save()
        return self.get(pid)

    def add_subject(self,project_id,subject):
        pid=str(project_id or "").strip().lower()
        subject=str(subject or "").strip()
        if not subject:raise ValueError("subject is required")
        if pid in BUILTIN_GRAND_CHALLENGES:
            raise ValueError("built-in projects are version-controlled; create a custom project to extend persistently")
        with self.lock:
            row=self.custom.get(pid)
            if not row:raise KeyError(project_id)
            row.setdefault("subjects",[])
            if subject not in row["subjects"]:row["subjects"].append(subject)
            self._save()
        return self.get(pid)

    def route(self,text,limit=10):
        q=str(text or "").lower()
        scored=[]
        for row in self.list():
            score=sum(3 for s in row["subjects"] if str(s).lower() in q)
            score+=sum(1 for token in row["mission"].lower().split() if len(token)>5 and token in q)
            if score:scored.append((score,row))
        scored.sort(key=lambda x:(-x[0],x[1]["project_id"]))
        return [x[1] for x in scored[:max(1,min(int(limit),30))]]

    def status(self):
        return {
            "name":"BRAHMAGYAN Grand Challenge Registry",
            "version":self.VERSION,
            "builtin_projects":len(BUILTIN_GRAND_CHALLENGES),
            "custom_projects":len(self.custom),
            "projects":self.list(),
            "policy":"projects coordinate long-running human-benefit research across Science Atlas topics and Rishi teams",
        }
