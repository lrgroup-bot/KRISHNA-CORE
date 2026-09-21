# KRISHNA Completion Matrix

This matrix is the canonical implementation ledger for the KRISHNA ideas agreed across the project chats. A feature is not marked complete merely because a UI card or adapter name exists.

Status meanings:
- **VERIFIED** — implemented with repository tests/contracts.
- **IMPLEMENTED / RUNTIME VERIFY** — code exists; real Windows runtime or external dependency still needs acceptance.
- **PARTIAL** — useful implementation exists but does not yet satisfy the complete design.
- **ROADMAP** — deliberately deferred.

## 1. KRISHNA authority and autonomous control

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| One public identity: KRISHNA | VERIFIED | Internal engines are selected by Core; clients do not choose Karma/Vishwakarma modes. |
| Neural Action Graph routing | VERIFIED | Core routing and architecture contracts. |
| Policy/Security Kernel between decision and execution | VERIFIED | Mutating/high-impact actions fail closed without approval. |
| Planner → specialists → critic → independent verifier → KRISHNA decision | IMPLEMENTED / RUNTIME VERIFY | Curated team planner now returns bounded role manifests, permissions/risk, Agency-Agents advisors, mandatory Critic and independent Verifier, with live mutation blocked until separate promotion. |
| Shadow repair, verification, promotion and rollback | VERIFIED | Repository tests cover bounded promotion/rollback. |
| Resource governor / PC observer / recovery | IMPLEMENTED / RUNTIME VERIFY | ResourceGovernor + PCObserver now pair with worker crash-loop backoff/quarantine, a Core Guardian restart loop, and critical-RAM Ollama unload that never deletes model files. Long-duration Windows soak remains. |
| Continue working while owner is away; notify only meaningful completed work | IMPLEMENTED SAFE BOUNDARY / RUNTIME VERIFY | AutonomySupervisor resumes explicitly opted-in non-mutating investigate/research/index commitments while unattended; mutation, promotion and external side effects still require their normal approval gates. Mobile completion notifications remain separate. |
| Permanent Commitment Ledger: never silently forget agreed work | VERIFIED boundary | Unfinished/forgotten commitment APIs exist and Work UI now surfaces them automatically. |
| Automatic resume/implementation of safe forgotten commitments | IMPLEMENTED SAFE BOUNDARY / RUNTIME VERIFY | Durable supervisor scans unfinished commitments, refreshes safe evidence on schedule, records evidence IDs/results, respects ResourceGovernor and never auto-resumes waiting-approval or non-allowlisted operations. |

## 2. Sudarshan

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| GPT-style project conversation workspace | VERIFIED boundary | Persistent project chats, history, attachments and chat actions exist. |
| Chat Rename / Pin / Share / Move / Delete dropdown | IMPLEMENTED / RUNTIME VERIFY | UI implementation and contracts exist. |
| Active Work / Verification / System Load informer | IMPLEMENTED / RUNTIME VERIFY | Command Center v4. |
| 50/50 Sudarshan + Garudanetra live-work split | IMPLEMENTED / RUNTIME VERIFY | Real Chromium PNG frame stream, evidence feed, owner takeover, typing/navigation/tab controls and Expand are wired; final Windows latency/interaction acceptance remains. |
| Files / Plugins / Projects / Research / Investigate tools | VERIFIED boundary | Existing APIs/UI. |
| Dockview draggable/floating workspace | ROADMAP | Planned React migration; current UI is transition HTML. |
| xterm terminal and React Flow NAG visualization | ROADMAP | Planned React migration. |

## 3. Garudanetra

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Private browser/research identity | IMPLEMENTED / RUNTIME VERIFY | Each live browser job uses an isolated non-persistent Chromium context; research/scout and live browsing remain under KRISHNA authority. |
| Chromium / Playwright / browser inspection | VERIFIED boundary | Browser operator/UI inspection tests exist. |
| Live Work panel + Pause / Take Control / Continue / Stop | IMPLEMENTED / RUNTIME VERIFY | Controls now drive the persistent Garudanetra browser session rather than UI-only state. |
| Actual streamed browser viewport and owner takeover | IMPLEMENTED / RUNTIME VERIFY | Persistent private Chromium session manager streams real PNG browser frames into Sudarshan and accepts owner click/scroll takeover commands; Windows Playwright acceptance remains. |
| UI Guardian detect → sandbox → verify → promote/rollback | IMPLEMENTED / RUNTIME VERIFY | Objective browser checks now run across the four target viewports; GUI candidates are persisted in Stable/Candidate/Experimental/Rejected registry and Stable promotion requires a passed evaluation plus explicit verification. Automatic repair generation still routes through Developer/shadow workflows. |
| Private + Task Memory / Persistent Workspace profiles | IMPLEMENTED / RUNTIME VERIFY | Private destroys state; Task Memory persists evidence into candidate Gyan memory; Persistent Workspace uses only a project-specific KRISHNA profile and requires explicit approval. UI mode selection is wired. |
| Learned browser skills saved to Gyan-Bhandar | IMPLEMENTED CANDIDATE PIPELINE / RUNTIME VERIFY | Deterministic locator recovery and optional external harness produce candidate selector skills; Task Memory proposes them as Gyan skill candidates requiring verification/approval before becoming trusted knowledge. |

