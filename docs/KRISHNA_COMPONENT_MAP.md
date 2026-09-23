# KRISHNA Component Map

This document is the human-readable ownership map for KRISHNA. It explains where a concept, agent, bot or AI capability belongs. KRISHNA remains the top-level authority; components below it are specialist runtimes, not independent competing assistants.

## 1. KRISHNA — top-level orchestrator

**Role:** owner-facing autonomous supervisor and system identity.

KRISHNA owns the overall goal, project context, memory, model routing and handoff between specialist systems. It delegates consequential execution through Sudarshan and preserves runtime/product truth.

Key concepts:
- local-first orchestration;
- project/chat context;
- autonomous supervision;
- commitment/task continuity;
- model routing and privacy policy;
- product/runtime integrity.

## 2. Sudarshan — action and execution authority

**Role:** permissioned control plane for actions/jobs.

Main components:
- Shared Action Bus;
- Agent Runtime;
- Job Runtime + durable queue;
- Mission Engine;
- Permission Runtime;
- Resource locks/gates;
- unified dispatch;
- MCP/A2A protocol boundary;
- independent verification and rollback/promotion gates.

Use Sudarshan whenever an agent wants to move from "I think/recommend" to "execute/modify/send/control".

## 3. Garudanetra — canonical browser/computer fabric

**Canonical engine:** Playwright.

Core browser capabilities:
- private browser sessions;
- task-memory sessions;
- approval-gated persistent workspaces;
- CDP screencast/live frames;
- semantic element observer + point-to-element;
- console/network/download evidence;
- action recording;
- approval-gated replay;
- recovery adapters;
- UI Guardian and developer verification bridge.

### Garudanetra Research Fabric v2

JetBot-inspired concepts adapted into Garudanetra:
- durable research mission workspace;
- reusable browser research skill registry;
- skill lifecycle/quality tracking;
- specialist research scout swarm;
- duplicate-launch suppression and circuit breaker;
- evidence ingestion with provenance/stance/quality;
- contradiction and failed-replication preservation;
- Rishi/Shishya/LAB BOT/Gyan-candidate handoff.

Garudanetra research specialist agents:
- **paper-scout** — scientific papers/reviews/replications;
- **github-scout** — implementations, issues, failure cases and reproducible code;
- **patent-scout** — patents and prior art;
- **dataset-scout** — datasets and benchmarks;
- **standards-scout** — standards, metrology and authoritative technical guidance;
- **contradiction-scout** — negative results, failed replications and alternative explanations.

Built-in research skills:
- `research.paper.search`
- `research.github.inspect`
- `research.patent.search`
- `research.dataset.find`
- `research.standard.find`
- `research.claim.verify`
- `research.contradiction.find`
- `research.lab.handoff`

Policy:
- JetBot is inspiration/candidate capability only; it is not a second browser authority.
- Playwright remains canonical.
- Distilled skills require explicit owner approval before promotion.
- Web research is candidate evidence until independent verification/BRAHMA QC.

Optional/candidate browser adapters remain behind Garudanetra:
Browser Harness, agent-browser, BrowserCode, OpenDevBrowser, Rustwright, Lucarne, Promptwright, Skyvern, rrweb, Browser Use, Cereon extension bridge and vision recovery.

## 4. Garuda — broad research/evidence scout

**Role:** research discovery outside a live browser-control session.

Garuda performs broad evidence scouting and can now hand richer browser work to Garudanetra Research Fabric. Garuda discovers; Garudanetra interacts with browser pages and captures browser evidence.

## 5. BRAHMAGYAN — deep learning and Rishi council

**Role:** domain-specialist learning, synthesis and research.

Main components:
- Rishi Council;
- temporary Shishya research trees;
- Rishi learning charters;
- collaboration/debate;
- science/frontier research;
- dual-source evidence discipline where classical sources are relevant.

Examples of Rishi specializations:
- **Veda Vyasa** — knowledge architecture and synthesis;
- **Vashistha** — ethics/governance;
- **Vishwamitra** — AI, robotics, quantum/frontier engineering;
- **Sushruta** — surgery/biomedical engineering;
- **Kashyapa** — biology/genetics;
- **Atri** — astronomy/remote sensing;
- **Gautama** — logic, statistics, causality, replication and evidence grading;
- **Jamadagni** — defensive security/resilience;
- **Bharadvaja** — experimental design/testing;
- **Kanada** — physics, chemistry, materials and nanoscience;
- **Kapila** — systems/cognition;
- **Patanjali** — attention/human performance;
- **Yajnavalkya** — epistemology/debate;
- **Agastya** — environment/culture/knowledge transmission;
- **Charaka** — internal/preventive medicine;
- **Panini** — linguistics/NLP;
- **Aryabhata/Brahmagupta/Bhaskaracharya/Madhava** — mathematics/scientific computation;
- **Varahamihira** — earth/atmospheric sciences;
- **Dhanvantari** — therapeutics/drug research;
- **Nagarjuna** — chemistry/process/materials;
- **Chanakya** — operations/economics/strategy;
- **Baudhayana** — geometry/civil/structural engineering.

