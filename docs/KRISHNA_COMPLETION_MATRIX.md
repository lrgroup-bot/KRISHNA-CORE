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

## 1A. Agent-Native reference / Shared Action execution spine

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Agent-Native used as reference, not replacement | VERIFIED architecture boundary | KRISHNA retains Neural Action Graph, Policy, memory, browser, automation and verifier authority; Agent-Native contributes the composable-primitive/runtime pattern. |
| Shared Action Bus | IMPLEMENTED / RUNTIME VERIFY | Named actions carry action ID, project, source, actor, permissions, approval, idempotency, sanitized payload/result, events and audit receipt. Raw shell is not an action primitive. |
| Projects / Chats on Shared Action Bus | IMPLEMENTED / RUNTIME VERIFY | Project registration and chat create/move/rename/delete priority UI paths use `actionReq`; compatibility routes delegate to the same actions. |
| Agent Runtime | IMPLEMENTED / RUNTIME VERIFY | Garuda, Garudanetra, UI Guardian, Developer and NARAD manifests have explicit action patterns and capabilities; agents dispatch through the Shared Action Bus. |
| Jobs | IMPLEMENTED / RUNTIME VERIFY | JobRuntime creates authoritative durable Missions, executes through the backend-owned durable queue, links compatibility TaskLedger IDs, and finalizes completion only after Sudarshan verification. Current worker mode is durable-queue-inline-worker. |
| Permissions | IMPLEMENTED / RUNTIME VERIFY | PermissionRuntime distinguishes local owner/system authority from capability-bounded agent/job/MCP/A2A/mobile callers. |
| Audit / rollback | IMPLEMENTED BOUNDARY / RUNTIME VERIFY | Shared Actions publish requested/completed/failed/blocked receipts and write sanitized durable MemoryStore audit metadata. Project file promotion/rollback remains under PromotionManager transactional backups. |
| MCP / A2A | INTERNAL ADAPTER BOUNDARY / RUNTIME VERIFY | MCP tool catalog/call and A2A dispatch adapters map to the same Shared Actions. No unauthenticated public protocol server is claimed. |
| Unified Dispatch | IMPLEMENTED / RUNTIME VERIFY | DispatchRuntime targets action, agent or job while preserving one execution authority. |
| Desktop / Mobile sync | IMPLEMENTED FOUNDATION / DEVICE VERIFY | Action state is mirrored as authenticated `action.sync` realtime events; mobile uses only its conversation status indicator, not a dashboard. |
| Garuda / Garudanetra integration | IMPLEMENTED / RUNTIME VERIFY | Garuda scout and Garudanetra start/control/upload/replay actions are registered on the same bus; priority UI functions use direct Shared Action receipts. |
| No decorative operational controls | PARTIAL / ENFORCED ON PRIORITY SURFACES | Repository contracts enforce action receipts for Projects/Chats/Garuda/Garudanetra. Remaining legacy POST-backed controls are real runtime endpoints but are migrated incrementally to named actions. |

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