## 4. Gyan-Bhandar

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Evidence-backed long-term memory | VERIFIED boundary | Candidate/verified learning APIs and approval UX exist. |
| Working / episodic / semantic / graph / skill / evidence memory facade | IMPLEMENTED / RUNTIME VERIFY | Typed memory kinds are enforced in MemoryFabric/Gyan-Bhandar, inventory is exposed by API and the UI can filter/inspect each category. |
| Provenance, confidence and explicit promotion | IMPLEMENTED / RUNTIME VERIFY | Learning and pending-approval records now preserve memory kind, provenance, confidence, evidence and approval state. |
| Supersession of outdated knowledge | IMPLEMENTED / RUNTIME VERIFY | Replacement knowledge is proposed through the approval queue; on approval the previous fingerprint becomes superseded and links to its replacement. Graft remains an optional backing adapter. |
| Code intelligence links from Codebase-Memory | PARTIAL | Optional CBM adapter exists; E:\KRISHNA-CBM / CBM-Runtime must be audited and connected. |

## 5. NARAD

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Native automation/messenger control plane | VERIFIED boundary | Durable workflow lifecycle and policy gates. |
| DRAFT → CANDIDATE/SANDBOX → VERIFIED → STABLE | VERIFIED | Runtime/tests. |
| Execution history and dead letters | IMPLEMENTED / RUNTIME VERIFY | Durable execution history plus identified dead letters and explicit retry lifecycle are implemented. |
| n8n / Activepieces / generic webhook boundaries | VERIFIED boundary | External execution is high-impact and approval gated. |
| MCP adapter | PARTIAL | Architecture requirement retained; provider-specific execution wiring remains. |
| Schedules / event triggers / webhooks | IMPLEMENTED / RUNTIME VERIFY | Stable workflows support durable event, >=60-second schedule and token-hashed webhook triggers; NaradScheduler runs as a Core daemon. |
| Gmail / Telegram / Slack / WhatsApp / Drive / Sheets / Calendar integrations | IMPLEMENTED / RUNTIME VERIFY | NARAD provider hub implements bounded Telegram, Discord, Slack, WhatsApp, Gmail, Drive, Sheets and Calendar operations. Provider workflows remain Policy approval gated and credentials stay in references/vault. Live provider credentials/API acceptance remains environment-dependent. |
| Credential vault / secret references | IMPLEMENTED / RUNTIME VERIFY | Narad supports environment references plus Windows user-bound DPAPI encrypted secrets. Plaintext is never returned by list/status APIs. Real Windows encryption round-trip is in runtime acceptance. |
| Full Automations / Connections / Messages / Triggers / History UI | PARTIAL / expanded | Control Center now manages workflows, manual/event/schedule/webhook triggers, connection references, dead letters and history. Provider-specific message inbox/outbox and richer visual workflow editing remain. |

## 6. Code intelligence and specialist workers

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Codebase-Memory-MCP as structural code intelligence | IMPLEMENTED / RUNTIME VERIFY | Adapter now discovers the known E:\\AI-Tools\\codebase-memory-mcp executable as well as env/PATH/alternate E: locations; indexing acceptance still runs on the real PC. |
| Graft behind Gyan-Bhandar | PARTIAL | Optional adapter exists; local runtime/CLI still requires reconciliation. |
| Context governor | VERIFIED boundary | Bounded verified-first context selection implemented. |
| Privacy-aware multi-model pool | VERIFIED boundary | Model router exposes local/cloud providers and coding plans according to project privacy. |
| Free/local-first routing (Ollama / GPT4All / encrypted free-only gateway) | IMPLEMENTED / RUNTIME VERIFY | Router tries local Ollama/GPT4All and supports DPAPI-backed OpenAI-compatible free-only gateway profiles. free_only requests never silently fall through to paid env-cloud providers. Provider runtime availability remains environment-dependent. |
| Cloud fallbacks (OpenAI/Gemini/Claude/Grok/OpenRouter) without leaking restricted project data | IMPLEMENTED BOUNDARY / RUNTIME VERIFY | Restricted/local-only projects cannot cloud-fallback. Approved cloud providers remain credential/environment dependent; encrypted gateway credentials are supported. |
| Agency-Agents specialist library | IMPLEMENTED / RUNTIME VERIFY | Runtime has external agency-agents library; selection/indexing exists. |
| Architect / Backend / Frontend / Debugger / DevOps / Security / Test / Research / Data / UI / Docs patterns | IMPLEMENTED / RUNTIME VERIFY | Curated manifests and task-driven team assembly are implemented and surfaced in Specialist Teams UI; Agency-Agents remain prompt-only advisory contexts. |
| OpenMontage only as media/YouTube worker | VERIFIED boundary | Media adapter keeps it outside the KRISHNA brain. |

