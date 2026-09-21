# GARUDANETRA Browser Fabric

Garudanetra is KRISHNA's browser/computer capability layer. Garuda is the separate research/evidence scout. KRISHNA remains the only decision authority.

## Canonical ownership

```text
KRISHNA
  |
  +-- Garuda ---------------- research/discovery/evidence
  |
  +-- Garudanetra Browser Fabric
        |
        +-- GarudanetraSessionManager ---- live browser session authority
        +-- BrowserOperator -------------- bounded inspection/verification
        +-- BrowserRecoveryAdapter ------- deterministic + optional recovery
        +-- UI Guardian ------------------ viewport verification consumer
        +-- DevelopmentOperator ---------- frontend/API verification consumer
```

The server must import `GarudanetraBrowserFabric`. The older `garudanetra.py::GarudanetraService` is compatibility-only and must not become a second runtime authority.

## Canonical engine

Playwright/Chromium is the canonical verified engine. Optional projects never silently replace it.

Runtime assets live on E::

```text
E:\Krishna-The GOD\.venv\...
E:\Krishna-The GOD\playwright-browsers
E:\Krishna-The GOD\state\garudanetra
E:\Krishna-The GOD\garudanetra\profiles
E:\Krishna-The GOD\downloads\garudanetra
```

`E:\Krishna-The GOD\browser-data` is treated as legacy data until explicitly reconciled. Audits report it; they do not delete or migrate it automatically.

## Native fabric capabilities

### Observe
- rendered visible text;
- bounded console and network evidence;
- tabs/downloads;
- screenshots/frames;
- semantic interactive-element map using session-scoped `e1/e2/...` refs;
- role/name/tag/geometry metadata;
- sensitive URL query values redacted.

### Act
- navigate/back/forward/reload;
- new/switch/close tab;
- click/double click;
- fill/type/keypress;
- hover/focus;
- select/check/uncheck;
- scroll/scroll-into-view;
- pointer click/drag for owner takeover;
- bounded runtime-file upload.

### Stream
Garudanetra prefers Chrome DevTools Protocol `Page.startScreencast` and stores the latest JPEG frame. If CDP screencast is unavailable it falls back to bounded PNG screenshots. The UI consumes the same frame API regardless of transport.

### Recover
Recovery order:
1. current selector or semantic ref;
2. deterministic role/name/label/placeholder/text recovery;
3. explicitly configured Browser Harness bridge;
4. explicitly configured vision-recovery bridge.

External recovery sees only bounded temporary evidence and its result is untrusted. It must resolve to a real page locator before use.

### Record and replay
Browser actions are recorded in memory. Task-Memory/Persistent sessions can persist the evidence trail. Fill/type values are redacted unless the caller explicitly sets `remember_value=true`.

Safe navigation/observation actions may be queued for replay. Consequential interactions such as click/fill/type/upload require explicit replay approval. Redacted values cannot be replayed.

### Learn
Task Memory can propose:
- recovered selector candidates;
- successful multi-step recorded workflows.

Each candidate is compiled as guidance-only with a distinct session-derived name and stored in Gyan-Bhandar as a candidate skill. Stable promotion still requires independent verification/benchmark evidence.

## Optional browser providers

`BrowserAdapterRegistry` discovers capabilities without granting authority.

| Adapter | Intended capability |
| --- | --- |
| Browser Harness | recovery helpers / reusable browser helpers |
| browser-use | optional semantic task planner |
| agent-browser | accessibility refs, CDP, streaming, WebMCP concepts |
| BrowserCode | reusable CDP/browser scripts |
| OpenDevBrowser | refs, active-tab/managed session concepts, diagnostics |
| Rustwright | optional native CDP engine experiment |
| Lucarne | watch/takeover/record session concepts |
| Promptwright | workflow recording/replay concepts |
| Skyvern | optional vision-assisted recovery |
| rrweb | optional record/replay provider |
| Cereon Browser Operator | optional dedicated real-browser extension endpoint |

These are not automatically installed, selected or executed. Availability is environment-dependent and surfaced by `/api/garudanetra/fabric`.

## Runtime adapter configuration

Optional adapters can be enabled without editing KRISHNA source. Create:

```text
E:\Krishna-The GOD\config\browser-runtime.ps1
```

Example:

```powershell
$env:KRISHNA_BROWSER_HARNESS_CMD = 'E:\Krishna-The GOD\tools\browser-harness\browser-harness.exe'
$env:KRISHNA_AGENT_BROWSER_CMD = 'E:\Krishna-The GOD\tools\agent-browser\agent-browser.exe'
$env:KRISHNA_LUCARNE_CMD = 'E:\Krishna-The GOD\tools\lucarne\lucarne.cmd'
# Configure only adapters actually installed and verified on this PC.
```

START_KRISHNA.ps1 loads this runtime-owned file when present. The file is not deployed from Git and can remain machine-specific.

## Environment bridge variables

```text
KRISHNA_BROWSER_HARNESS_CMD
KRISHNA_BROWSER_VISION_RECOVERY_CMD
KRISHNA_AGENT_BROWSER_CMD
KRISHNA_BROWSERCODE_CMD
KRISHNA_OPENDEVBROWSER_CMD
KRISHNA_RUSTWRIGHT_CMD
KRISHNA_LUCARNE_CMD
KRISHNA_PROMPTWRIGHT_CMD
KRISHNA_SKYVERN_CMD
KRISHNA_RRWEB_CMD
KRISHNA_CEREON_BROWSER_ENDPOINT
```

External commands must be explicitly configured by the owner/runtime. They never become KRISHNA authority.

## APIs

```text
GET  /api/garudanetra/fabric
GET  /api/garudanetra/sessions
GET  /api/garudanetra/session?id=<session>
GET  /api/garudanetra/frame?id=<session>
GET  /api/garudanetra/semantic?id=<session>
GET  /api/garudanetra/recording?id=<session>

POST /api/garudanetra/session/start
POST /api/garudanetra/session/control
POST /api/garudanetra/session/replay
```

## Release acceptance

Runtime acceptance verifies:
- canonical Browser Fabric owner and Playwright engine;
- live browser frame;
- CDP stream state or explicit fallback warning;
- semantic observer;
- replay approval gate;
- action recording;
- private/task-memory/persistent approval behavior;
- UI Guardian viewport verification.

No optional adapter is reported active merely because its source repository exists.