## 3. Garuda + Garudanetra Browser Fabric

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Garuda research identity is separate from Garudanetra | VERIFIED boundary | Garuda owns research/evidence scouting; Garudanetra owns browser/computer execution. The UI and runtime no longer route the Garudanetra mission button through Garuda research. |
| One canonical Garudanetra Browser Fabric | VERIFIED boundary | `browser_fabric.py` owns the live session authority and shared inspector boundary. Server runtime no longer imports the legacy `GarudanetraService`. |
| Playwright / Chromium canonical engine | VERIFIED / RUNTIME ACCEPTED | Playwright remains the canonical verified engine; optional adapters cannot silently replace it. E-drive startup pins browser assets to the KRISHNA runtime. |
| Semantic accessibility-style refs | IMPLEMENTED / RUNTIME VERIFY | Live sessions maintain bounded `e1/e2/...` semantic refs with role/name/geometry and allow ref-driven browser actions/recovery. |
| CDP screencast live frame | IMPLEMENTED / RUNTIME VERIFY | Garudanetra starts a Chrome DevTools Protocol screencast and retains bounded PNG screenshot fallback if CDP streaming is unavailable. |
| Live Work + owner takeover | IMPLEMENTED / RUNTIME VERIFY | Pause / Take Control / Continue / Stop / tabs / typing / keypress / click / drag / scroll / upload remain wired. Live Work stays collapsed unless explicitly opened or owner attention is required. |
| Private + Task Memory / Persistent Workspace profiles | IMPLEMENTED / RUNTIME VERIFY | Private destroys state; Task Memory preserves evidence; Persistent Workspace uses only project-specific KRISHNA profiles and requires explicit approval. |
| Console/network/download/visible-text evidence | IMPLEMENTED / RUNTIME VERIFY | Live session snapshots redact sensitive URL query fields and retain bounded verification evidence. |
| Self-healing locator recovery | IMPLEMENTED / RUNTIME VERIFY | Deterministic role/label/placeholder/text recovery runs first; optional Browser Harness and configured vision recovery produce untrusted candidate evidence only. |
| Browser action recording | IMPLEMENTED / RUNTIME VERIFY | Successful/error actions are captured; typed/fill values are redacted by default unless explicitly marked reusable. |
| Bounded workflow replay | IMPLEMENTED / RUNTIME VERIFY | Safe navigation/observation replay is allowed; consequential click/fill/type/upload style replay is blocked without explicit approval. |
| Learned browser skills saved to Gyan-Bhandar | IMPLEMENTED CANDIDATE PIPELINE / RUNTIME VERIFY | Recovered locators and successful recorded workflows compile to distinct guidance-only skill candidates with evidence. Benchmark/verification is still required for Stable promotion. |
| Optional GitHub browser implementations | IMPLEMENTED ADAPTER REGISTRY / ENVIRONMENT-DEPENDENT | Browser Harness, browser-use, agent-browser, BrowserCode, OpenDevBrowser, Rustwright, Lucarne, Promptwright, Skyvern, rrweb and Cereon are discoverable capability adapters/providers. They are not auto-installed or auto-authorized. |
| UI Guardian + Developer verification share browser authority | VERIFIED boundary | Both use the Browser Fabric inspector boundary rather than defining a second public browser authority. |
| Legacy duplicate Garudanetra service | DEPRECATED COMPATIBILITY ONLY | `garudanetra.py` is marked legacy; active runtime authority is `browser_fabric.py` + `garudanetra_session.py`. |
| Browser E-drive reconciliation | IMPLEMENTED / RUNTIME VERIFY | Audit now inventories `browser-data`, `playwright-browsers`, Garudanetra state/profiles, adapter environment and related browser processes without deleting user data. |

## 4. Gyan-Bhandar

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Evidence-backed long-term memory | VERIFIED boundary | Candidate/verified learning APIs and approval UX exist. |
| Working / episodic / semantic / graph / skill / evidence memory facade | IMPLEMENTED / RUNTIME VERIFY | Typed memory kinds are enforced in MemoryFabric/Gyan-Bhandar, inventory is exposed by API and the UI can filter/inspect each category. |
| Provenance, confidence and explicit promotion | IMPLEMENTED / RUNTIME VERIFY | Learning and pending-approval records now preserve memory kind, provenance, confidence, evidence and approval state. |
| Supersession of outdated knowledge | IMPLEMENTED / RUNTIME VERIFY | Replacement knowledge is proposed through the approval queue; on approval the previous fingerprint becomes superseded and links to its replacement. Graft remains an optional backing adapter. |
| Code intelligence links from Codebase-Memory | PARTIAL | Optional CBM adapter exists; E:\KRISHNA-CBM / CBM-Runtime must be audited and connected. |


