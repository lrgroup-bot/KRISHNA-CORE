# SURYADEV fleet rollout — opt-in, no automatic production deployment

## Current authority and scope

BRAHMAGYAN owns the knowledge ledger. Council Rishis/Acharyas own
domain research and independent theory/practical examinations. BRAHMA owns
scheduling policy; this draft's fleet service currently executes within
the paired KRISHNA Core API (a lightweight relay) until a standalone BRAHMA
scheduler is deployed. SURYADEV nodes acquire owner-approved source evidence
only. CHANDRADEV hardware-wide fleet supervision is not yet installed.

**Do not merge, install, sign or build an EXE until CI and isolated two-PC
and rollback tests pass.**

## Core-side preparation

Core's existing validated, manually approved source inventory remains:
`<Core SURYADEV state>/mission-authority/approved-curriculum.json`,
schema `krishna.suryadev.approved-curriculum.v1`. Entries must contain
an allowed HTTPS source host, a six-hour topic mission, and explicitly
approved URLs. Removing a source from this inventory prevents new dispatch.
No search agent may silently expand the inventory.

The new `SuryadevFleetService` derives stable task IDs from approved
mission IDs and URLs; each task is attributed to a registered subject
specialist. State is persisted atomically in `fleet-authority/fleet-leases.json`.
The agent status returns fleet counters, but no knowledge masteries.

## Owner-approved laptop activation after verified deployment

The device must first be explicitly paired with Core over the existing
pinned-HTTPS scheme; keep the token in a private file, never commit it.
The local `learning-plan.json` must independently approve each candidate
URL exactly, not merely its hostname. Existing source and book databases
are not cleared or replaced.

The following is the planned command **after the new branch is tested and
copied/installed into `D:\Work\SURYADEV`**, with a real owner-created
Core pairing file at the example path. It is not an instruction to run
before deployment:

```powershell
cd "D:\Work\SURYADEV"
.\start-continuous-learning.ps1 `
  -DataDir "D:\Work\SURYADEV-DATA" `
  -CoreMissionConfig "D:\Work\SURYADEV-DATA\core-mission-connection.json" `
  -FleetMode `
  -CollectApprovedBooks
```

`-FleetMode` activates pinned-TLS node heartbeats, bounded multi-lease
claims, renewals and collection receipts. No local Ollama model is required.
`-CollectApprovedBooks` only indexes already approved local books, not remote
unapproved media. Do not combine it with `-UseOllama`. All source-specific
network access remains subject to the existing permissions and provider limits.
There is only one active worker per data directory.

## Lease semantics and hard truths

- Every incoming assignment is revalidated against the device's own exact
  approved URL list and source kind.
- A lease is bound to one paired node, with expiry and ownership verification.
  Persisted local task IDs allow safe lease replay and several concurrent jobs.
  Renewals are required for long-running jobs.
- A recorded source SHA-256 is a **candidate collection receipt**, not an
  independent proof that source bytes were uploaded or factually verified.
- Previously collected source evidence remains local when Core is offline;
  completion is not claimed without Core acknowledgment. Expired leases are
  orphaned for recovery rather than rewritten as a success.
- Server-side YouTube 429 results impose a one-hour fleet-wide no-new-
  YouTube-admission period. Do not circumvent provider controls using extra PCs.
- Hardware safety: 85% admission guard, reduction from 75% pressure, current
  measured CPU/RAM/disk headroom. These do not enforce hard OS-wide limits.
  GPU telemetry and real temperatures remain hardware/driver-dependent.
- Queue exhaustion is truthfully reported when the approved curriculum
  contains no more work. Infinite *unique* research is not guaranteed.

## Acceptance gates before rollout

1. GitHub Core and SURYADEV unit tests pass on Windows and Linux.
2. Paired TLS device authentication, token replay and source allowlist
   rejection are tested on two isolated real machines.
3. Execute 1/5/10-node planner simulations, then 2-PC lease acceptance and
   task completion with actual persisted evidence.
4. Power off one node during a job; verify expired lease returns to queue,
   no duplicate globally accepted result, and original evidence preserved.
5. Confirm average and peak CPU/RAM stay within operational thresholds, and
   external-source rate limits remain honored across nodes.
6. Have a second Rishi independently examine a genuine practical artifact
   through BRAHMAGYAN. Never award a learning level based on a job receipt.
7. Run browser UI regressions, package only after tests, install only with
   owner authorization, and preserve rollback.

## Unimplemented requirements

BRAHMA self-hosted standalone scheduler service, direct dispatch from
arbitrary BRAHMAGYAN Rishi research subquestions, automatic six-hour refill
after the finite operator-approved catalogue is exhausted, true Rishi exam
generation and signed independent grading, spaced-retention tests, central
local Ollama gateway routing, CHANDRADEV real hardware fleet guardian,
fully benchmarked adaptive 20+ tab scheduling, physical two-PC proof and
universal signed EXE packaging are still unfinished.


## Native HTTPS + owner-approved zero-code pairing (feature-branch deployment)

The new opt-in Core listener uses the SAME production Core handler, but accepts
only SURYADEV pairing, heartbeat, status, mission, lease, completion and
candidate-bundle routes. It binds to a **specific private IPv4 NIC**, never
0.0.0.0, and preserves each remote peer's real TCP address. No reverse proxy
may downgrade a remote identity into Core-localhost authority. The ordinary
Core HTTP control room remains unchanged, and must never receive a device
credential over the network.

