# SURYADEV — Universal learning fleet architecture (2026-10-25)

> Implementation-stage contract. **Do not merge into production or replace the live
> laptop installation until the new branch passes CI and separate 2-node physical
> acceptance.** This document distinguishes working code from intended releases.

## Identity and authority

- **One host runtime / one source tree** is installed on any supported SURYADEV
  Windows, Linux or macOS node. Windows EXE packaging is ONE host artifact for
  compatible Windows nodes, NOT one EXE per hardware configuration. Other OSes
  need platform-native packaging. Every node gets a unique **owner-paired**
  `suryadev-<id>` device identity and independent evidence directory.
- **KRISHNA**: final governance, pairing, quota, plugin trust/revocation,
  task leases, receipts and operator-approved repair authorization.
- **SURYADEV RAKSHAK**: independent low-memory health-monitoring process on
  the KRISHNA PC. KRISHNA only provides a read-only fleet-node snapshot; it
  does not execute a five-minute watchdog thread.
- **BRAHMAGYAN**: canonical candidate/claim/mission/exam ledger. It is NOT the
  source collector, question generator, independent examiner or autopublisher.
- **RISHI Council**: topic experts author research questions, challenge
  evidence, independently test practical skill and grade theory/practical.
- **BRAHMA**: approved mission backlog and device task leasing.
- **SURYADEV 1..N**: evidence collection / indexing / bounded local
  interpretation from exactly approved sources, with measured process health.
- **CHANDRADEV/MRITYUNJAY**: independent validation and separately authorized
  remediation; NOT blanket permission to kill unrelated programs.

```text
Owner/KRISHNA approved scope and trusted plugin keys
                   |
          BRAHMAGYAN mission ledger
                   |
      Rishi research questions and challenges
                   |
        BRAHMA backlog & lease authority
                   |
    Fleet scheduler (resource/capability/queue)
       /              |              \
SURYADEV 1        SURYADEV 2       SURYADEV N
 websites/PDF     video/browser    any eligible lane
  local sources     frame evidence  safety/model choice
       \              |              /
    exact URL, bytes/hash, page/line/time, error
                   |
    authenticated KRISHNA receipt (NOT mastery)
                   |
     BRAHMAGYAN candidate evidence L0 ...
                   |
     distinct Rishi challenge / practical / exam
                   |
     verified/failed/disputed knowledge ledger
```

## Resource admission: no per-PC fixed number

Each node samples CPU, RAM/available memory, disk, measured GPU/VRAM where
supported, power, thermal sensors, network interface and recent approved-source
reachability. A missing sensor is **unknown**, not free capacity.

One authoritative worker lock per node. Work queues are different from jobs
admitted simultaneously. At/above 85% CPU/RAM/disk/supported GPU or inadequate
memory/storage, new heavy work is refused; >=75% RAM or >=70% CPU, new work is
conservatively throttled. Resource usage can still spike between samples.
Local model generation remains serialized with the shared model lock.

The same portable launcher supports:
- **Legacy profile:** fixed 3-task upper cap (old laptop data unaffected).
- **Opt-in `--adaptive-fleet`:** maximum 125 local slots as a SOFTWARE
  *upper bound*, further reduced by live hardware admission and each existing
  source-lane engine's limits. This DOES NOT claim 125 tabs are supported or
  safe on a given device. Existing per-kind implementation ceilings remain
  website 10, browser video 10, PDF 100 and book 5. Higher counts need a
  real tab-memory benchmark, plugin capability profiling, fair queueing,
  provider/legal-source limits and dynamic scale-up tests.
- Neither profile has an automatic default right to reclaim memory by
  terminating unrelated Windows/Linux/macOS processes.

**Automatic specialization:** owner-approved sources are sent only to
authenticated nodes advertising the required capability. Video-only SURYADEV 2
can now request a video lane without the former website-only admission probe.
This is not yet a globally optimal all-node rebalance algorithm. Expand node
capability detection, work estimation and anti-thrashing before claiming that
every Youtube job migrates automatically to the fastest machine.

## Continuous chain (zero compulsory schedule downtime)