## 4A. BRAHMA learning governor

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| One internal learning governor for mobile / PC / system observations | IMPLEMENTED / RUNTIME VERIFY | `BrahmaBot` classifies source/modality, applies bounded active-learning value, checks existing Rishi knowledge first and decides whether new learning is warranted. It is an internal capability, not a MAIN MENU item. |
| Learning belongs to the Rishis | IMPLEMENTED / RUNTIME VERIFY | BRAHMA routes accepted candidate observations into the selected lead Rishi's persistent learning ledger; it does not write field observations directly into trusted Gyan. |
| Required information comes from Rishi knowledge | IMPLEMENTED / RUNTIME VERIFY | `brahma.retrieve` selects the relevant Rishi team and returns scoped `knowledge_packet` findings/open questions before new research is requested. |
| Mobile-first learning policy | IMPLEMENTED / DEVICE VERIFY | Mobile provides bounded high-value observation/evidence; deep research/cross-checking remains on the PC. Hawkeye learning capture and curated evidence ingest now call BRAHMA. |
| PC learning policy | IMPLEMENTED / RUNTIME VERIFY | PC/document/code/research inputs can be routed to Rishi learning/research with provenance. |
| Gyan-Bhandar QC head | IMPLEMENTED / RUNTIME VERIFY | Production knowledge proposals route through Rishi intake + BRAHMA QC before the existing Gyan proposal/owner-approval path; low-maturity knowledge remains with the Rishis. |
| Evidence vs knowledge boundary | IMPLEMENTED / RUNTIME VERIFY | Raw/operational evidence may be stored as evidence/episodic memory; direct semantic/skill/graph stores are blocked so they cannot bypass Rishi/BRAHMA learning QC. |
| QC provenance / evidence / maturity / contradiction gates | VERIFIED BY UNIT CONTRACTS / CI PENDING | Candidate promotion requires traceable provenance, evidence, confidence, maturity and no unresolved contradiction; only strong L4+ evidence may be marked verified. |
| Gautama and Veda Vyasa remain evidence reviewer/compiler | VERIFIED boundary | BRAHMA governs routing/QC and does not replace Gautama epistemic review or Veda Vyasa compilation. |
| No silent direct truth write | VERIFIED boundary | BRAHMA creates a Gyan proposal only after QC; Gyan-Bhandar keeps durable memory authority and its normal approval path. |
| Bi-temporal knowledge history | IMPLEMENTED / RUNTIME VERIFY | BRAHMA records valid-time and learned-time separately, preserves superseded claims, and supports point-in-time queries without deleting history. |
| Source-family / contamination control | IMPLEMENTED / RUNTIME VERIFY | Evidence is grouped into independent source families so copied/related sources do not inflate evidence counts; source independence is attached to BRAHMA QC provenance. |
| Cost-aware Learning Value Score | IMPLEMENTED / RUNTIME VERIFY | Learning decisions combine uncertainty, novelty, evidence quality, importance, future reuse and Rishi knowledge gap, discounted by compute/network/storage cost. |
| Idle/sleep-time consolidation | IMPLEMENTED / RUNTIME VERIFY | A low-frequency BRAHMA scheduler runs deterministic consolidation + freshness decay only when KRISHNA is Idle, CPU/RAM are below configurable limits, and ResourceGovernor grants a non-blocking slot. It never performs deep model/Rishi research itself and never directly promotes to Gyan. |
| Memory evaluation harness | IMPLEMENTED / RUNTIME VERIFY | BRAHMA reports retrieval precision/recall/F1 plus duplicate, stale, contradiction and provenance-completeness metrics; external LoCoMo/LongMemEval/BEAM adapters remain optional future benchmark connectors. |
| Contradiction graph | IMPLEMENTED / RUNTIME VERIFY | Contradictory temporal claims are linked and resolved without erasing either claim or its evidence history. |
| Provenance fingerprinting | IMPLEMENTED / RUNTIME VERIFY | Learning/QC derives stable SHA-256 provenance fingerprints across source references and evidence metadata. |
| Rishi knowledge graph / council formation | IMPLEMENTED / RUNTIME VERIFY | BRAHMA emits lead/collaborator/Gautama-review/Vyasa-compile relationships and shared-domain edges for each learning topic. |
| Independent Rishi teach-back | IMPLEMENTED FOUNDATION / RUNTIME VERIFY | BRAHMA creates blinded challenges for a different Rishi and scores conclusion/evidence reconstruction before a result can be treated as additional verification evidence. |
| Freshness / forgetting / decay | IMPLEMENTED / RUNTIME VERIFY | Time-sensitive claims receive volatility-aware TTL review; stale knowledge is marked for re-verification and never silently deleted. |

## 5. NARAD

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Native automation/messenger control plane | VERIFIED boundary | Durable workflow lifecycle and policy gates. |
| Lean n8n-pattern workflow graph | IMPLEMENTED / RUNTIME VERIFY | Native typed DAG nodes, explicit dependencies, action/job dispatch and safe data mapping are implemented without embedding the n8n runtime. |
| Sudarshan workflow authority | IMPLEMENTED / RUNTIME VERIFY | Production NARAD binds to Sudarshan; every node enters Action/Job permission gates and leaves through IndependentCriticVerifier. |
| Bounded retry/backoff | IMPLEMENTED / RUNTIME VERIFY | Retry max is bounded; side-effecting external steps do not retry unless explicitly retry-safe. |
| Durable checkpoints/resume | IMPLEMENTED / RUNTIME VERIFY | Incomplete runs persist completed node receipts/outputs in the existing NARAD state file; resume skips already verified nodes. |
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
17. Shared Action Bus, Agent Runtime, Jobs, Permissions, MCP/A2A adapter and Dispatch acceptance pass.
18. Priority operational UI controls produce real action receipts and desktop/mobile action state remains coherent.
19. NARAD runs in typed-dag/sudarshan mode, checkpoint/resume and retry contracts pass, and no embedded n8n runtime is required.


