from __future__ import annotations

"""Deep subject ontology for BRAHMAGYAN.

Keeps permanent Rishis small while allowing every knowledge domain to expand:
domain -> discipline -> specialty -> frontier -> research/LAB capability.
The ontology is modern KRISHNA routing metadata, not a historical attribution
to the people whose names are used for Rishi profiles.
"""

SUBJECT_DEPTH = {
    "physical_sciences": {
        "owners": ("kanada", "gautama"),
        "disciplines": {
            "physics": ("classical mechanics","electromagnetism","thermodynamics","statistical mechanics","quantum physics","particle physics","nuclear physics","condensed matter","plasma physics","optics","photonics","superconductivity"),
            "chemistry": ("organic chemistry","inorganic chemistry","physical chemistry","analytical chemistry","electrochemistry","catalysis","surface chemistry","computational chemistry"),
            "materials": ("metals","ceramics","polymers","composites","nanomaterials","2d materials","quantum materials","metamaterials","mofs","smart materials"),
        },
    },
    "mathematics_computation": {
        "owners": ("aryabhata","brahmagupta","bhaskaracharya","madhava","pingala","gautama"),
        "disciplines": {
            "pure_mathematics": ("algebra","geometry","number theory","topology","analysis","logic","combinatorics"),
            "applied_mathematics": ("differential equations","optimization","operations research","dynamical systems","numerical methods","scientific computing"),
            "statistics_data_science": ("probability","statistical inference","causal inference","bayesian methods","experimental design","time series","uncertainty quantification"),
            "information_science": ("information theory","coding theory","compression","signal processing","error correction"),
        },
    },
    "computing_digital_systems": {
        "owners": ("tvasta","pingala","jamadagni","vishvakarma"),
        "disciplines": {
            "computer_science": ("algorithms","complexity","data structures","programming languages","compilers","formal methods","software engineering"),
            "systems": ("operating systems","kernels","drivers","virtualization","containers","distributed systems","cloud","datacentres","hpc"),
            "computer_architecture": ("cpu","gpu","npu","memory hierarchy","interconnects","accelerators","heterogeneous computing"),
            "chips": ("semiconductors","vlsi","eda","fpga","asic","chiplets","advanced packaging","fabrication","yield"),
            "data_systems": ("databases","storage","filesystems","distributed storage","stream processing","vector databases"),
            "networks": ("tcp/ip","ethernet","wifi","routing","switching","sdn","edge computing","telecommunications"),
            "ai_systems": ("machine learning systems","deep learning","foundation models","multimodal ai","agents","inference","training","quantization","rag"),
            "emerging_computing": ("quantum computing","photonic computing","neuromorphic computing","analog computing","in-memory computing","reversible computing","dna computing","molecular computing","biological computing","organoid intelligence"),
        },
    },
    "engineering": {
        "owners": ("vishvakarma","bharadvaja","baudhayana","tvasta"),
        "disciplines": {
            "electrical_electronics": ("circuits","power electronics","embedded electronics","sensors","instrumentation","control electronics","rf","microwave"),
            "mechanical": ("mechanics","machines","thermofluids","tribology","mechatronics","robotics","cad","cae"),
            "civil_infrastructure": ("structures","geotechnical","transportation","water resources","construction","surveying","smart infrastructure"),
            "chemical_process": ("transport phenomena","reaction engineering","separations","process control","process safety"),
            "manufacturing": ("cnc","additive manufacturing","robotic manufacturing","metrology","quality engineering","industrial automation"),
            "robotics_control": ("control theory","kinematics","dynamics","slam","planning","manipulation","autonomous systems","human robot interaction"),
        },
    },
    "aerospace_space": {
        "owners": ("marichi","aryabhata","atri","kanada","vishvakarma","tvasta"),
        "disciplines": {
            "aeronautics": ("aerodynamics","compressible flow","flight mechanics","aircraft structures","hypersonics","cfd"),
            "propulsion": ("liquid rockets","solid rockets","hybrid rockets","cryogenics","combustion","electric propulsion","ion propulsion","hall thrusters","plasma propulsion","future propulsion"),
            "launch_systems": ("staging","reusable launch vehicles","thermal protection","range systems","launch operations","vehicle health monitoring"),
            "spacecraft": ("spacecraft design","avionics","gnc","telemetry","thermal control","power systems","space robotics","life support"),
            "astrodynamics": ("orbital mechanics","trajectory optimization","rendezvous","entry descent landing","mission design"),
            "space_operations": ("satellites","payloads","ground systems","space communications","space debris","isru","planetary operations"),
        },
    },
    "life_health_sciences": {
        "owners": ("kashyapa","sushruta","charaka","dhanvantari","kapila","patanjali","gautama"),
        "disciplines": {
            "molecular_cell_biology": ("molecular biology","cell biology","biochemistry","gene regulation","proteomics","metabolomics"),
            "genetics_genomics": ("genetics","genomics","epigenetics","transcriptomics","population genetics","gene editing","functional genomics"),
            "biotechnology": ("synthetic biology","bioprocessing","bioengineering","systems biology","computational biology","bioinformatics"),
            "neuroscience": ("cellular neuroscience","systems neuroscience","cognitive neuroscience","computational neuroscience","neuroengineering","bci","neuroprosthetics"),
            "immunology": ("innate immunity","adaptive immunity","immune tolerance","autoimmunity","immunotherapy","vaccinology"),
            "cancer_science": ("cancer genetics","tumor biology","metastasis","tumor immunology","biomarkers","therapy resistance"),
            "regeneration_aging": ("stem cells","organoids","tissue engineering","cellular reprogramming","senescence","telomeres","autophagy","aging biology"),
            "medicine": ("anatomy","physiology","pathology","diagnostics","internal medicine","surgery","preventive medicine","public health"),
            "therapeutics": ("pharmacology","drug discovery","medicinal chemistry","pharmacokinetics","toxicology","clinical trials","precision medicine"),
        },
    },
    "earth_environment_agriculture": {
        "owners": ("varahamihira","parashara","agastya","shalihotra","atri"),
        "disciplines": {
            "earth_science": ("geology","geophysics","geochemistry","seismology","volcanology","geomorphology"),
            "atmosphere_climate": ("meteorology","climate science","atmospheric chemistry","remote sensing","climate modeling"),
            "water_ocean": ("hydrology","hydrogeology","oceanography","coastal science","water quality"),
            "ecology_environment": ("ecology","biodiversity","conservation","pollution","environmental monitoring","ecosystem modeling"),
            "agriculture": ("agronomy","soil science","crop genetics","plant pathology","irrigation","precision agriculture","agricultural robotics","food systems"),
            "animal_science": ("veterinary science","animal physiology","animal nutrition","livestock science","zoonoses","wildlife health"),
        },
    },
    "energy": {
        "owners": ("kanada","vishwamitra","vishvakarma","bharadvaja"),
        "disciplines": {
            "power_energy": ("power systems","grids","power electronics","energy storage","batteries","supercapacitors"),
            "generation": ("solar","wind","hydro","geothermal","nuclear fission","fusion","hydrogen","fuel cells"),
            "energy_systems": ("microgrids","grid stability","energy efficiency","thermal storage","carbon capture","energy economics"),
        },
    },
    "humanities_language_society": {
        "owners": ("veda-vyasa","panini","yajnavalkya","agastya","vashistha","narada"),
        "disciplines": {
            "language": ("phonetics","phonology","morphology","syntax","semantics","pragmatics","translation","nlp"),
            "philosophy": ("epistemology","logic","metaphysics","ethics","philosophy of science","philosophy of mind"),
            "history_civilization": ("history","archaeology","history of science","history of technology","cultural transmission"),
            "law_governance": ("constitutional law","civil law","criminal law","evidence","contracts","business law","technology law","privacy","regulation"),
        },
    },
}