`start-node.py --adaptive-fleet --continuous --model collector` opt-ins to
`mission_rest_policy=continuous` in the node's persistent workspace marker.
Six-hour boundaries increment the mission counter without interrupting
in-flight source jobs or imposing the *legacy ten-minute mandatory rest*.
Older workspaces and existing mid-rest intervals retain the old safe cadence.
Actual downtime can still happen due to hardware pressure, sleep/shutdown,
source exhaustion, quota/cooldown, credential expiry or network loss. It must be
reported, **never faked as learning**.

BRAHMA keeps ahead-of-time approved and deduplicated assignments; low-water
mission renewals exist, but require actual paired TLS delivery and a replenished
owner-approved source catalog. Non-YouTube work may continue during 429
cooldowns. Task-failure recovery never bypasses licensing or source policy.

## Hardware-specific model choice

**Collector mode** is the default for portable nodes and performs no Ollama
generation. `qwen3.5:2b` is supported as a lightweight opt-in model; a
central private inference service may later take analysis jobs. Heavy local
models must not be loaded just to scrape/parse a webpage. The next phase
requires a measured per-node model router with available RAM/VRAM, latency,
quality/evidence, temperature and license compatibility gates: local collector
→ small local model → authorized central model → defer inference. No paid
fallback, no external private content without consent. A model response is
never independent verification.

## Verified learning, not superficial summarization

Require separate, inspectable receipts for:

1. **Source authorization** — exact URL/file hash, owner scope, source identity.
2. **Source acquisition** — content SHA-256, retrieved date and complete
   enumerated source units (web page/viewport, PDF page/line, book
   spine/line, video timeline plus caption, image and audio coverage).
3. **Coverage QC** — every expected unit accounted for, with gaps and
   unreadable diagrams/pages/segments kept visible; no invented duration.
4. **Candidate interpretation** — source-aligned claims, citations, examples,
   contrary evidence and source limitations from local or central model.
5. **Independent verification** — Rishi challenge, reproducible practical
   test artifacts and separate theory/practical examiner.
6. **Retention** — novel recall/transfer after delays; revise knowledge when
   challenged. A completed page index alone cannot prove comprehension.

Currently the source ledger, snapshots, book line journals, video audit and
BRAHMAGYAN exam recording are implemented in parts. **Automatic end-to-end
independent Rishi assessment is not done**. Signed examiner identity and
source-complete verifiable transfer need dedicated work.

## Five-minute fleet oversight by independent SURYADEV RAKSHAK

**KRISHNA runs no watchdog background thread.** An independent Python
`suryadev_rakshak.py` process polls every 300 seconds. It loads no browser
or Ollama, starts no KRISHNA scheduler and never kills applications.

**Preferred zero-HTTP live path (even before updating KRISHNA Core):**
RAKSHAK can read the existing, atomically persisted
`<KRISHNA runtime state>/suryadev/device-nodes.json` **read-only** using
`--core-state`. Source is resolved and checked; no Core server RPCs or
new endpoints are required. The guard is a separate process on the KRISHNA
computer. Core's usual paired-node heartbeat updates remain unchanged.

```powershell
python .\suryadev_rakshak.py --data "E:\GITHUB\SURYADEV-RAKSHAK-DATA" --core-state "<FULL_PATH_TO_EXISTING_device-nodes.json>" --once
```

For ongoing monitored operation, omit `--once`; use Ctrl+C to stop.
Optional upgraded Core releases expose a **loopback-only** read-only
`GET /api/suryadev/fleet/nodes` for a 300s read request as an alternative.
Neither mode permits a remotely located RAKSHAK without separate pinned-TLS
enrollment; don't expose the endpoint over LAN.

All reports go to RAKSHAK's **own** durable `rakshak-status.json` and
transition-only `rakshak-incidents.jsonl`, not KRISHNA's runtime data.
No registered node is NOT considered a healthy fleet; it is reported clearly.
A queued task without observed active source work is a diagnostic only,
not an instruction to restart or kill any process.

Autostart on reboot, node-to-guard TLS on a separate machine, escalation to
MRITYUNJAY and safe authorized repair actions require separate validated
deployment. **No self-heal command/process termination is implemented here.**

## Plugins — versioned trust contract, not blind remote execution