These are KRISHNA design roles inspired by traditional/historical associations; modern scientific claims still require modern evidence.

## 6. BRAHMA BOT — learning governor/QC

**Role:** decides what is worth learning and whether candidate knowledge is mature enough for trusted memory.

BRAHMA:
- routes topics to Rishis;
- grades evidence/provenance;
- tracks contradictions;
- requires stronger learning where needed;
- gates promotion into Gyan-Bhandar.

## 7. Gyan-Bhandar — trusted knowledge store

**Role:** evidence/knowledge memory with provenance, maturity and supersession.

Concepts:
- candidate vs verified knowledge;
- provenance;
- supersession/version history;
- encrypted storage;
- retrieval/context compilation;
- approval-gated knowledge promotion.

## 7A. KRISHNA Cognitive Brain — associative knowledge activation

**Role:** connect concepts across trusted memory so KRISHNA can recall related knowledge, expose missing branches and route only genuine gaps to research.

Core behavior:
- persistent concept graph above Gyan-Bhandar;
- query-time associative activation and multi-hop concept expansion;
- Hybrid RAG expansion using related concepts rather than keyword-only retrieval;
- memory-coverage checks before fresh research;
- knowledge-gap packets with a suggested Rishi;
- explicit provenance/confidence on concept relationships;
- safe cross-domain comparison without silently asserting equivalence.

Example:
- Anu activates Paramanu, modern Atom comparisons and then Molecule through linked concepts.
- Classical Anu/Paramanu remain on a **classical** evidence track.
- Modern Atom/Molecule remain on a **modern_science** evidence track.
- Cross-track links are comparisons, not claims that the concepts are identical.

Gyan-Bhandar remains the trusted factual memory, BRAHMA remains the promotion/QC gate, and Rishis remain the research owners. The Cognitive Brain is the associative activation layer between them.

## 8. HAWKEYE — live perception/evidence fusion

**Role:** coordinate measurable live-world evidence.

Specialist lanes:
- **PERCEPTION** — what is actually seen/heard;
- **PHYSIO** — measurable physical signals;
- **BEHAVIOR** — observable behavior only;
- **TEMPORAL** — what changed over time;
- **DIAGNOSTIC** — fault hypotheses and next measurements;
- **REASONER** — fuse multiple evidence lanes and expose contradictions.

Sudarshan verifies consequential conclusions/actions.

## 9. BHOOMIPUTRA — field/geospatial/structure specialist

**Role:** field perception, sites, terrain, structures and geospatial measurements.

Capabilities include:
- live field sessions;
- GNSS/RTK/depth adapter boundaries;
- photogrammetry/geo planning;
- quarry/building/site evidence;
- coordinate and measurement provenance.

Real field hardware stays hardware-unverified until connected and accepted.

## 10. HAWKEYE Diagnostic adapters

**Role:** read-only technical evidence.

Current domains:
- electronics measurements;
- receive-only vehicle OBD/CAN/J1939 evidence;
- acoustic feature measurements.

They do not silently transmit/program/control equipment.

## 11. LAB BOT — practical experiment bridge

**Role:** turn a Rishi hypothesis into a machine-checkable experiment.

Flow:
Rishi -> LAB BOT -> design completeness -> simulation/dry-run -> reviewed adapter -> measurement -> replication -> BRAHMA/Gyan.

Modes:
- simulation;
- measurement;
- fabrication;
- wet lab.

Physical execution requires registered adapters and review/approval gates.

## 12. Quantum Lab + Nano Lab

**Owner:** LAB BOT.

Quantum Lab:
- bounded local state-vector simulation;
- quantum research plans;
- classical-baseline requirements;
- optional Qiskit/PennyLane provider detection;
- quantum sensing/QML/chemistry planning.

Nano Lab:
- nanoscale geometry;
- surface-to-volume analysis;
- nanomaterials/nanoelectronics/nanophotonics research plans;
- optional pymatgen/ASE provider detection.