## 7. KABACH

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Project security/boundary guardian | VERIFIED boundary | Backend KABACH agent and project protection API. |
| Dedicated navigation and project-boundary view | IMPLEMENTED / RUNTIME VERIFY | Command Center v4 runtime branch. |
| Defensive research delegated through Garudanetra | VERIFIED boundary | Orchestrator keeps KRISHNA authority. |

## 8. Source/runtime deployment integrity

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| E:\KRISHNA-SOURCE is authoritative code | IMPLEMENTED / RUNTIME VERIFY | Verified deploy flow enforces Git source. |
| E:\Krishna-The GOD is runtime/state/models/assets | IMPLEMENTED / RUNTIME VERIFY | Deploy excludes runtime-owned state/models/assets. |
| DEPLOYED_COMMIT.json with file hashes | IMPLEMENTED / RUNTIME VERIFY | Added atomic deployment manifest. |
| Detect source/runtime drift | IMPLEMENTED / RUNTIME VERIFY | RuntimeIntegrity API + UI. |
| Refuse misleading CORE ONLINE when drifted | IMPLEMENTED / RUNTIME VERIFY | START_KRISHNA blocks DRIFT and auto-deploys when source is ahead. |
| Non-destructive E: reconciliation audit | IMPLEMENTED / RUNTIME VERIFY | AUDIT_KRISHNA_E_DRIVE.ps1 now inspects AI-Tools CBM/OpenMontage, alternate CBM roots, AGI, agents, guardian, voice, Agency-Agents, dual mobile runtimes, dashboard, canonical avatar and unresolved leftovers. |
| One-command real Windows runtime acceptance | IMPLEMENTED / RUNTIME VERIFY | ACCEPT_KRISHNA_RUNTIME.ps1 starts an isolated local Core, validates integrity, NARAD, intelligence, KABACH, commitments, autonomy, Gyan promotion, Garudanetra live frames, UI Guardian, mobile state and E-drive audit, writes a JSON report, then shuts down. Verified deploys run it by default and refuse final start on failed release gates. |

## 9. Mobile

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Conversation-first mobile experience | IMPLEMENTED / RUNTIME VERIFY | mobile_v3 now exposes only conversation, microphone, attachment and avatar UX; dashboard/project/tool controls were removed from the UI. Natural-language requests still route through KRISHNA Core. |
| Secure pairing/device credential | VERIFIED boundary | Pair/resume/idempotency tests. |
| Same KRISHNA conversation/session across PC/mobile | IMPLEMENTED / RUNTIME VERIFY | Mobile now auto-creates/reuses a persistent KRISHNA Mobile chat and sends through the same Core chat/history path; real-device acceptance remains. |
| Proactive completion notifications | IMPLEMENTED / RUNTIME VERIFY | Android listens to task.completed realtime events and posts a local completion notification; real-device background delivery remains to be accepted. |
| One canonical mobile runtime | PARTIAL | E:\Krishna-The GOD\mobile\companion and repository mobile_v3 must be reconciled. |
| Remote use away from home | IMPLEMENTED PRIVATE-OVERLAY BOUNDARY / RUNTIME VERIFY | Core rejects public Internet clients, START_KRISHNA has Tailscale-only PrivateRemote mode, mobile accepts LAN/private-overlay targets, and configuration helper verifies Tailscale. Real away-from-home device acceptance remains. |