## 14. Project Perfection / Design Studio

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Deadline-driven HR sizing | IMPLEMENTED / RUNTIME VERIFY | `DeadlineHR` sizes bounded parallel workers from serial/parallel estimates and deadline budget. |
| Recursive route/state discovery | IMPLEMENTED / RUNTIME VERIFY | Garudanetra/Playwright same-origin crawler records pages, controls, fields, state hashes and edges; potentially mutating controls are skipped by default. |
| X/Y geometry verification | IMPLEMENTED / RUNTIME VERIFY | Multi-viewport DOM boxes are checked for overflow and substantial overlap. |
| Permanent deterministic regressions | IMPLEMENTED / RUNTIME VERIFY | Generated route regression source + persistent manifest + runner; repaired defects persist detector evidence in Immune Memory. |
| Accessibility | IMPLEMENTED / RUNTIME VERIFY | Semantic sanity checks plus optional/strict local axe-core execution. |
| Visual regression | IMPLEMENTED / RUNTIME VERIFY | Controlled golden baseline storage and pixel diff; intentional selected redesign creates a new approved baseline only after candidate verification. |
| Hawkeye UI perceptual review | IMPLEMENTED / RUNTIME VERIFY | Local-only VisionAdapter reviews bounded page/viewport screenshots for high-confidence visible defects; it cannot override deterministic evidence and fails honestly when the local vision model is unavailable. |
| Performance gates | IMPLEMENTED / RUNTIME VERIFY | Browser timing metrics are checked against explicit thresholds when required. |
| API property/fuzz testing | IMPLEMENTED ADAPTER / RUNTIME VERIFY | Schemathesis adapter; verified deploy provisions the dependency locally on E:. |
| Mutation testing | IMPLEMENTED / RUNTIME VERIFY | Reversible mutations run only inside isolated candidates and must be detected by verification. |
| Browser chaos | IMPLEMENTED / RUNTIME VERIFY | Ephemeral-context API 500/abort, offline reload, denied permissions and double-click scenarios. |
| Candidate auto-repair | IMPLEMENTED / RUNTIME VERIFY | Up to three bounded model-assisted repair rounds; KABACH filters patches; no live tree mutation during repair. |
| Independent Critic + QA worker review | IMPLEMENTED / RUNTIME VERIFY | Completion gates feed IndependentCriticVerifier and bounded ephemeral QA reviewers. |
| Definition of Done certificate | IMPLEMENTED / RUNTIME VERIFY | Missing/failed required gate produces NOT_COMPLETE; percent-complete cannot override evidence. |
| Windows EXE retest | IMPLEMENTED CI / RUNTIME VERIFY | Windows workflow builds EXE then launch/restart retests it. |
| Android APK retest | IMPLEMENTED CI / DEVICE VERIFY | Android workflow boots emulator, installs/launches/backgrounds/restarts APK and inspects fatal logs. |
| iOS retest executor | IMPLEMENTED BOUNDARY / ENVIRONMENT-DEPENDENT | simctl executor exists; requires a macOS simulator/device and an iOS artifact. |
| Design web research | IMPLEMENTED / RUNTIME VERIFY | Garuda researches current public UI references; references are evidence/inspiration only. |
| Rendered A/B/C/D previews | IMPLEMENTED / RUNTIME VERIFY | Design Studio shows actual script-sandboxed rendered candidates; labels are selection handles, not abstract styles. |
| Submit → implement → verify → apply | IMPLEMENTED / RUNTIME VERIFY | Submit invokes bounded frontend implementation, candidate verification, transactional promotion, live post-apply verification and automatic rollback on failure. |
| Point/drag/speak editor | IMPLEMENTED / RUNTIME VERIFY | Garudanetra point selection maps live element metadata to candidate source; deterministic edits or bounded semantic model edits run in isolated candidates. |
| One-command Finish Project | IMPLEMENTED / RUNTIME VERIFY | `scripts/FINISH_KRISHNA_PROJECT.ps1` runs the governed pipeline, auto-repair, independent review, verified apply, live post-apply verification and rollback. |
| Verified deployment integration | IMPLEMENTED / RUNTIME VERIFY | `DEPLOY_KRISHNA_ONCE.ps1` provisions Project Perfection dependencies and `ACCEPT_KRISHNA_RUNTIME.ps1` checks runtime/UI/action contracts. |

Project Perfection is not allowed to report RELEASE_GATES_PASSED unless all applicable required gates have evidence. Environment-specific hardware/provider checks remain runtime acceptance, not source-code claims.
