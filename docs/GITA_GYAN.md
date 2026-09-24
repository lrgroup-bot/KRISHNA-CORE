# KRISHNA GITA-GYAN

GITA-GYAN is KRISHNA's local-first Bhagavad Gita learning runtime. It is part of the existing KRISHNA avatar/conversation system; it is not a separate application or sidebar product.

## Behaviour

- One verse is selected per local calendar day and is not repeated until the bundled edition has been traversed.
- The same day's lesson remains stable across repeated requests.
- The canonical Sanskrit, transliteration and bundled public-domain English translation are immutable source data.
- Odia/Hindi explanations are derived teaching aids and are cached separately under KRISHNA runtime state.
- KRISHNA uses the existing WISDOM avatar state for Gita teaching.
- Sanskrit recitation uses the configured local Hindi Indic-TTS Devanagari voice path. This is a pronunciation aid, not a Vedic-recitation verifier.
- The explanation uses the user's preferred Odia or Hindi local Indic-TTS voice when configured.
- Follow-up questions are answered by the local model and retained with learning progress.
- Every seventh delivered lesson includes a seven-lesson revision payload.
- Daily events are queued durably for every paired mobile device, so a temporarily offline phone can receive the lesson when it resumes its KRISHNA session.
- Desktop and mobile keep the existing conversation-first UI. No new main-menu item is required.

## Natural conversation examples

- Krishna, today's Gita.
- Krishna, Odia re deeply bujhaa.
- Krishna, Hindi mein Gita samjhao.
- Bhagavad Gita chapter 2 shloka 47 deeply explain.
- Ei shloka business re kemiti apply haba?
- Is shlok ka matlab meri daily life mein kaise use karun?
- Yesterday Gita revise kara.

KRISHNA's normal /api/core/chat route recognizes explicit Gita/Bhagavad-Gita/shloka requests and keeps those messages in the same persistent chat.

## Local-first source boundary

The bundled file is:

core/krishna_core/data/bhagavad_gita_public_domain.json

Its source metadata identifies Shri Purohit Swami (1935) as the primary public-domain English translator. The source dataset contains 701 numbered entries. Verse-count conventions can differ by edition, so KRISHNA preserves the source numbering rather than silently renumbering the scripture.

Canonical source fields are never overwritten by model output. Generated teaching content is stored separately in:

<runtime>/.krishna_state/gita-gyan/explanations/

Learning progress is stored in:

<runtime>/.krishna_state/gita-gyan/progress.json

If progress JSON is unreadable, GITA-GYAN refuses to overwrite it.

## Interpretation integrity

The local explainer is instructed to distinguish source text from interpretation and modern practical application. It must not attribute a position to a named philosophical school unless a source for that school is available. Without sourced school-specific commentary, KRISHNA may present clearly labelled textual, devotional, action-oriented and contemplative lenses only as learning perspectives.

If the local model is unavailable, the canonical Sanskrit/transliteration/public-domain English remains available and the API marks the generated explanation as degraded instead of inventing a translation.

## Runtime configuration

Environment variables:

- KRISHNA_GITA_DAILY_ENABLED=1
- KRISHNA_GITA_DAILY_TIME=07:30
- KRISHNA_GITA_POLL_SECONDS=30
- KRISHNA_GITA_LANGUAGE=or
- KRISHNA_GITA_DEEP=1
- KRISHNA_TIMEZONE=Asia/Kolkata

Supported teaching languages are or (Odia) and hi (Hindi). The daily time is interpreted in KRISHNA_TIMEZONE.

## HTTP API

Read endpoints:

- GET /api/gita/status
- GET /api/gita/progress
- GET /api/gita/today?language=or&deep=1
- GET /api/gita/verse?chapter=2&verse=47&language=hi&deep=1
- GET /api/gita/revision?language=or&limit=7

Learning/action endpoints:

- POST /api/gita/preference
- POST /api/gita/lesson
- POST /api/gita/understood
- POST /api/gita/question
- POST /api/gita/speak
- POST /api/gita/command

Paired mobile devices are restricted to the explicit private-network mobile allowlist. Audio is fetched through authenticated /api/voice/audio IDs; the mobile bridge does not receive KRISHNA PC filesystem paths.

## Verification

Unit tests cover daily sequencing, same-day stability, no-repeat delivery, source/commentary separation, local explanation caching, questions/progress, command parsing, and once-per-day timezone-aware scheduling.

HTTP tests disable the background daily scheduler and validate GITA-GYAN status/progress/verse contracts without requiring Ollama or TTS. This keeps CI deterministic while production keeps the daily scheduler enabled by default.
