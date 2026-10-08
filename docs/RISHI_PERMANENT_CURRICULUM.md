# BRAHMAGYAN Permanent Rishi Curriculum

Status: implemented on `feature/rishi-permanent-curriculum`.

## Purpose

The Rishi Council already has permanent subject charters and evidence-backed learning ledgers. The curriculum layer turns those charters into progressive, auditable learning programs without creating a second research authority or a resident crawler.

Every permanent Rishi receives five stages:

1. **Foundation** — vocabulary, scope, canonical models, measurement language and authoritative source families.
2. **Core** — mechanisms, methods, standard practices, basic calculations/interpretation and source independence.
3. **Advanced** — competing models, uncertainty, edge cases, failure modes and theory-to-evidence links.
4. **Frontier** — recent research, standards, patents, datasets, tools, contradictions and falsifiable next questions.
5. **Synthesis** — provenance-preserving knowledge maps, supported/contested/unknown separation and council handoff.

With 31 permanent council profiles this produces 155 stable curriculum units.

## Structural research basis

The external educational frameworks below inform curriculum structure only. They do not become evidence for Rishi subject claims.

- National Medical Commission revised CBME curriculum (12 September 2024): competency-based progression, integrated learning/assessment, knowledge plus skills/attitudes/values, and clinical exposure for medical training.
- AICTE model engineering curricula: staged basic science, engineering science, professional core, practical/laboratory work and applied/design work.
- Central Sanskrit University current syllabus framework: discipline-specific classical study with multidisciplinary/modern components.

KRISHNA adapts those structural ideas to machine learning/research governance rather than pretending a Rishi has earned a human academic degree.

## Evidence and assessment are separate

An exam cannot manufacture evidence.

Each stage has:

- minimum direct Rishi findings;
- minimum verified findings where required;
- an assessment threshold;
- required council reviewers;
- prerequisite-stage checks for mastery.

A unit may therefore be `assessment_passed_evidence_pending`: the Rishi understood the assessment but still lacks enough verified evidence to call the unit mastered.

Gautama is the default evidence/assessment reviewer. Synthesis additionally requires Veda Vyasa. BRAHMAGYAN claim maturity remains a separate system and is never upgraded merely because a curriculum assessment passed.

## Source planning

Every unit obtains a non-executing source plan from the same source catalogs used by RISHI GYAN-SAGAR:

- `rishi-gyan-sagar`
- `rishi-deep-sources`

The plan selects appropriate papers, books, classical corpora, datasets, standards, patents, software archives or technical repositories based on Rishi + subject + stage. It performs no network access itself.

Rights remain separated as:

`READ != INDEX != ARCHIVE != TRAIN`

Source discovery never grants reuse or model-training rights.

## Daily queue

The academy produces two bounded queues:

- **research queue** — earliest evidence-incomplete stage for each Rishi, balanced toward the least-trained council members;
- **assessment queue** — units whose evidence requirement is ready but assessment is still pending.

Queue generation performs no network work and starts no resident worker. Existing KRISHNA research execution remains behind Garuda, the Shared Action Bus, browser/connector permissions and zero-spend controls.

## Specialist examples

### Sushruta

Foundation: anatomy, physiology, pathology, clinical research  
Core: diagnostics, surgery, medical devices, medical imaging  
Advanced: biomedical engineering, biomechanics, biomaterials, clinical engineering  
Frontier: neural engineering, regenerative medicine, tissue engineering, medical AI  
Synthesis: patient safety, evidence translation, device lifecycle, clinical decision support

### Kanada

Foundation: mechanics, thermodynamics, electromagnetism, measurement  
Core: atomic/molecular science, chemistry, materials  
Advanced: condensed matter, physical properties, metrology  
Frontier: nanoscience, emerging materials, new states of matter  
Synthesis: physical models, uncertainty budgets and model/evidence reconciliation

### Panini

Foundation: Sanskrit, phonetics, grammar, morphology  
Core: syntax, semantics, textual criticism, Indian languages  
Advanced: formal grammar, parsing, translation, corpus linguistics  
Frontier: NLP, computational linguistics, language models, multilingual reasoning  
Synthesis: high-precision translation, philological provenance and machine-readable grammar

### Gautama

Foundation: logic, epistemology, probability, statistics  
Core: causality, research methodology, source independence, argument analysis  
Advanced: bias, replication, evidence grading, fact checking  
Frontier: meta-science, causal identification, replication failure, measurement error  
Synthesis: falsification, evidence audit, uncertainty calibration and false-consensus detection

## Runtime integration

`CurriculumRishiLearningLedger` is a strict subclass of the existing `RishiLearningLedger`. KRISHNA activates it at package initialization before the Orchestrator imports the ledger. This means existing code continues to use one ledger and gains:

- `curriculum(rishi_id)`
- `curriculum_dashboard()`
- `curriculum_daily_queue()`
- `curriculum_source_plan()`
- `curriculum_record_exam()`
- `curriculum_record_study()`

Existing `profile`, `dashboard`, `topic_matrix`, `bootstrap_status`, and `next_learning_assignment` remain compatible and now expose/use curriculum information.

No new resident service, model process, crawler or paid dependency is introduced.
