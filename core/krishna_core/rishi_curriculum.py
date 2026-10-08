from __future__ import annotations

"""Permanent, evidence-gated curricula for the BRAHMAGYAN Rishi Council.

The curriculum layer is deliberately a planner/ledger, not another research
runtime.  It reuses the permanent Rishi learning ledger for findings and the
same GYAN-SAGAR source catalogs for source selection.  Network execution stays
behind KRISHNA's existing Garuda / Shared Action Bus / browser / connector
boundaries.

Historical/traditional Rishi names remain KRISHNA design roles.  A modern
subject assignment never asserts that a historical figure practiced that
modern discipline.
"""

import json
import os
import re
import time
import uuid
from pathlib import Path
from threading import RLock

from .rishi_learning import RishiLearningLedger as _BaseRishiLearningLedger
from .rishi_learning import DIRECT_LEARNING_ROLES
from .rishi_gyan_sagar import RishiGyanSagar
from .rishi_deep_sources import RishiDeepSourceExpansion


CURRICULUM_VERSION = "rishi-curriculum-v1"

# The external frameworks below inform *structure*, not factual subject answers.
# Actual Rishi claims still need source evidence and BRAHMAGYAN maturity gates.
CURRICULUM_RESEARCH_BASIS = (
    {
        "authority": "National Medical Commission (India)",
        "reference": "Revised Competency Based Medical Education Curriculum 2024",
        "published": "2024-09-12",
        "applies_to": ("sushruta", "charaka", "dhanvantari", "shalihotra"),
        "principles": (
            "competency-based progression",
            "knowledge, skills, attitudes and values",
            "integrated learning and assessment",
            "clinical/real-world exposure before claims of competence",
        ),
        "url": "https://www.nmc.org.in/wp-content/uploads/2026/02/12bCompetencyBasedMedicalEducationCBMECurriculum12092024.pdf",
    },
    {
        "authority": "All India Council for Technical Education (India)",
        "reference": "AICTE Model Curricula for Undergraduate Engineering & Technology",
        "published": "2024 model-curriculum series",
        "applies_to": (
            "vishwamitra", "vishvakarma", "bharadvaja", "kanada", "nagarjuna",
            "baudhayana", "aryabhata", "bhaskaracharya", "jamadagni",
        ),
        "principles": (
            "foundation/basic science before specialization",
            "engineering science before professional core",
            "practical/laboratory verification",
            "design, project and applied synthesis",
        ),
        "url": "https://aicte-india.org/",
    },
    {
        "authority": "Central Sanskrit University (India)",
        "reference": "Current syllabus framework",
        "published": "2026-2027 syllabus cycle",
        "applies_to": ("panini", "veda-vyasa", "yajnavalkya", "patanjali", "agastya"),
        "principles": (
            "discipline-specific classical study",
            "textual provenance and philology",
            "multi-disciplinary and modern elective context",
            "classical claims remain separate from modern empirical evidence",
        ),
        "url": "https://www.sanskrit.nic.in/syllabus.php",
    },
)


STAGES = (
    {
        "id": "foundation",
        "label": "Foundation",
        "order": 1,
        "min_findings": 1,
        "min_verified": 0,
        "exam_threshold": 0.70,
        "objectives": (
            "Define the field's vocabulary, scope, canonical models and measurement language.",
            "Map authoritative source families and distinguish primary evidence from commentary.",
            "Identify safety, rights, uncertainty and classical/modern evidence boundaries.",
        ),
    },
    {
        "id": "core",
        "label": "Core",
        "order": 2,
        "min_findings": 2,
        "min_verified": 1,
        "exam_threshold": 0.75,
        "objectives": (
            "Understand mechanisms, methods, standard practices and common failure modes.",
            "Use primary or normative evidence and reproduce basic calculations/interpretations.",
            "Compare at least two independent source families where the claim permits it.",
        ),
    },
    {
        "id": "advanced",
        "label": "Advanced",
        "order": 3,
        "min_findings": 3,
        "min_verified": 1,
        "exam_threshold": 0.80,
        "objectives": (
            "Evaluate competing models, edge cases, uncertainty and known limitations.",
            "Connect theory to measured, experimental, clinical or implementation evidence.",
            "Explain how the field fails and how evidence quality changes conclusions.",
        ),
    },
    {
        "id": "frontier",
        "label": "Frontier",
        "order": 4,
        "min_findings": 3,
        "min_verified": 1,
        "exam_threshold": 0.80,
        "objectives": (
            "Track recent research, standards, patents, datasets, tools and unresolved contradictions.",
            "Separate emerging feasibility from replicated or practice-ready evidence.",
            "Form falsifiable next questions instead of converting novelty into certainty.",
        ),
    },
    {
        "id": "synthesis",
        "label": "Synthesis",
        "order": 5,
        "min_findings": 2,
        "min_verified": 1,
        "exam_threshold": 0.85,
        "objectives": (
            "Integrate the field into a provenance-preserving knowledge map that another Rishi can use.",
            "State supported conclusions, contested conclusions, unknowns and required next evidence.",
            "Teach the subject without erasing uncertainty, chronology, licensing or evidence boundaries.",
        ),
    },
)

