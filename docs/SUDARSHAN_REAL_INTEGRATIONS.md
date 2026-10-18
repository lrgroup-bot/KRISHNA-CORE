# SUDARSHAN real-adapter integration and verification

This branch provides real local execution entry points, not a promise that REA,
MiroFish, Playwright or an AI coding CLI is already installed on the owner's PC.

## Requirements

- Python 3.11 or newer; Git for disposable VISHWAKARMA worktrees.
- REA: independently installed `rea-agents` CLI with a supported Node.js version;
  see https://rea.tools/ . No auto-downloading or paid decompiler setup.
- MiroFish: explicitly started local backend on port 5001 with a *completed*
  simulation and completed report. Original MiroFish may require cloud Zep/API
  services; those do **not** meet KRISHNA's local-first/free-only policy.
  Any local fork must be separately vetted for compatible API endpoints.
- UI Guardian: `pip install playwright`, then `python -m playwright install chromium`
  on the machine running tests. Mobile mode is browser emulation, not native APK testing.
- BRAHMAGYAN: Ollama listening locally on 127.0.0.1:11434; an installed local
  model such as `qwen3:8b`. Never forward project content to hosted APIs.
- VISHWAKARMA: trusted explicitly configured local coding CLI plus test command.
  A Git worktree protects the original checkout, **not** the host filesystem or
  network from a malicious process. Run unknown tools only inside an OS sandbox.
- MRITYUNJAYA: a baseline snapshot captured before coding, for later integrity
  comparison. It does not perform destructive resets.

## Run one real adapter

From the KRISHNA-CORE repository root, create a local JSON spec file and run:

```powershell
python -m tools.sudarshan_native_cli --engine UI_GUARDIAN --spec C:\\sudarshan\\ui.json --approve-local-run
```

Example `ui.json` for a locally running application:

```json
{
  "plan": {
    "url": "http://127.0.0.1:8766/health",
    "device": "desktop",
    "steps": [
      {"action": "expect_visible", "selector": "body"}
    ]
  }
}
```

The REA JSON spec requires `target`, `root`, and an absolute
`rea_executable` path. The target must remain under the explicitly authorized
root. REA runs `analyze-javascript-application <target> --json`.

The MiroFish JSON spec requires `simulation_id` and `project_id`; optional
`base_url` defaults to `http://127.0.0.1:5001`. It calls the **read-only**
documented API `GET /api/simulation/<id>` and
`GET /api/report/by-simulation/<id>`. It does not start a costly simulation.

BRAHMAGYAN spec fields: `db_path`, `project_id`, `feature_id`, and
`mode`. Mode `propose` also requires `rishi`, `source_text`,
`evidence_ids` and `model`. Proposed findings remain pending. For mode
`approved`, only previously reviewed findings count as knowledge. Use
`review_lesson(db, project_id, feature_id, id, 'approved', reviewer)` in an
owner-authorized review interface; the current SQLite API itself is not an
authenticated multiuser approval system.

VISHWAKARMA spec fields: `repository`, `code_argv`, `test_argv`,
`output_dir` (outside the source repository). Both commands must start with
an absolute executable path. It exports proposed changes to a local ZIP for
review and automatically discards the temporary worktree. Never auto-apply
the ZIP without an explicit reviewed patch and regression tests.

MRITYUNJAYA spec: `{"baseline": <snapshot>}`, where `snapshot` is the
dictionary returned by `tools.sudarshan_mrityunjaya.baseline(repository)`
**before** the coding run. It verifies that the original checkout is unchanged.

## Existing six-agent pipeline

`python -m tools.sudarshan_cli --config <config.json> --approve-local-run`
accepts a `config.json` with `project_id`, `feature_id`, `db_path`,
and all six `adapters`. Every adapter entry supplies:

```json
{
  "argv": [
    "<absolute path to Python executable>",
    "-m", "tools.sudarshan_native_cli",
    "--engine", "REA",
    "--spec", "<absolute local REA JSON spec>",
    "--approve-local-run"
  ],
  "cwd": "<absolute KRISHNA-CORE checkout path>",
  "timeout": 120
}
```

Create one entry each for REA, MiroFish, BRAHMAGYAN, VISHWAKARMA,
UI_GUARDIAN and MRITYUNJAYA. Incomplete configurations are rejected
*before* execution. A blocked, failed, or untested stage stops the pipeline.

**No implementation, merge, push, release, deployment, or live repair is
authorized by a green adapter status.** The 35 release gates remain
fail-closed pending independent verification and owner signoff.

## Test

```powershell
python -m compileall -q tools tests
python -m unittest discover -s tests -p "test_sudarshan*.py" -v
```

The contract tests mock external REA/MiroFish services and do not verify a real
host installation. A separate owner-approved end-to-end test with local services
running and retained logs is necessary.

## Upstream references

- REA: https://rea.tools/ and https://github.com/morluto/rea
- MiroFish: https://github.com/666ghj/MiroFish
- MiroFish API: `backend/app/api/simulation.py` and `backend/app/api/report.py`

This document is not evidence of on-device installation or successful operation.
