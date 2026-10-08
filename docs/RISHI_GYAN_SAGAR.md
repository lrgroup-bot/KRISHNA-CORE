# RISHI GYAN-SAGAR

Status: implemented source/rights fabric on `feature/rishi-gyan-sagar`.

## Purpose

RISHI GYAN-SAGAR is BRAHMAGYAN's source-discovery and rights-control layer. It gives the Rishi Council broad lawful access to books, papers, theses, classical texts, courses, patents, technical standards, source code, models and datasets without turning external websites into KRISHNA authorities.

The implementation is deliberately split into two capabilities:

- `knowledge.research` -> `rishi-gyan-sagar`
- `knowledge.rights` -> `rishi-rights-gate`

Registration creates no resident crawler and no background network load. Network/browser execution remains behind KRISHNA's existing permission, browser, connector and Shared Action Bus boundaries.

## Non-negotiable rights model

Access is not one Boolean. Every item is evaluated separately for:

1. **READ** - a Rishi may inspect the material for a research question.
2. **INDEX** - KRISHNA may retain factual metadata, citation/provenance and a searchable reference.
3. **ARCHIVE** - KRISHNA may retain a local full-text/content copy only when source/item rights permit it.
4. **TRAIN** - content may enter a model-training corpus only when rights, provenance and an immutable checksum permit it.

Unknown rights never auto-upgrade from READ/INDEX to ARCHIVE/TRAIN. CC0/public-domain and compatible CC licences can be handled automatically within their obligations. Non-commercial and no-derivatives licences are conservative/review-gated in LR's commercial context. A software repository licence is not treated as automatic permission to train a model on the code.

## Core source tiers

### P0 - foundational Rishi knowledge

- OpenAlex - scholarly discovery graph.
- Crossref - DOI metadata, funding, licence and post-publication/retraction context.
- Unpaywall - DOI to lawful OA-location resolution; not search.
- CORE - open-research/full-text resolver.
- DOAJ - OA journal/article quality and metadata layer.
- DOAB + OAPEN - open scholarly books and book metadata/full-text resolution.
- Europe PMC + PubMed Central - biomedical discovery and licence-aware full text.
- Shodhganga - Indian doctoral theses; browser/repository access until an official machine interface is runtime-verified.
- SARIT + Digital Corpus of Sanskrit - machine-readable Indic/classical and linguistic research.
- NPTEL + SWAYAM - Indian engineering/science/education curricula.
- RFC Editor + W3C + NIST - normative and government technical knowledge.
- GitHub + Software Heritage - implementation evidence and software provenance.

### P1 - specialist/frontier expansion

- arXiv - frontier preprints, always explicitly labelled as preprints.
- OpenReview - paper/review/discussion context for modern AI/ML research.
- EPO Open Patent Services - patents, claims, prior art and legal status; never cross the free threshold automatically.
- IETF Datatracker - emerging standards and working-group material.
- Hugging Face Hub - models/datasets/cards; every artifact remains licence/model-card/dataset-card gated before download/execution.
- Project Gutenberg, Open Library, Internet Archive and Wayback - books, catalogues and historical evidence.
- Muktabodha, GRETIL and IIT Kanpur Gita Supersite - Indic/classical texts and commentaries with collection/item-specific rights.

### P2 - supplementary curriculum/discovery

- Google Books - book discovery/availability.
- MIT OpenCourseWare - curriculum source with course-material licence restrictions preserved.

## Verified 2026 implementation facts

- Unpaywall retired its text-search endpoint on 18 September 2026. OpenAlex is used for scholarly discovery; Unpaywall remains a DOI OA resolver.
- Crossref supports unauthenticated public access and a polite pool using `mailto`; KRISHNA must cache and respect rate/concurrency limits.
- DOAJ article/journal metadata is available through API/OAI-PMH and its metadata is CC0.
- DOAB exposes OAI-PMH and CC0 metadata; each linked book keeps its own content licence.
- OAPEN exposes OAI-PMH and downloadable metadata formats.
- PMC automated full-text retrieval must use official PMC services, and not every PMC article is reusable.
- RFC Editor explicitly supports local mirrors via rsync.
- EPO OPS allows a bounded free tier and then paid usage. KRISHNA's zero-spend policy blocks automatic paid escalation.
- Software Heritage's public API is pointwise; mass extraction is not permitted through that API, and underlying code licences still govern reuse.
- Open Library asks applications to use low-volume identified API calls and monthly dumps for bulk metadata instead of using the API as a high-traffic backend.
- Hugging Face model/dataset cards expose licence metadata, but an artifact is never trusted solely because a licence string exists; card limitations and repository files also require review.

## Research flow

```text
Rishi question
    |
    v
RISHI GYAN-SAGAR source plan
    |
    +--> discovery sources
    +--> metadata/citation verification
    +--> lawful full-text resolver
    +--> standards/patents/code when relevant
    +--> classical/modern tracks kept distinct
    |
    v
Gautama evidence challenge
    |
    v
Veda Vyasa synthesis/provenance compilation
    |
    v
BRAHMAGYAN maturity gates
    |
    v
RISHI RIGHTS GATE
 READ | INDEX | ARCHIVE | TRAIN
    |
    v
GYAN-BHANDAR proposal/approval
```

## Source-routing examples

- Sushruta/Charaka: Europe PMC, PMC, OpenAlex, Crossref, DOAJ; classical Ayurveda remains separately labelled through SARIT and related corpora.
- Panini/Agastya: SARIT, DCS, GRETIL, Muktabodha, classical commentary sources plus modern linguistic research.
- Vishwamitra/Vishvakarma: OpenAlex, arXiv/OpenReview, EPO patents, NIST/W3C/IETF/RFC, GitHub, Software Heritage and Hugging Face.
- Kanada/Atri: scholarly graph + arXiv + NIST + standards/datasets appropriate to the physical/observational question.
- Bharadvaja: NPTEL/SWAYAM/OCW for curriculum, papers for evidence, code/datasets for reproducibility.
- Gautama: Crossref/retraction context, source-family independence, contradictions, provenance and citation verification.

## Safety and quality rules

- Sci-Hub and disposable-email services are not approved Rishi knowledge sources.
- Browser-only sources stay browser-only until an official machine interface and terms are verified.
- Preprints never silently become peer-reviewed evidence.
- Classical/traditional claims and modern scientific/clinical claims stay on separate evidence tracks.
- Retractions remain visible as historical/contradiction evidence and never count as normal support.
- No source can spend money automatically.
- No model/dataset/code artifact can execute merely because it was discovered.
- Provenance, item licence and checksum are required before training-corpus promotion.

## Code

- `core/krishna_core/rishi_gyan_sagar.py` - source catalog, research routing, request planning, rights decisions and ingestion gate.
- `core/krishna_core/capability_fabric.py` - non-resident `knowledge.research` and `knowledge.rights` capability registration.
- `core/tests/test_rishi_gyan_sagar.py` - source, routing, zero-spend and rights regression coverage.