**Core PC deployment preparation** (only after a successful regression gate
and backups; do not send private-key contents into a chat or GitHub):

1. Obtain an owner-trusted TLS certificate and private key in PEM form with a
   SAN matching the Core PC's private IPv4 address. An explicitly pinned
   self-signed certificate is acceptable for this dedicated local fleet
   channel when its fingerprint is verified on the Core PC itself.
   Secure the private key with appropriate filesystem ACLs. Do not use an
   unaudited proxy, disable TLS, or trust a certificate fingerprint returned
   by a discovered/unknown network service.
2. Before starting Core, set these environment variables in the shell that
   launches it; substitute the actual private IP, paths and permitted port:

   ```powershell
   $env:KRISHNA_SURYADEV_TLS_CERT_FILE = 'E:\\Krishna-The GOD\\secure\\suryadev-cert.pem'
   $env:KRISHNA_SURYADEV_TLS_KEY_FILE  = 'E:\\Krishna-The GOD\\secure\\suryadev-key.pem'
   $env:KRISHNA_SURYADEV_TLS_BIND_IP   = '192.168.0.100'
   $env:KRISHNA_SURYADEV_TLS_PORT      = '8443'
   ```

   These are **example paths/IPs**, not inferred live hardware settings.
   No firewall permission is added automatically. Restrict port 8443 to the
   explicitly approved local devices and keep it inaccessible from WAN.
   The native TLS endpoint comes online with the next Core process start.
   Keep port 8766 controlled separately for existing local UI clients.
3. Compute the server certificate's **DER leaf SHA-256 fingerprint locally on
   KRISHNA PC**. For example, with owner-installed OpenSSL:
   `openssl x509 -in <cert.pem> -noout -fingerprint -sha256`.
   Copy the verified fingerprint to the laptop out-of-band.

**SURYADEV 1 laptop**, in a *second PowerShell window* with the existing
installed dashboard/worker untouched:

```powershell
$root = 'D:\\Work\\SURYADEV-FLEET-CANARY-20261025'
$py = "$root\\.venv\\Scripts\\python.exe"
$app = "$root\\app"
$data = "$root\\data"
& $py "$app\\suryadev_pairing_bootstrap.py" --data $data request `
  --endpoint 'https://192.168.0.100:8443' `
  --cert-sha256 '<VERIFIED_64_HEX_CERTIFICATE_FINGERPRINT>' `
  --device-id 'suryadev-1'
```

This **generates a fresh secret locally** and sends only its SHA-256 over
certificate-pinned TLS. It prints a `request_id` for explicit approval, not a
secret. It will refuse to overwrite an existing pairing or token file.

**KRISHNA main PC**, through its current loopback HTTP control API, inspect
the pending identity and approve ONLY the matching request ID:

```powershell
$pending = Invoke-RestMethod 'http://127.0.0.1:8766/api/mobile/pair/pending'
$pending.pending | Select-Object request_id,device_id,name,expires_at,credential_proposed
# Verify the device/request in the list and replace the placeholder:
$approval = Invoke-RestMethod 'http://127.0.0.1:8766/api/mobile/pair/approve' `
  -Method POST -ContentType 'application/json' `
  -Body '{"request_id":"<EXACT_REQUEST_ID_FROM_VERIFIED_PENDING_LIST>"}'
$approval | Select-Object approved,device_id,mode
```

This local approval must return `client-hash-zero-code` and must not return
a plaintext token. If it expires, do not bypass approval; recover carefully
rather than generating a second identity on top of the existing pending file.

**SURYADEV laptop activation** only after approved:

```powershell
& $py "$app\\suryadev_pairing_bootstrap.py" --data $data activate
$o = Invoke-RestMethod 'http://127.0.0.1:8872/api/operations'
$o.connections | Format-List
```

Activation verifies the actual already-approved credential over pinned TLS
using KRISHNA's own device-status route. A 404 specifically saying the node
has not sent a heartbeat is acceptable as an authenticated *pre-heartbeat*
state; a 401, wrong 404, certificate mismatch or network error is not.
Activation writes the same `core-mission-connection.json` schema the
existing worker supports, but does **not** claim a live heartbeat or Rishi
learning. An already-running collector can adopt the configuration on its
next poll; no duplicate worker should be started.

**For the fleet to receive real new jobs** the Core PC must also have an
operator-approved, validated `mission-authority/approved-curriculum.json`
and the laptop's existing `learning-plan.json` must independently approve
those exact source URLs (or an explicitly approved paired-Core host delegation).
Use `core/suryadev-approved-curriculum.example.json` as a reviewed
schema reference. The two completed Python/About and W3C dummy PDF jobs
are local evidence; they are not retroactively authenticated fleet receipts.

**Canary success criteria:** current `/api/operations.connections.krishna`
reports authenticated heartbeat; a freshly leased task has an actual
SHA-256-verified evidence file; KRISHNA returns a matching fleet receipt;
BRAHMAGYAN reports a recorded **unverified** candidate; and a separately
approved and independently graded Rishi examination is recorded with real
artifacts. No Rishi mastery/retention claims without that final evidence.

**No physical deployment claimed by this PR:** Certificate/private key
creation, selecting the correct NIC and firewall boundary, Core restart,
pairing approval and the actual two-PC round trip require operator access
to the KRISHNA PC and laptop. Neither a CI mock nor a source-level test
can substitute for that.