## 10. Voice and avatar

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Provider-neutral local STT/TTS boundary | VERIFIED | VoiceRuntime + LocalCLIProvider. |
| Odia speech | IMPLEMENTED PROVIDER BOUNDARY / RUNTIME VERIFY | AI4Bharat IndicConformer-style local STT and Indic-TTS-style local worker boundaries are wired with an E:-runtime setup helper. Actual model assets/commands must be configured and accepted on Windows. |
| Always-listening wake word “Krishna” | IMPLEMENTED / RUNTIME VERIFY | Local openWakeWord service boundary with custom KRISHNA model, microphone loop, cooldown and Core event emission is wired. Wake word remains activation only; custom model/hardware acceptance remains. |
| Owner voice verification | IMPLEMENTED GATE / NOT SECURITY AUTHORITY | Mobile uses a local owner voice gate before speech recognition; device credentials remain authoritative for sensitive actions. This gate must not be treated as strong biometric authentication. |
| Child KRISHNA avatar / local GLB route | VERIFIED boundary | Local avatar route/fallback and manifest boundary. |
| Rigged walking/body animation | PARTIAL | Requires verified rigged GLB asset. |
| Facial animation / lip sync / state animations (Dhyan, Flute, Work, Chat, Search) | PARTIAL | State boundary exists; full animation runtime/provider integration remains. |

## 11. Creator, media and revenue workers

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Creator providers (ComfyUI/Wan/LTX/SkyReels) behind worker boundary | VERIFIED boundary | Optional provider adapters only. |
| OpenMontage media bridge | IMPLEMENTED / RUNTIME VERIFY | E:\\AI-Tools\\OpenMontage installation is detected, but cloned source is not treated as executable authority; a dedicated OPENMONTAGE_CMD/worker bridge is required. |
| Revenue/CRM/publishing adapters | VERIFIED boundary | Business layer only; not KRISHNA authority. |
| Active provider workers installed and verified | ENVIRONMENT-DEPENDENT | Do not report active until binaries/services are present. |

## 12. UI architecture

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Liquid Glass + Bento + Spatial visual language | IMPLEMENTED / evolving | Current transition shell uses this direction. |
| KRISHNA Home separate from Sudarshan | VERIFIED UX boundary | Home is governing/core view; Sudarshan is work console. |
| Real-world/Vrindavan-inspired KRISHNA home option | PARTIAL | Prior patch/reference exists; final unified home still evolving. |
| React/shadcn foundation | ROADMAP | Final migration after runtime contracts stabilize. |
| Dockview | ROADMAP | Final workspace shell. |
| React Flow / xyflow Neural Action Graph | ROADMAP | Final workspace shell. |
| React Three Fiber avatar/spatial | ROADMAP | Final workspace shell. |
| GUI Registry Stable / Candidate / Experimental / Rejected | IMPLEMENTED / RUNTIME VERIFY | Persistent registry and Developer UI are implemented with verified Stable promotion gate. |

## 13. Glass / XR

The KRISHNA Glass hardware remains a later dedicated roadmap item after PC + mobile are stable. A production-safe WearableBridge is now implemented to track only verified capabilities:
- local sensorimotor/reflex layer beneath the main reasoning brain,
- camera/vision, audio, IMU/head tracking,
- hand gesture plus optional wrist/ring input,
- AR display,
- observe → decide → act → verify loop,
- shared control with PC/mobile.

Current bridge boundary:
- Phase 1: Bluetooth audio/microphone/speaker + phone camera capability registration.
- Phase 2: vendor camera/display adapters only after real hardware verification.
- Phase 3: IMU/gesture/wrist/ring/AR capabilities only after adapter/device evidence.
Vendor-specific capability is never claimed from product marketing or source presence alone.

Hardware Glass remains **ROADMAP / CAPABILITY-GATED**, not a production-complete claim.

## Final release gate

Do **not** build the final `Krishna_AGI.exe` until:
1. source/runtime integrity is SYNCED,
2. Windows runtime tests pass,
3. Sudarshan project/chat workflows pass,
4. Garudanetra real browser work and evidence flow pass,
5. Narad API/UI lifecycle passes,
6. Gyan-Bhandar candidate → approval → verified recall passes,
7. KABACH boundaries pass,
8. mobile connection/resume passes,
9. voice/avatar unavailable providers fail honestly,
10. restart/recovery/rollback and CPU/RAM governance pass,
11. DPAPI secret vault + free-only model routing pass on Windows,
12. attachment -> local vision -> conversation path passes when a supported local model is configured,
13. public-Internet remote clients are rejected and private-overlay mobile access passes,
14. Garudanetra Private/Task Memory/Persistent Workspace lifecycles pass,
15. local Odia voice/wake providers fail honestly when unconfigured and pass when configured,
16. wearable capability registry reports only hardware-verified capabilities.