STAGE_BY_ID = {x["id"]: x for x in STAGES}
MATURITY_RANK = {f"L{x}": x for x in range(9)}
VERIFIED_EVIDENCE = {
    "verified", "replicated", "strongly_supported", "moderately_supported",
}


# Curated stage maps for Rishis where the order of study materially matters.
# Every other permanent council member is generated from the existing charter.
SPECIAL_STAGE_SUBJECTS = {
    "sushruta": {
        "foundation": ("anatomy", "physiology", "pathology", "clinical research"),
        "core": ("diagnostics", "surgery", "medical devices", "medical imaging"),
        "advanced": ("biomedical engineering", "biomechanics", "biomaterials", "clinical engineering"),
        "frontier": ("neural engineering", "regenerative medicine", "tissue engineering", "medical AI"),
        "synthesis": ("patient safety", "evidence translation", "medical-device lifecycle", "clinical decision support"),
    },
    "charaka": {
        "foundation": ("physiology", "nutrition", "internal medicine", "preventive medicine"),
        "core": ("diagnosis", "pharmacology", "public health", "disease progression"),
        "advanced": ("metabolism", "chronic disease", "therapeutics", "clinical prevention"),
        "frontier": ("aging medicine", "precision prevention", "drug and lifestyle evidence", "risk modification"),
        "synthesis": ("systemic medicine", "prevention evidence", "benefit-risk communication", "clinical uncertainty"),
    },
    "dhanvantari": {
        "foundation": ("pharmacology", "toxicology", "pharmacokinetics", "pharmacodynamics"),
        "core": ("drug discovery", "drug delivery", "clinical pharmacology", "therapeutics"),
        "advanced": ("target validation", "treatment optimization", "translational medicine", "critical care"),
        "frontier": ("precision medicine", "drug repurposing", "novel modalities", "safety-efficacy tradeoffs"),
        "synthesis": ("mechanism-to-treatment translation", "therapeutic evidence", "adverse-effect reasoning", "treatment uncertainty"),
    },
    "kanada": {
        "foundation": ("mechanics", "thermodynamics", "electromagnetism", "measurement science"),
        "core": ("atomic physics", "molecular science", "chemistry", "materials science"),
        "advanced": ("condensed matter", "physical properties", "metrology", "cross-scale physics"),
        "frontier": ("nanoscience", "emerging materials", "new states of matter", "measurement-model mismatch"),
        "synthesis": ("physical models", "uncertainty budgets", "matter classification", "model-evidence reconciliation"),
    },
    "vishwamitra": {
        "foundation": ("artificial intelligence", "robotics", "systems engineering", "energy technology"),
        "core": ("autonomous systems", "space technology", "quantum technology", "emerging materials"),
        "advanced": ("human-machine interfaces", "patents", "technical standards", "engineering validation"),
        "frontier": ("frontier engineering", "new tools and repositories", "cross-field invention", "future technologies"),
        "synthesis": ("technology readiness", "evidence-to-prototype translation", "interoperability", "safe adoption"),
    },
    "vishvakarma": {
        "foundation": ("design systems", "UI", "UX", "frontend architecture"),
        "core": ("typography", "spacing", "responsive design", "accessibility"),
        "advanced": ("component architecture", "browser testing", "visual regression", "interaction design"),
        "frontier": ("image-to-code", "UI repair", "human-AI interface design", "design-system evolution"),
        "synthesis": ("coherent product language", "measurable interface quality", "design drift prevention", "verified implementation handoff"),
    },
    "panini": {
        "foundation": ("Sanskrit", "phonetics", "grammar", "morphology"),
        "core": ("syntax", "semantics", "textual criticism", "Indian languages"),
        "advanced": ("formal grammar", "parsing", "translation", "corpus linguistics"),
        "frontier": ("NLP", "computational linguistics", "language models", "multilingual reasoning"),
        "synthesis": ("high-precision translation", "philological provenance", "machine-readable grammar", "cross-lingual knowledge transfer"),
    },
    "gautama": {
        "foundation": ("logic", "epistemology", "probability", "statistics"),
        "core": ("causality", "research methodology", "source independence", "argument analysis"),
        "advanced": ("bias", "replication", "evidence grading", "fact checking"),
        "frontier": ("meta-science", "causal identification", "replication failure", "measurement error"),
        "synthesis": ("falsification", "evidence audit", "uncertainty calibration", "false-consensus detection"),
    },
    "veda-vyasa": {
        "foundation": ("knowledge architecture", "research provenance", "history of science", "textual traditions"),
        "core": ("research synthesis", "knowledge graphs", "scientific timelines", "ontology"),
        "advanced": ("cross-domain synthesis", "version history", "duplicate knowledge detection", "historical source criticism"),
        "frontier": ("knowledge-map evolution", "conflict preservation", "cross-field evidence integration", "reusable knowledge structures"),
        "synthesis": ("canonical compilation", "provenance-preserving synthesis", "contested-knowledge representation", "council knowledge handoff"),
    },
    "bharadvaja": {
        "foundation": ("scientific method", "measurement design", "experimental design", "testing"),
        "core": ("benchmarking", "simulation", "engineering methodology", "research reproducibility"),
        "advanced": ("applied science", "learning science", "knowledge transfer", "experiment quality"),
        "frontier": ("better experiment design", "benchmark construction", "falsification planning", "theory-to-application transfer"),
        "synthesis": ("reproducible research program", "test strategy", "measurement evidence", "teachable method"),
    },
    "atri": {
        "foundation": ("astronomy", "measurement science", "timekeeping", "remote sensing"),
        "core": ("astrophysics", "solar physics", "planetary science", "earth observation"),
        "advanced": ("cosmology", "geodesy", "space observation", "measurement uncertainty"),
        "frontier": ("new observations", "anomalous astronomical data", "planetary dynamics", "observation-model disagreement"),
        "synthesis": ("observation provenance", "uncertainty-aware astronomy", "model-data comparison", "multi-instrument evidence"),
    },
    "jamadagni": {
        "foundation": ("defensive cybersecurity", "system resilience", "data integrity", "failure analysis"),
        "core": ("software security", "incident response", "disaster recovery", "reliability engineering"),
        "advanced": ("AI security", "supply-chain security", "fault tolerance", "safety engineering"),
        "frontier": ("adversarial testing", "autonomous-system security", "unexpected interaction risk", "recovery research"),
        "synthesis": ("defense-in-depth", "failure-to-recovery architecture", "resilience evidence", "safe rollback strategy"),
    },
    "narada": {
        "foundation": ("constitutional law", "statutory interpretation", "legal research", "jurisdiction"),
        "core": ("legislation", "rules and regulations", "judicial precedent", "evidence law"),
        "advanced": ("contracts", "business law", "privacy and data protection", "cyber and technology law"),
        "frontier": ("new Acts and amendments", "regulator directions", "current judgments", "compliance-by-design"),
        "synthesis": ("current-law verification", "precedent hierarchy", "lawful alternatives", "compliance reasoning"),
    },
    "parashara": {
        "foundation": ("agronomy", "soil science", "crop science", "irrigation"),
        "core": ("plant pathology", "agroecology", "food systems", "agricultural biotechnology"),
        "advanced": ("crop resilience", "precision agriculture", "water-efficient farming", "soil restoration"),
        "frontier": ("climate-resilient crops", "plant disease control", "food-system resilience", "agricultural sensing"),
        "synthesis": ("farm-system evidence", "field validation", "resource efficiency", "food-security strategy"),
    },
    "aryabhata": {
        "foundation": ("mathematics", "trigonometry", "algorithms", "numerical methods"),
        "core": ("scientific computing", "simulation", "computational astronomy", "orbital mechanics"),
        "advanced": ("numerical stability", "scientific software", "precision computation", "dynamical models"),
        "frontier": ("high-precision computation", "scientific code verification", "modern orbital models", "computational discovery"),
        "synthesis": ("verified numerical model", "error analysis", "reproducible computation", "mathematical prediction"),
    },
}