FRONTIER_AXES = (
    "mechanism", "state_of_the_art", "maturity", "limitations", "negative_results",
    "contradictory_evidence", "reproducibility", "safety", "ethics", "standards",
    "patents", "open_source_implementations", "cross_domain_transfer",
    "what_else_can_this_become", "lab_testability",
)

def all_specialties():
    rows = []
    for domain, drow in SUBJECT_DEPTH.items():
        for discipline, specialties in drow["disciplines"].items():
            for specialty in specialties:
                rows.append({"domain": domain, "discipline": discipline, "specialty": specialty, "owners": list(drow["owners"])})
    return rows

def find_subject(text):
    q = str(text or "").lower()
    hits = []
    for row in all_specialties():
        score = sum(1 for token in row["specialty"].split() if token in q)
        if row["specialty"] in q:
            score += 4
        if score:
            hits.append((score, row))
    hits.sort(key=lambda x: (-x[0], x[1]["specialty"]))
    return [row for _, row in hits]

def gap_report(council_ids):
    ids = set(council_ids)
    gaps = []
    for domain, row in SUBJECT_DEPTH.items():
        active = [x for x in row["owners"] if x in ids]
        if not active:
            gaps.append({"kind": "domain_without_owner", "domain": domain})
        for owner in row["owners"]:
            if owner not in ids:
                gaps.append({"kind": "missing_owner", "domain": domain, "owner": owner})
    return gaps