To minimize host rebuilds, the stable EXE will eventually contain a narrow
versioned plugin RPC/protocol boundary (source parser, browser engine,
transcript provider, vision processor, optional model adapter, knowledge
validator, exporters). Plugin packages can be downloaded and updated
independently only after compatibility, source permission and signature checks.

Foundation now included:
- `suryadev_plugins.py` scans a local data-root `plugins/<plugin_id>`
  directory and verifies an owner-pinned Ed25519 signer public key, a
  canonical signed manifest (API v1) and the executable payload SHA-256.
- No trust-on-first-use; no implicit software download, auto-install,
  plugin execution, privilege escalation or new source authorization.
- The read-only dashboard `GET /api/plugins` reports validated manifests
  separately from rejected ones. An accepted manifest is **NOT activated**.
- Sandbox-limited subprocess execution, schema validation, plugin lifecycle,
  version compatibility, key revocation, staged rollout, rollback and
  crash isolation are **future development gates**. Python imports are not
  an effective security sandbox.

The first host EXE should be a stable, signed launcher/communication supervisor
with strict plugin ABI and rollback. **Never rebuilding it cannot be guaranteed**:
critical vulnerabilities, OS ABI changes, broken host/protocol features and
new native capabilities may require a signed host update.

## Additional implementation after first audit

- **Dynamic fleet allocation:** Core prioritizes non-video work for general
  collectors when a video-only node can take YouTube, subject to approved
  source URLs, Rishi balancing and fresh paired-node telemetry.
- **In-flight lease renewal:** 85% pressure stops NEW jobs, not legitimate
  renewal of already-leased work. Renewals still need a fresh authenticated
  worker and telemetry; expired/unpaired jobs are rejected.
- **Automatic local model policy:** `--model auto` checks measured hardware
  and the *already-installed* local `qwen3.5:2b` model. Low RAM, CPU,
  battery, thermal headroom or missing Ollama selects `collector`. No model
  downloads, paid fallback or heavy model is automatic.
- **Capability advertisements:** nodes report installed `pypdf`, `yt_dlp`,
  and Playwright prerequisites rather than claiming every source backend.
  Installed package detection is not a full Chromium or provider-access
  smoke test. Local book collection requires an approved source plan.
- **SURYADEV local crash guard:** optional `suryadev_node_guard.py` launches
  the *same* portable SURYADEV app, keeps its own status journal and safely
  retries a crashed child up to three times in an hour. Repeated crashes are
  quarantined; source evidence is never reset. It does not enumerate, stop,
  or kill unrelated OS applications. Windows uses its own process group;
  POSIX signals only the guardian-owned session group.
- **Mission-renewal consistency:** continuous profile records zero forced
  rest in the local BRAHMAGYAN renewal outbox, while legacy installations
  retain the ten-minute rest contract.
- **RAKSHAK:** separate 300s observer, with direct read-only ledger mode;
  KRISHNA runs NO monitoring thread or additional AI model.

A guardian can be invoked from the installed SURYADEV directory after
separate profile preparation, approved-source configuration and CI gates:

```powershell
python -u .\suryadev_node_guard.py --data "D:\Work\SURYADEV-FLEET-CANARY-DATA" --model auto --adaptive-fleet --continuous --port 8773
```

`--model auto` is optional; `collector` guarantees zero local model use.
The guardian is NOT automatically installed as an OS startup task.

**Still not proven without physical acceptance:** signed TLS pairing of
multiple real PCs; complete YouTube visual/audio/caption coverage; real
PDF/book source quality; independent Rishi examinations and delayed retention;
true 100-tab hardware benchmark; secure sandboxed plugin execution; and
automatic low-water creation of a sufficient new *approved* curriculum.

## Deployment / physical acceptance

Do not replace the running laptop data installation in this PR. On a separate
test node and backed-up empty data root after CI succeeds:

```powershell
python start-node.py --data "D:\\Work\\SURYADEV-FLEET-DATA" --model collector --adaptive-fleet --continuous
```

Then perform tests with 1, 2 and 4 owner-paired nodes. Verify actual node
capabilities and per-source work; 5-minute watchdog; 85% refusal; approval
catalogue depletion; machine disconnect/lease reassignment; full video and
book evidence; signed Core acknowledgment; and independent Rishi exam.
Only then consider host/EXE deployment.