DOMAIN_SOURCE_HINTS = (
    (
        {"medicine", "medical", "clinical", "surgery", "diagnos", "pharma", "health", "biology", "genetic", "drug", "veterinary"},
        ("paper", "full-text", "book", "guideline", "dataset"),
    ),
    (
        {"ai", "software", "robot", "cyber", "engineering", "frontend", "browser", "network", "telecom", "gpu", "system"},
        ("paper", "software", "standard", "patent", "dataset"),
    ),
    (
        {"sanskrit", "grammar", "linguistic", "textual", "upanishad", "veda", "philosophy", "classical"},
        ("classical-text", "book", "paper", "metadata"),
    ),
    (
        {"physics", "chemistry", "material", "astronomy", "space", "earth", "climate", "geology", "measurement"},
        ("paper", "dataset", "technical-report", "standard", "book"),
    ),
    (
        {"math", "algebra", "geometry", "number", "numerical", "equation", "combinator"},
        ("paper", "book", "software", "dataset"),
    ),
    (
        {"agriculture", "agronomy", "crop", "soil", "ecology", "environment", "food"},
        ("paper", "dataset", "technical-report", "book"),
    ),
    (
        {"law", "legal", "statut", "regulation", "judicial", "precedent", "compliance"},
        ("paper", "book", "metadata"),
    ),
    (
        {"sales", "marketing", "economics", "customer", "supply", "business", "strategy"},
        ("paper", "book", "dataset", "metadata"),
    ),
)


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text[:80] or "unit"


def _terms(value):
    return {
        x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}", str(value or "").lower())
        if len(x) > 2
    }


def _chunks(items, count=5):
    rows = list(items or [])
    if not rows:
        return [[] for _ in range(count)]
    out = [[] for _ in range(count)]
    # Preserve charter order while spreading a long charter across five stages.
    for idx, item in enumerate(rows):
        bucket = min(count - 1, int(idx * count / max(1, len(rows))))
        out[bucket].append(item)
    # Ensure no empty stage by carrying the nearest subject forward.
    last = rows[0]
    for idx in range(count):
        if out[idx]:
            last = out[idx][-1]
        else:
            out[idx] = [last]
    return out


