# KRISHNA Cognitive Brain

## Purpose

KRISHNA Cognitive Brain is the associative-memory and gap-directed learning layer above BRAHMA BOT, the Rishi Council, BRAHMAGYAN and Gyan-Bhandar.

It is inspired by the useful software-design metaphor behind films such as *Lucy*: progressively better integration of memory, association, perception, reasoning and learning. It does **not** implement or claim a biological "brain percentage", superhuman neuroscience, consciousness, telepathy, or other fictional abilities.

## Core behavior

When a Rishi studies a topic, KRISHNA stores more than the literal keyword. It may store:

- the concept itself;
- aliases and alternate names;
- typed relationships to related concepts;
- knowledge/evidence track;
- Rishi provenance;
- confidence, maturity and evidence status;
- links to further concepts discovered during BRAHMAGYAN research.

Example:

```
Anu
 ├─ related_to → Paramanu
 ├─ compared_with → Atom
 │                   └─ combines_to_form → Molecule
 └─ ...
```

If a later query is `Molecule`, spreading activation can reach `Atom` and then the previously learned `Anu` neighborhood. KRISHNA then retrieves relevant Rishi findings before deciding that new research is required.

Association strength is a retrieval priority signal, **not proof**.

## Progressive cognition levels

- **C0 Capture** — stores bounded concept observations.
- **C1 Recall** — resolves concepts and aliases.
- **C2 Association** — activates linked concepts.
- **C3 Gap-aware** — identifies concepts that are connected but weakly supported.
- **C4 Cross-domain** — connects independently sourced domains and evidence tracks.
- **C5 Metacognitive** — keeps provenance, maturity, uncertainty and contradiction boundaries visible.

These are KRISHNA software-capability stages, not percentages of human brain usage.

## Research-first retrieval

The query path is:

```
User question
  ↓
Cognitive Brain concept resolution
  ↓
Associative activation
  ↓
BRAHMA retrieves relevant Rishi ledgers
  ↓
Supported findings reused
  ↓
Missing/weak branches become explicit research gaps
  ↓
Bounded BRAHMAGYAN missions are created
  ↓
Existing Sudarshan / NARAD / Rishi live-research paths perform permitted research
  ↓
Verified connected findings are fed back into the graph
```

Repeated searches do not create duplicate study missions for the same project/topic.

## BRAHMAGYAN integration

Every BRAHMAGYAN claim seeds its mission topic into the concept brain.

When a claim reaches a connected state and carries `connections`, those relationships are ingested into associative memory with claim/mission provenance. This means the concept graph grows from verified research rather than from keyword guessing alone.

Rishi or agent code can also submit structured concept neighborhoods through the shared action bus.

## Shared actions

- `brahma.cognitive.status`
- `brahma.cognitive.query`
- `brahma.cognitive.ingest`
- `brahma.cognitive.study`

`brahma.cognitive.study` creates bounded, deduplicated BRAHMAGYAN missions for actual knowledge gaps. Network/model execution still remains behind Sudarshan permissions and the existing research runtime.

## Evidence-track rule

Modern science and Vedic/classical material stay independently sourced.

A relationship such as:

```
Anu --compared_with--> Atom
```

is allowed when evidence warrants comparison.

An unsupported relationship such as:

```
Anu --equivalent_to--> Atom
```

is rejected across modern-science and Vedic/classical tracks. Similar terminology or philosophical resemblance is never automatically converted into scientific equivalence.

## Privacy

Persisted concept labels, aliases and provenance pass through KABACH's existing privacy sanitizer. Tokens, passwords, API keys, credentials and similar sensitive strings are redacted before the cognitive graph is written to disk.

## Authority boundaries

Cognitive Brain does not replace:

- **KRISHNA** — overall supervisor.
- **Sudarshan** — action/permission authority.
- **BRAHMA BOT** — learning governor and Gyan QC.
- **Rishi Council** — specialist scholarship.
- **BRAHMAGYAN** — evidence maturation and deep research protocol.
- **Gyan-Bhandar** — trusted long-term knowledge store.
- **Garudanetra/Garuda** — external research and browser/evidence infrastructure.

The Cognitive Brain decides what existing knowledge should become active together and where the knowledge graph has holes. It does not declare unverified associations true.
