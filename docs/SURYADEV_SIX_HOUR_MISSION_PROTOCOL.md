# SURYADEV <-> KRISHNA: six-hour renewal protocol (v1, opt-in)

## What is implemented
- SURYADEV v6.4 creates a durable low-water request with desired_hours=6
  when fewer than three executable jobs remain. HTTP 429-paused YouTube is
  excluded. Neither requests nor 6-hour timers prove learning occurred.
- KRISHNA reuses the existing SuryadevAgent, existing owner-paired device
  verification, and existing BRAHMA/Rishi bundle-ACK authority.
- Core `SuryadevMissionBacklog` maintains up to TWO prepared six-hour
  research packets from an **operator-supplied approved catalogue**. An
  unknown or exhausted catalogue produces `no_approved_work`.
- Core paired endpoints: POST `/api/suryadev/mission/request` and
  POST `/api/suryadev/mission/ack`. A paired device ID must start with
  `suryadev-`. All other public/unauthorized requests are rejected by
  existing server/pairing policy.
- Opt-in outbound client `suryadev_krishna_mission.py` uses a pinned TLS
  leaf cert, private IPv4 origin, a separate 48-256-character credential
  file, a bounded JSON response and no redirect. It never sends bearer
  credentials before TLS pin verification.
- The laptop queues only exact URLs already present in its
  `learning-plan.json.approved_urls`, still subject to
  `max_queued`, `max_new_per_cycle`, public-URL validation and SQLite
  dedup. Even trusted Core cannot expand laptop source permission by adding
  another URL on the same host.
- A persisted local receipt plus a paired Core ACK is required before the
  local renewal flag becomes `krishna_assignment_acknowledged=True`.
  This indicates only **assignment delivery**, not a completed six-hour
  session, acquired evidence or BRAHMAGYAN learning acceptance. The
  existing learning-bundle channel remains separate.

## Owner-approval prerequisites

1. Review `core/suryadev-approved-curriculum.example.json`; it contains
   three illustrative real official-website sources, NOT an installed
   approval. Copy reviewed content to the KRISHNA SuryadevAgent state root
   under `mission-authority/approved-curriculum.json`. The Core-side
   `SuryadevAgent.status().mission_backlog` should then show
   `prepared=2`. The Core does not auto-create a catalogue.
2. Separately, approve the *exact same desired URLs* in the laptop's
   `D:\Work\SURYADEV-DATA\learning-plan.json` under `approved_urls`.
   Back it up first, preserve its existing feeds/limits/URLs, and keep
   matching hostnames in `allowed_source_hosts`. Do not delete SQLite
   findings, existing lock files, or source policy.
3. Use the **already-authorized Core pairing process** for a device ID
   beginning with `suryadev-`. Pairing/review takes place on the main Core
   machine; a `/health` response or LAN discovery is never pairing.
4. Set up a genuine HTTPS KRISHNA endpoint with a verified, owner-controlled
   certificate, for example via an authorized TLS proxy; the ordinary
   `http://...:8766` listener is NOT automatically HTTPS. Do not send the
   paired device token to plain HTTP.
5. In a private file on the laptop, configure a copy of
   `standalone/suryadev/krishna-mission-connection.example.json` with the
   actual HTTPS private IPv4 origin, SHA-256 leaf certificate fingerprint,
   approved paired device ID, and credential file path. Keep secrets out of
   Git and dashboard settings. The sample fingerprint deliberately cannot
   pass validation.

Only after the normal dashboard and worker tests pass, stop the existing
worker and dashboard in their own PowerShell terminals (Ctrl+C), update the
feature branch and run the guarded installer. Start exactly one continuous
worker with:

```powershell
cd "D:\Work\SURYADEV"
.\start-continuous-learning.ps1 -DataDir "D:\Work\SURYADEV-DATA" -ActivateOfficialTech -CoreMissionConfig "D:\Work\SURYADEV-DATA\paired-core-mission.json"
```

Without a TLS-pinned connection or owner-approved catalogue, OMIT
`-CoreMissionConfig`; normal v6.4 website/PDF/RSS continuity works independently.

Check local `/api/operations`:
- `continuity`: source-refresh outcomes and any per-feed errors
- `mission_renewal`: the request ID, queue low-water, and actual Core ACK
- `by_source`: source jobs acquired/processed; new mission IDs alone do
  not increment these counts
- `D:\Work\SURYADEV-DATA\krishna-mission-sync.json`: no secrets; local
  transport state `core_delivery_acknowledged`, `retry_later`,
  `no_new_approved_sources`, or `core_curriculum_exhausted`

## Remaining gates
- Core and laptop have not been physically connected or pair-tested for
  this new path in the user's environment. GitHub unit/CI is not hardware
  acceptance and does not install on the main Core or laptop.
- The finite operator catalogue cannot guarantee that novel approved
  sources fill six hours; when exhausted, the system must report this
  rather than replay completed URLs or invent progress.
- Real learning-bundle ingestion from standalone SQLite into BRAHMAGYAN
  still needs a source-specific evidence bundle adapter plus the existing
  server receipt/hash ACK; no Rishi LED should go green based on a
  delivery acknowledgment.
- Validate HTTPS transport, pair revocation, crash/power-outage recovery,
  malformed plan, zero-new-URL offers, and live device resources before
  unattended cross-machine rollout. Do not package a new EXE before browser,
  worker and Core integration tests pass.