class RishiCurriculumAcademy:
    """Persistent assessment/session ledger + dynamically generated curricula."""

    VERSION = CURRICULUM_VERSION

    def __init__(self, state_root, council, learning_ledger, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "curriculum.json"
        self.council = council
        self.ledger = learning_ledger
        self.memory = memory
        self.lock = RLock()
        self.base_sources = RishiGyanSagar()
        self.deep_sources = RishiDeepSourceExpansion()
        self.state = {
            "version": self.VERSION,
            "exams": [],
            "study_sessions": [],
            "created_at": time.time(),
        }
        self.load_error = None
        self._load()

    def _load(self):
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.state.update(raw)
                self.state.setdefault("exams", [])
                self.state.setdefault("study_sessions", [])
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            if self.memory:
                self.memory.audit("rishi_curriculum", "load_failed", self.load_error)

    def _healthy(self):
        if self.load_error:
            raise RuntimeError("Rishi curriculum state is unreadable; refusing to overwrite it: " + self.load_error)

    def _save(self):
        self._healthy()
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def _charter(self, rishi_id):
        rid = str(rishi_id or "").strip().lower()
        self.council.get(rid)
        # Call the base implementation directly so subclass presentation wrappers
        # cannot recurse back through curriculum generation.
        return _BaseRishiLearningLedger.charter(self.ledger, rid)

    def _stage_subjects(self, rishi_id):
        rid = str(rishi_id or "").strip().lower()
        special = SPECIAL_STAGE_SUBJECTS.get(rid)
        if special:
            return {stage["id"]: list(special[stage["id"]]) for stage in STAGES}
        charter = self._charter(rid)
        groups = _chunks(charter.get("primary_subjects") or [], len(STAGES))
        return {stage["id"]: list(groups[idx]) for idx, stage in enumerate(STAGES)}

    def _source_kinds(self, subjects):
        tokens = _terms(" ".join(subjects or []))
        kinds = []
        for hints, row_kinds in DOMAIN_SOURCE_HINTS:
            if any(any(token.startswith(hint) or hint in token for hint in hints) for token in tokens):
                for kind in row_kinds:
                    if kind not in kinds:
                        kinds.append(kind)
        if not kinds:
            kinds = ["paper", "book", "metadata"]
        return kinds

    def _special_rules(self, rishi_id, stage_id):
        rid = str(rishi_id or "").strip().lower()
        rules = []
        if rid in {"sushruta", "charaka", "dhanvantari", "shalihotra"}:
            rules.extend((
                "Clinical/health competence is never inferred from reading alone; human-use claims require appropriate modern evidence.",
                "Keep mechanism, preclinical evidence, clinical evidence and guideline-level evidence visibly separate.",
                "Safety, contraindications, population limits and uncertainty must remain explicit.",
            ))
        if rid in {"vishwamitra", "vishvakarma", "bharadvaja", "jamadagni", "kanada", "nagarjuna", "baudhayana"}:
            rules.extend((
                "Engineering competence requires reproducible calculations, tests, measurements, simulations or implementation evidence where applicable.",
                "Standards and safety constraints outrank convenience; prototype feasibility is not production readiness.",
            ))
        if rid in {"panini", "veda-vyasa", "yajnavalkya", "patanjali", "agastya"}:
            rules.extend((
                "Preserve edition, textual layer, translation and commentary provenance.",
                "Classical resemblance never counts as experimental proof for a modern scientific claim.",
            ))
        if rid == "gautama":
            rules.extend((
                "Audit source independence, study design, causal identification and contradiction handling.",
                "Do not reward consensus created by copied or dependent sources.",
            ))
        if rid == "narada":
            rules.extend((
                "Current official law, commencement status, amendments and authentic judgments govern modern legal conclusions.",
                "Use the dedicated Narada legal-source runtime for final current-law verification.",
            ))
        if stage_id == "frontier":
            rules.append("Recent or novel material remains provisional until independently checked.")
        if stage_id == "synthesis":
            rules.append("Veda Vyasa must be included in the final assessment review and unresolved disagreement must be preserved.")
        return rules

    def _unit(self, rishi_id, stage):
        rid = str(rishi_id or "").strip().lower()
        profile = self.council.get(rid)
        subjects = self._stage_subjects(rid)[stage["id"]]
        charter = self._charter(rid)
        source_kinds = self._source_kinds(subjects)
        objectives = list(stage["objectives"])
        objectives.extend(self._special_rules(rid, stage["id"]))
        if stage["id"] == "frontier":
            objectives.extend(charter.get("frontier_focus") or [])
        return {
            "unit_id": f"{rid}:{stage['id']}",
            "rishi_id": rid,
            "rishi_name": profile["display_name"],
            "rishi_role": profile["role"],
            "stage": stage["id"],
            "stage_label": stage["label"],
            "stage_order": stage["order"],
            "subjects": subjects,
            "subject": " / ".join(subjects),
            "objectives": objectives,
            "source_kinds": source_kinds,
            "assessment": {
                "min_direct_findings": stage["min_findings"],
                "min_verified_findings": stage["min_verified"],
                "exam_threshold": stage["exam_threshold"],
                "required_reviewers": ["gautama"] + (["veda-vyasa"] if stage["id"] == "synthesis" else []),
                "exam_alone_is_not_mastery": True,
            },
            "classical_lens": charter.get("classical_lens") or [],
            "execution_policy": "curriculum plans evidence work only; live research executes through existing KRISHNA authority boundaries",
        }

    def curriculum(self, rishi_id, include_sources=False):
        rid = str(rishi_id or "").strip().lower()
        profile = self.council.get(rid)
        units = []
        for stage in STAGES:
            unit = self._unit(rid, stage)
            unit["progress"] = self.unit_progress(rid, unit["unit_id"])
            if include_sources:
                unit["source_plan"] = self.source_plan(rid, unit["unit_id"], max_sources=10)
            units.append(unit)
        return {
            "version": self.VERSION,
            "rishi_id": rid,
            "display_name": profile["display_name"],
            "role": profile["role"],
            "units": units,
            "research_basis": [x for x in CURRICULUM_RESEARCH_BASIS if rid in x["applies_to"]],
            "policy": "stage completion requires evidence; exams measure understanding but cannot manufacture evidence or BRAHMAGYAN maturity",
        }

    def all_curricula(self, include_sources=False):
        return [self.curriculum(x["id"], include_sources=include_sources) for x in self.council.list()]

    def _unit_from_id(self, rishi_id, unit_id):
        rid = str(rishi_id or "").strip().lower()
        wanted = str(unit_id or "").strip().lower()
        for stage in STAGES:
            unit = self._unit(rid, stage)
            if unit["unit_id"] == wanted:
                return unit
        raise KeyError(unit_id)

    def _snapshot_findings(self, rishi_id):
        rid = str(rishi_id or "").strip().lower()
        self.council.get(rid)
        with self.ledger.lock:
            row = json.loads(json.dumps(self.ledger.state["rishis"][rid]))
        return list(row.get("findings") or [])

    @staticmethod
    def _finding_matches(unit, finding):
        wanted = _terms(" ".join(unit.get("subjects") or []))
        actual = _terms(f"{finding.get('topic') or ''} {finding.get('claim') or ''}")
        return bool(wanted & actual)

    @staticmethod
    def _is_verified(finding):
        maturity = MATURITY_RANK.get(str(finding.get("maturity") or "L0"), 0)
        status = str(finding.get("evidence_status") or "").strip().lower()
        return maturity >= 3 and status in VERIFIED_EVIDENCE and not bool(finding.get("unresolved"))

    def _latest_exam(self, rishi_id, unit_id):
        rid = str(rishi_id or "").strip().lower()
        uid = str(unit_id or "").strip().lower()
        with self.lock:
            rows = [
                json.loads(json.dumps(x)) for x in self.state.get("exams") or []
                if x.get("rishi_id") == rid and x.get("unit_id") == uid
            ]
        rows.sort(key=lambda x: float(x.get("created_at") or 0), reverse=True)
        return rows[0] if rows else None

    def _previous_unit_id(self, rishi_id, stage_order):
        if int(stage_order) <= 1:
            return None
        prev = [x for x in STAGES if int(x["order"]) == int(stage_order) - 1]
        return f"{rishi_id}:{prev[0]['id']}" if prev else None

    def unit_progress(self, rishi_id, unit_id):
        rid = str(rishi_id or "").strip().lower()
        unit = self._unit_from_id(rid, unit_id)
        matching = [
            x for x in self._snapshot_findings(rid)
            if x.get("role") in DIRECT_LEARNING_ROLES and self._finding_matches(unit, x)
        ]
        verified = [x for x in matching if self._is_verified(x)]
        unique_missions = sorted({str(x.get("mission_id")) for x in matching if x.get("mission_id")})
        evidence_ready = (
            len(matching) >= int(unit["assessment"]["min_direct_findings"])
            and len(verified) >= int(unit["assessment"]["min_verified_findings"])
        )
        exam = self._latest_exam(rid, unit["unit_id"])
        exam_passed = bool(exam and exam.get("passed"))
        previous = self._previous_unit_id(rid, unit["stage_order"])
        prerequisite_mastered = True
        if previous:
            # Avoid recursive prerequisite chains: inspect only the prior unit's
            # evidence + exam directly and let each stage enforce its own prior.
            prev_unit = self._unit_from_id(rid, previous)
            prev_matching = [
                x for x in self._snapshot_findings(rid)
                if x.get("role") in DIRECT_LEARNING_ROLES and self._finding_matches(prev_unit, x)
            ]
            prev_verified = [x for x in prev_matching if self._is_verified(x)]
            prev_evidence = (
                len(prev_matching) >= int(prev_unit["assessment"]["min_direct_findings"])
                and len(prev_verified) >= int(prev_unit["assessment"]["min_verified_findings"])
            )
            prev_exam = self._latest_exam(rid, previous)
            prerequisite_mastered = bool(prev_evidence and prev_exam and prev_exam.get("passed"))
        mastered = bool(evidence_ready and exam_passed and prerequisite_mastered)
        if mastered:
            status = "mastered"
        elif exam_passed and not evidence_ready:
            status = "assessment_passed_evidence_pending"
        elif evidence_ready:
            status = "assessment_ready"
        elif matching:
            status = "studying"
        else:
            status = "not_started"
        return {
            "unit_id": unit["unit_id"],
            "status": status,
            "direct_findings": len(matching),
            "verified_findings": len(verified),
            "mission_count": len(unique_missions),
            "evidence_ready": evidence_ready,
            "exam_passed": exam_passed,
            "prerequisite_mastered": prerequisite_mastered,
            "mastered": mastered,
            "latest_exam": exam,
            "requirements": unit["assessment"],
            "last_evidence_at": max([float(x.get("learned_at") or 0) for x in matching] or [0.0]),
        }

    def source_plan(self, rishi_id, unit_id, max_sources=10):
        unit = self._unit_from_id(rishi_id, unit_id)
        topic = f"{' '.join(unit['subjects'])} {unit['stage_label']} {unit['rishi_role']}"
        limit = max(3, min(int(max_sources), 20))
        base = self.base_sources.research_plan(
            topic, rishi_id=unit["rishi_id"], kinds=unit["source_kinds"], max_sources=limit,
        )
        extra = self.deep_sources.research_plan(
            topic, rishi_id=unit["rishi_id"], kinds=unit["source_kinds"], max_sources=limit,
        )
        merged = []
        seen = set()
        rows = list(base.get("sources") or []) + list(extra or [])
        rows.sort(key=lambda x: (-int(x.get("score") or 0), str(x.get("priority") or "P9"), str(x.get("name") or "")))
        for row in rows:
            sid = str(row.get("id") or "")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            merged.append(row)
            if len(merged) >= limit:
                break
        execution_route = "narada_legal" if unit["rishi_id"] == "narada" else "garuda_or_approved_connector"
        return {
            "rishi_id": unit["rishi_id"],
            "unit_id": unit["unit_id"],
            "topic": topic,
            "source_kinds": unit["source_kinds"],
            "sources": merged,
            "source_ids": [x["id"] for x in merged],
            "source_fabrics": ["rishi-gyan-sagar", "rishi-deep-sources"],
            "execution_route": execution_route,
            "network_executed": False,
            "zero_spend": True,
            "rights_policy": "READ/INDEX/ARCHIVE/TRAIN remain separate; discovery never grants reuse or training rights",
        }

    def record_exam(self, rishi_id, unit_id, score, reviewers=None, evidence=None, notes=""):
        rid = str(rishi_id or "").strip().lower()
        unit = self._unit_from_id(rid, unit_id)
        value = float(score)
        if value > 1.0:
            value = value / 100.0
        value = max(0.0, min(value, 1.0))
        reviewer_ids = []
        for reviewer in reviewers or []:
            reviewer = str(reviewer or "").strip().lower()
            if reviewer and reviewer not in reviewer_ids:
                self.council.get(reviewer)
                reviewer_ids.append(reviewer)
        required = list(unit["assessment"]["required_reviewers"])
        missing = [x for x in required if x not in reviewer_ids]
        threshold = float(unit["assessment"]["exam_threshold"])
        passed = bool(value >= threshold and not missing)
        row = {
            "exam_id": str(uuid.uuid4()),
            "rishi_id": rid,
            "unit_id": unit["unit_id"],
            "stage": unit["stage"],
            "score": value,
            "threshold": threshold,
            "reviewers": reviewer_ids,
            "required_reviewers": required,
            "missing_reviewers": missing,
            "evidence": list(evidence or []),
            "notes": str(notes or "")[:4000],
            "passed": passed,
            "created_at": time.time(),
            "policy": "exam pass measures curriculum understanding only; evidence gates and BRAHMAGYAN maturity remain separate",
        }
        with self.lock:
            self.state["exams"].append(row)
            self.state["exams"] = self.state["exams"][-5000:]
            self._save()
        if self.memory:
            self.memory.audit("rishi_curriculum_exam", "passed" if passed else "not_passed", f"{rid}:{unit['unit_id']}:{value}")
        return {**row, "unit_progress": self.unit_progress(rid, unit["unit_id"])}

    def record_study_session(self, rishi_id, unit_id, *, mission_id=None, run_id=None, source_ids=None, notes=""):
        rid = str(rishi_id or "").strip().lower()
        unit = self._unit_from_id(rid, unit_id)
        row = {
            "session_id": str(uuid.uuid4()),
            "rishi_id": rid,
            "unit_id": unit["unit_id"],
            "stage": unit["stage"],
            "mission_id": str(mission_id or "") or None,
            "run_id": str(run_id or "") or None,
            "source_ids": [str(x) for x in (source_ids or []) if str(x)],
            "notes": str(notes or "")[:4000],
            "created_at": time.time(),
        }
        with self.lock:
            self.state["study_sessions"].append(row)
            self.state["study_sessions"] = self.state["study_sessions"][-10000:]
            self._save()
        if self.memory:
            self.memory.audit("rishi_curriculum_study", "recorded", f"{rid}:{unit['unit_id']}:{row['mission_id'] or '-'}")
        return {**row, "unit_progress": self.unit_progress(rid, unit["unit_id"])}

    def _last_session_at(self, rishi_id, unit_id=None):
        rid = str(rishi_id or "").strip().lower()
        uid = str(unit_id or "").strip().lower() if unit_id else None
        with self.lock:
            rows = [
                x for x in self.state.get("study_sessions") or []
                if x.get("rishi_id") == rid and (uid is None or x.get("unit_id") == uid)
            ]
        return max([float(x.get("created_at") or 0) for x in rows] or [0.0])

    def next_research_assignment(self, rishi_id=None):
        allowed = None
        if rishi_id:
            allowed = str(rishi_id or "").strip().lower()
            self.council.get(allowed)
        candidates = []
        with self.ledger.lock:
            snapshot = json.loads(json.dumps(self.ledger.state["rishis"]))
        for profile in self.council.list():
            rid = profile["id"]
            if allowed and rid != allowed:
                continue
            direct_total = len([
                x for x in snapshot[rid].get("findings") or []
                if x.get("role") in DIRECT_LEARNING_ROLES
            ])
            for stage in STAGES:
                unit = self._unit(rid, stage)
                progress = self.unit_progress(rid, unit["unit_id"])
                if progress["evidence_ready"]:
                    continue
                missing_direct = max(0, int(unit["assessment"]["min_direct_findings"]) - int(progress["direct_findings"]))
                missing_verified = max(0, int(unit["assessment"]["min_verified_findings"]) - int(progress["verified_findings"]))
                candidates.append((
                    direct_total,
                    int(stage["order"]),
                    progress["direct_findings"],
                    progress["verified_findings"],
                    self._last_session_at(rid, unit["unit_id"]),
                    rid,
                    unit,
                    progress,
                    missing_direct,
                    missing_verified,
                ))
                # Only the earliest evidence-incomplete stage for a Rishi competes
                # for today's queue, preserving progressive learning.
                break
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4], x[5]))
        _, _, _, _, _, rid, unit, progress, missing_direct, missing_verified = candidates[0]
        plan = self.source_plan(rid, unit["unit_id"], max_sources=8)
        return {
            "rishi_id": rid,
            "display_name": unit["rishi_name"],
            "role": unit["rishi_role"],
            "unit_id": unit["unit_id"],
            "stage": unit["stage"],
            "stage_label": unit["stage_label"],
            "subject": unit["subject"],
            "subjects": unit["subjects"],
            "objectives": unit["objectives"],
            "source_plan": plan,
            "progress": progress,
            "missing_direct_findings": missing_direct,
            "missing_verified_findings": missing_verified,
            "research_question": (
                f"Study {unit['subject']} at {unit['stage_label']} level for {unit['rishi_name']}. "
                "Use independent evidence where applicable, identify contradictions and limitations, "
                "and produce narrow claims suitable for Gautama review and Veda Vyasa provenance-preserving synthesis."
            ),
            "knowledge_track": "modern_science" if any(
                k in set(unit["source_kinds"]) for k in {"paper", "dataset", "technical-report", "standard", "patent"}
            ) else "general",
            "finding_count": direct_total if 'direct_total' in locals() else 0,
            "bootstrap_complete": all(
                any(f.get("role") in DIRECT_LEARNING_ROLES for f in row.get("findings") or [])
                for row in snapshot.values()
            ),
            "policy": "balanced permanent curriculum queue; evidence work precedes assessment, while assessment never upgrades BRAHMAGYAN claims",
        }

    def assessment_queue(self, rishi_id=None, limit=20):
        rid_filter = None
        if rishi_id:
            rid_filter = str(rishi_id or "").strip().lower()
            self.council.get(rid_filter)
        rows = []
        for profile in self.council.list():
            rid = profile["id"]
            if rid_filter and rid != rid_filter:
                continue
            for stage in STAGES:
                unit = self._unit(rid, stage)
                progress = self.unit_progress(rid, unit["unit_id"])
                if progress["evidence_ready"] and not progress["exam_passed"]:
                    rows.append({
                        "rishi_id": rid,
                        "display_name": profile["display_name"],
                        "unit_id": unit["unit_id"],
                        "stage": unit["stage"],
                        "subject": unit["subject"],
                        "exam_threshold": unit["assessment"]["exam_threshold"],
                        "required_reviewers": unit["assessment"]["required_reviewers"],
                        "progress": progress,
                    })
        rows.sort(key=lambda x: (STAGE_BY_ID[x["stage"]]["order"], x["rishi_id"]))
        return rows[:max(1, min(int(limit), 100))]

    def daily_queue(self, limit=12, rishi_id=None):
        limit = max(1, min(int(limit), 50))
        research = []
        # Build a balanced queue without mutating state by repeatedly choosing the
        # best eligible candidate while excluding already selected Rishis first.
        candidates = []
        wanted = str(rishi_id or "").strip().lower() if rishi_id else None
        for profile in self.council.list():
            if wanted and profile["id"] != wanted:
                continue
            assignment = self.next_research_assignment(profile["id"])
            if assignment:
                candidates.append(assignment)
        candidates.sort(key=lambda x: (
            int(x.get("progress", {}).get("direct_findings") or 0),
            STAGE_BY_ID.get(x.get("stage"), {}).get("order", 99),
            float(x.get("progress", {}).get("last_evidence_at") or 0),
            x.get("rishi_id") or "",
        ))
        research = candidates[:limit]
        return {
            "version": self.VERSION,
            "generated_at": time.time(),
            "research": research,
            "assessments": self.assessment_queue(wanted, limit=limit),
            "policy": "queue generation performs no network work and spends no money; live execution remains separately permission-gated",
        }

    def dashboard(self, queue_limit=12):
        rows = []
        total_units = 0
        evidence_ready = 0
        mastered = 0
        for profile in self.council.list():
            units = []
            for stage in STAGES:
                unit = self._unit(profile["id"], stage)
                progress = self.unit_progress(profile["id"], unit["unit_id"])
                units.append(progress)
                total_units += 1
                evidence_ready += int(bool(progress["evidence_ready"]))
                mastered += int(bool(progress["mastered"]))
            current = next((x for x in units if not x["evidence_ready"]), units[-1])
            rows.append({
                "rishi_id": profile["id"],
                "display_name": profile["display_name"],
                "current_stage": current["unit_id"].split(":", 1)[1],
                "research_ready_units": len([x for x in units if x["evidence_ready"]]),
                "mastered_units": len([x for x in units if x["mastered"]]),
                "total_units": len(units),
                "mastery_fraction": round(len([x for x in units if x["mastered"]]) / max(1, len(units)), 3),
            })
        return {
            "version": self.VERSION,
            "rishis": rows,
            "total_rishis": len(rows),
            "total_units": total_units,
            "research_ready_units": evidence_ready,
            "mastered_units": mastered,
            "pending_assessments": len(self.assessment_queue(limit=100)),
            "daily_queue": self.daily_queue(limit=queue_limit),
            "research_basis": list(CURRICULUM_RESEARCH_BASIS),
            "resident_workers": 0,
            "policy": "permanent curricula are state/planning only; no resident crawler or paid learning service is created",
        }


