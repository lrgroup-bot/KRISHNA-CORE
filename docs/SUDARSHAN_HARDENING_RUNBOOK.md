# SUDARSHAN hardened integration — operator and verification runbook

**Status:** development only. Full REA, MiroFish, Ollama, physical Android,
deployment and repair are not certified on the owner's machine. No auto merge,
spending or production deployment. No Windows EXE packaging before actual UI
testing and owner acceptance.

## Architecture (reuse, no replacement)

KRISHNA's existing `Orchestrator` owns the `SharedActionBus`,
`PermissionRuntime`, `SudarshanProjectOrchestrator`,
`BrahmagyanRuntime`, `GyanBhandarAgent`, `GitWorktreeManager`
and `MrityunjayRuntime`. No competing approval or learning databases are
introduced. New research evidence enters through existing
`sudarshan.research.observe` / `sudarshan.research.mission`
actions. The only new SQLite table holds **single-use consent nonces**
in KRISHNA's existing runtime database.

## 1. Set up host-local consent before any research invocation

Generate a 256-bit random secret on the owner-controlled PC using a secure
random source. Never commit, message or screenshot the secret.

```powershell
python -c "import secrets;print(secrets.token_hex(32))"
```

Protect it with the OS owner credential mechanism and supply it as
`KRISHNA_SUDARSHAN_CONSENT_KEY` **to both the KRISHNA server and the
local consent issuer**. The key must remain stable across KRISHNA restarts.
The default when missing is **DENY**.

Configure `KRISHNA_REA_CLI_PATH` to a previously installed, trusted **absolute**
REA executable path. Keep the MiroFish API bound to `127.0.0.1:5001`;
do not bind it to 0.0.0.0 or permit external access. An upstream MiroFish
configuration that depends on Zep Cloud is **not** zero-cost local operation.

For a signed action request, prepare an **exact** JSON payload (same
project specification and REA/MiroFish engine spec to be submitted, no
`owner_token` yet). In the repository root, issue the token **locally**:

```powershell
$env:PYTHONPATH="core"
python -m krishna_core.sudarshan_owner_consent --action sudarshan.research.observe --project PROJECT_ID --payload-json path\\to\\payload.json --db-path path\\to\\krishna-runtime.sqlite
```

Use the **actual** configured `settings.db_path` for `--db-path`.
The CLI prints a short-lived proof. Paste it into payload field
`owner_token` and dispatch that exact payload via KRISHNA's loopback
`/api/action-bus/dispatch` using `approved: true`, the same `project`
and `action: "sudarshan.research.observe"`. This token is bound to the
action, project and payload, expires after at most 300 seconds, and is
consumed once, including across server restarts. Any payload change
requires a **new** approval proof.

To turn pending evidence into a BRAHMAGYAN verification mission, sign a
**different** payload for action `sudarshan.research.mission`, supplying
`project_id` and an existing `approval_id`. Proposals remain **unverified**
until independently checked and approved by KRISHNA.

**Security limit:** Possession of the local secret is not a cryptographic
proof of a named person's identity. Host-local secret storage, OS-user
security and authenticated UI session integration still need deployment
review. Do not expose this to LAN or mobile. Existing generic action-bus
endpoints still require their own security audit.

## 2. Evidence is hash-linked and retained locally

Every **real** REA/MiroFish run through the canonical bridge writes the
raw bounded JSON output under KRISHNA's runtime
`sudarshan-evidence/<sha256(project)>/<engine>/<sha256>.json`.
The Gyan approval queue receives the matching `sha256:...` identifier.
The bridge **rejects** successful adapter claims if the bytes cannot be
verified in the project-scoped archive.

For local inspection, only after approval:

```python
from tools.sudarshan_evidence_archive import verify, load
assert verify(root, project_id, "REA", evidence_id)
raw_evidence = load(root, project_id, "REA", evidence_id)
```

This archive is not a digital signature or an independent product-behavior
test. Protect storage ACLs, apply retention/redaction policies, and never
push sensitive artifacts to Git or cloud services.

## 3. Browser and actual Android

UI Guardian's Playwright Chromium path disables service workers, blocks
requests to unapproved hostnames, tests configured controls, counts console
errors and archives actual screenshot evidence when configured with an
absolute `evidence_root` and a `project_id`.

Physical Android is different from browser mobile emulation. With
developer mode authorized and ADB on the owner PC, create a JSON spec:

```json
{
  "mode": "android",
  "adb_executable": "C:\\Android\\platform-tools\\adb.exe",
  "device_serial": "YOUR_DEVICE_SERIAL",
  "app_package": "com.example.yourapp",
  "expected_resource_ids": ["com.example.yourapp:id/main_button"],
  "project_id": "KRISHNA",
  "evidence_root": "E:\\krishna-evidence"
}
```

Replace all examples with the **verified actual** paths/serial/package.
Then run `python -m tools.sudarshan_native_cli --engine UI_GUARDIAN
--spec path\\to\\android.json --approve-local-run`.

The current physical Android adapter inventories and asserts UI controls;
it does **not** install APKs, tap every button or change device settings.
A guarded Appium/UiAutomator action suite, emulator/test account and user
approved action coverage remain required for a full native test.

## 4. Canonical coding / recovery

The VISHWAKARMA proposal runner now uses KRISHNA's existing
`GitWorktreeManager`. The original checkout remains untouched and
proposals require owner review. A Git worktree is **not** an OS sandbox:
unknown code must run with Windows restricted-token / VM isolation.

Mrityunjaya's local integrity verifier hashes nonignored tracked and
untracked file bytes in addition to Git HEAD/status; previously a dirty
file could change without a changed status string. Ignored files are
explicitly not covered. This is not live deployment rollback: the existing
KRISHNA transactional promotion/recovery runtime remains the only
authorized live-repair mechanism.

## 5. CI and remaining exit gates

```powershell
python -m compileall -q tools tests core
python -m unittest discover -s tests -p "test_sudarshan*.py" -v
$env:PYTHONPATH="core"
python -m unittest discover -s core/tests -p "test_sudarshan_canonical_integration.py" -v
python -m unittest discover -s core/tests -p "test_sudarshan_owner_consent.py" -v
```

The draft PR must not be marked ready for release until:
1. all applicable GitHub CI checks pass and no unrelated regressions occur;
2. real REA, actual compatible local MiroFish and local Ollama are installed;
3. entire browser UI, real Android app, and native UI flows are verified;
4. owner sessions are authenticated and the consent secret is protected;
5. raw evidence is retained securely and Gyan/claims are independently reviewed;
6. verified repair and rollback survive crash/restart tests on the live host;
7. Windows runtime and deployment are rechecked after explicit merge approval.

**No script in this PR installs software, purchases compute, auto-merges,
auto-deploys or promotes a failing run.**
