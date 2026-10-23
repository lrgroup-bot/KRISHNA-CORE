# KRISHNA-fed SURYADEV — single-worker automatic mission intake (v7.5)

## Owner intent

**KRISHNA assigns, BRAHMA schedules, Rishi Council investigates, SURYADEV collects, BRAHMAGYAN verifies.**
Operators should not reenter research URLs for every six-hour mission. The local official source pack is an **offline fallback**, not the principal distributed research scheduler.

## Implemented GitHub branch behavior

- Dashboard startup **only** auto-launches a single KRISHNA-fleet worker if the laptop already holds the valid **owner-provisioned** `<SURYADEV-DATA>/core-mission-connection.json`, using the existing pinned HTTPS certificate, device ID starting `suryadev-`, and a separately stored pairing token. Merely typing an IP into Settings does not pair. The same worker lock prevents duplicates. If an external worker already holds the lock, its process remains untouched.
- The dashboard-managed child uses 1 research job, 1 Garudanetra browser tab, and <=2 local Ollama CPU threads. It runs the existing `--fleet-mode` client with `--plan` and `--core-mission-config`. No second scheduler or paid model is introduced.
- A locally scoped, one-time operator choice `paired_core_host_delegation: true` lets the **authenticated** KRISHNA fleet or six-hour mission client choose URLs only on hostnames already listed in `learning-plan.json.allowed_source_hosts`. The Core itself must independently have an approved curriculum; the local worker still validates HTTPS, userinfo, fragments, ports, DNS-public destination, research source type, resource capacity and job deduplication. Default remains **false**, preserving old exact-URL restrictions. One-click change through the loopback CSRF-protected Mission Pulse UI creates a plan backup.
- Fresh accepted paired Core heartbeat receipts are rendered as Core-connected only while younger than 150 seconds. BRAHMAGYAN/Rishi remain disconnected until separate verified evidence and exam receipts; Core being reachable or a local config file does **not** qualify.
- If no pairing exists, the laptop continues official-source/RSS/local work. It must say **Core not paired** instead of implying remote work arrived.
- No stored evidence/SQLite rows, old application folder, Core credentials or independent KRISHNA trading safeguards are changed.

## Still required on real machines

The owner must perform a **one-time secure device pairing**, providing actual TLS-pinned Core origin, device identity and token-file path at `<SURYADEV-DATA>/core-mission-connection.json`. The example file is NOT a credential and cannot be used as one. Verify the Core endpoint serves genuine HTTPS; the normal plain HTTP Core port does not automatically meet that requirement. Neither this GitHub code nor local dashboard health checks constitute device enrollment.

The Core's current backlog is finite and sourced from `mission-authority/approved-curriculum.json`. **Autonomous KRISHNA/Rishi generation of new curriculum entries, automated online source discovery outside the already approved host scope, a permanently installed Windows service, two-physical-PC acceptance and evidence/BRAHMAGYAN mastery sync remain separate pending work.** Do not claim infinite six-hour learning on an exhausted finite list. Unapproved links remain rejected.

## Verification

The isolated Windows test data remains distinct from the original SURYADEV installation. Update development branch, reinstall into `D:\Work\SURYADEV-UNIFIED-TEST` after browser and CI checks, then restart dashboard `8771`. Read `GET /api/learning/control` for `core_dispatch.ready`, `dispatch_mode` and the delegation state; read `GET /api/operations` for actual Core fleet state, heartbeat and real job receipts. Green connection LEDs require authenticated heartbeat acknowledgments, not a successful ping.

The user should never have to perform *per-source* copy/paste after the one-time secure pairing and delegated scope. Source selection remains bounded by Core's approved curriculum and the laptop's approved hostnames.