class CurriculumRishiLearningLedger(_BaseRishiLearningLedger):
    """Drop-in RishiLearningLedger with permanent curriculum capabilities.

    Keeping this as a subclass preserves every existing learning/collaboration API
    while giving the existing Orchestrator, background bootstrap path and HTTP
    read surfaces richer curriculum assignments automatically.
    """

    CURRICULUM_VERSION = CURRICULUM_VERSION

    def __init__(self, state_root, council, memory=None):
        super().__init__(state_root, council, memory)
        self.curriculum_academy = RishiCurriculumAcademy(
            Path(state_root) / "curriculum", council, self, memory
        )

    def curriculum(self, rishi_id, include_sources=False):
        return self.curriculum_academy.curriculum(rishi_id, include_sources=include_sources)

    def curriculum_dashboard(self, queue_limit=12):
        return self.curriculum_academy.dashboard(queue_limit=queue_limit)

    def curriculum_daily_queue(self, limit=12, rishi_id=None):
        return self.curriculum_academy.daily_queue(limit=limit, rishi_id=rishi_id)

    def curriculum_source_plan(self, rishi_id, unit_id, max_sources=10):
        return self.curriculum_academy.source_plan(rishi_id, unit_id, max_sources=max_sources)

    def curriculum_record_exam(self, rishi_id, unit_id, score, reviewers=None, evidence=None, notes=""):
        return self.curriculum_academy.record_exam(
            rishi_id, unit_id, score, reviewers=reviewers, evidence=evidence, notes=notes,
        )

    def curriculum_record_study(self, rishi_id, unit_id, **kwargs):
        return self.curriculum_academy.record_study_session(rishi_id, unit_id, **kwargs)

    def next_learning_assignment(self):
        assignment = self.curriculum_academy.next_research_assignment()
        return assignment if assignment is not None else super().next_learning_assignment()

    def bootstrap_status(self):
        out = super().bootstrap_status()
        # Preserve the legacy bootstrap meaning (at least one direct finding per
        # permanent Rishi) so existing startup behavior and tests stay compatible.
        out["curriculum"] = {
            "version": self.CURRICULUM_VERSION,
            "permanent": True,
            "next_assignment": self.curriculum_academy.next_research_assignment(),
            "pending_assessments": len(self.curriculum_academy.assessment_queue(limit=100)),
        }
        return out

    def profile(self, rishi_id, topic=None, limit=50):
        row = super().profile(rishi_id, topic, limit)
        row["curriculum"] = self.curriculum_academy.curriculum(rishi_id, include_sources=False)
        return row

    def dashboard(self, limit_findings=8):
        row = super().dashboard(limit_findings)
        row["curriculum"] = self.curriculum_academy.dashboard(queue_limit=12)
        return row

    def topic_matrix(self):
        row = super().topic_matrix()
        row["curriculum"] = {
            "version": self.CURRICULUM_VERSION,
            "stages": [
                {
                    "id": x["id"],
                    "label": x["label"],
                    "order": x["order"],
                    "min_findings": x["min_findings"],
                    "min_verified": x["min_verified"],
                    "exam_threshold": x["exam_threshold"],
                }
                for x in STAGES
            ],
            "permanent": True,
            "unit_count": len(self.council.list()) * len(STAGES),
            "policy": "Foundation -> Core -> Advanced -> Frontier -> Synthesis; evidence and assessment stay separate",
        }
        return row