Joint bridge:
- quantum materials;
- quantum dots;
- spin defects;
- nanophotonics;
- nanoscale quantum sensing;
- mesoscopic devices;
- molecular/material simulation.

Real QPUs and nanofabrication are not considered available until physically connected and verified.

## 13. KABACH — security/privacy guardian

**Role:** defensive security and privacy boundary.

Concepts:
- project protection registry;
- privacy policy;
- defensive SOC/remediation flow;
- sensitive input redaction;
- dependency/security auditing;
- protected-project mutation gate;
- private remote boundary.

Secrets are never treated as learning material.

## 14. NARAD — automation/workflow runtime

**Role:** durable typed workflows and provider connectors.

Concepts:
- DAG workflows;
- scheduler;
- resource/concurrency gate;
- connector/provider hub;
- messaging/Google connectors;
- n8n as external connector only.

Sudarshan remains execution authority; NARAD does not bypass permissions.

## 15. Developer + Project Perfection

**Role:** bounded software creation/repair and verification.

Components:
- developer agent;
- shadow/candidate workspace;
- tests/build/lint;
- recursive crawl;
- accessibility/performance/chaos checks;
- visual editor;
- Design Studio;
- post-apply verification;
- rollback/promotion.

## 16. UI Guardian

**Role:** objective UI verification.

Checks:
- viewport matrix;
- interactive controls;
- visual/semantic usability contracts;
- browser evidence;
- regression state.

## 17. Vishvakarma design team

**Role:** design specialist layer used by Sudarshan/Project Perfection.

Purpose:
- generate design candidates;
- compare rendered options;
- preserve selected design intent;
- hand implementation to bounded developer/project pipelines.

## 18. Model/AI layer

**Local-first authority:** Model Router/Gateway.

Concepts:
- Ollama local models;
- GPT4All/local provider boundary;
- qwen2.5vl local multimodal vision where installed;
- encrypted cloud credentials;
- OpenAI-compatible optional cloud profiles;
- free-only/no-silent-paid-fallback policy;
- local_only/restricted privacy rules.

Models provide inference; they do not become system authority.

## 19. Mobile Edge

**Role:** secure conversation/evidence edge.

Concepts:
- canonical `mobile_v3` Android source;
- conversation/voice interface;
- evidence curator;
- encrypted sync;
- background sync;
- offline perception;
- wake service;
- paired-device boundary.

Legacy PC companion remains compatibility-only.

## 20. Voice + Avatar

Voice:
- Krishna wake word;
- native voice boundary;
- Odia/Hindi target support;
- local owner/speaker-verification boundary.

Avatar:
- child Krishna visual identity;
- TalkingHead;
- model-viewer;
- HeadAudio;
- MotionEngine;
- state machine.

The production skeletal/facial/viseme GLB asset remains a separate incomplete physical/asset task until the rig passes audit.

## Authority summary

```
USER
  |
KRISHNA
  |
SUDARSHAN  ------------------------------ execution / permission / verification
  |
  +-- GARUDANETRA ----------------------- browser/computer + research fabric
  |     +-- paper/github/patent/dataset/standards/contradiction scouts
  |
  +-- GARUDA ---------------------------- broad research discovery
  |
  +-- BRAHMAGYAN ------------------------ Rishi + Shishya research
  |     +-- BRAHMA BOT ------------------ QC/learning governor
  |     +-- GYAN-BHANDAR ---------------- trusted knowledge
  |     +-- COGNITIVE BRAIN ------------- associative concept activation
  |
  +-- HAWKEYE --------------------------- live evidence fusion
  |     +-- BHOOMIPUTRA ----------------- field/geospatial
  |     +-- DIAGNOSTIC ------------------ electronics/vehicle/acoustics
  |
  +-- LAB BOT --------------------------- experiments
  |     +-- QUANTUM LAB
  |     +-- NANO LAB
  |
  +-- KABACH ---------------------------- security/privacy
  |
  +-- NARAD ----------------------------- workflows/connectors
  |
  +-- DEVELOPER / PROJECT PERFECTION ---- software creation/verification
  |     +-- UI GUARDIAN
  |     +-- VISHVAKARMA DESIGN TEAM
  |
  +-- MODEL ROUTER/GATEWAY -------------- local/cloud inference providers
  |
  +-- MOBILE EDGE ----------------------- secure conversation/evidence edge
```

No subordinate component above is allowed to silently become a second KRISHNA or bypass Sudarshan for consequential actions.
