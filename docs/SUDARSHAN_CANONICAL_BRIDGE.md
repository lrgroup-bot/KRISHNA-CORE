# Canonical SUDARSHAN Research Bridge — milestone 1

This PR connects the **existing** SUDARSHAN REA/MiroFish adapters to
KRISHNA's canonical `Orchestrator` rather than constructing another runtime,
learning database, permission engine or worktree manager.

## What changes

- `Orchestrator` instantiates `SudarshanCanonicalIntegration` during startup
  and registers two actions on the existing `SharedActionBus`.
- `sudarshan.research.observe` validates the project against
  `SudarshanProjectOrchestrator.start`, invokes the preexisting, allowlisted
  **REA or MiroFish** read-only integration, and queues a **non-verified**
  evidence record through `GyanBhandarAgent.propose`.
- `sudarshan.research.mission` accepts a pending proposal belonging to
  the same project and starts a **research** mission using the existing
  `BrahmagyanRuntime.create_mission`. It does not approve that evidence.
- Both actions run through KRISHNA's `SharedActionBus` with project scope,
  auditing, idempotency and the existing policy/permission resolver.
- `authorized=True` is *not* taken from incoming research adapter payloads.
  The bridge does not grant new permissions.
- Only local PC action origin is enabled by this initial integration; no
  mobile, job, agent or cloud source can dispatch these bridge actions.
- The REA binary must match the supervisor's configured
  `KRISHNA_REA_CLI_PATH` environment variable. It is **disabled when unset**.
  MiroFish uses the fixed loopback endpoint `http://127.0.0.1:5001`.
- Evidence digests are observations, not original source artifacts or proof
  that a product feature works. Neither action can approve release.

## How to use (owner-local proof only)

Run the canonical KRISHNA server and inspect the registered action list.
The new actions are visible via the existing local action registry.

Call them through the existing `/api/action-bus/dispatch` endpoint only
after authenticating through the owner's trusted local control surface.
The current loopback API's `approved` boolean is **not** independently
authenticated; secure owner-session proof is required before exposing this
integration on any network or treating action receipts as owner identity proof.

The observation payload must have:

```json
{
  "project_id": "project-id",
  "engine": "REA",
  "topic": "Feature discovery",
  "project_context": {
    "source": "owner",
    "repository": "/absolute/local/repo",
    "project_brain": {},
    "requirements": {},
    "architecture": {},
    "design": {},
    "dependencies": {},
    "tests": {},
    "deployment": {},
    "memory": {},
    "runtime": {}
  },
  "spec": {
    "root": "/absolute/local/repo",
    "target": "/absolute/local/repo",
    "rea_executable": "/absolute/path/from/KRISHNA_REA_CLI_PATH"
  }
}
```

For MiroFish, use `engine: "MiroFish"` and `spec` with a
`project_id` matching the action project and a **completed** local
`simulation_id`. It does not start new simulations.

The approved action envelope's project must equal the payload project.
A successful observation returns a pending Gyan approval ID and evidence
digest. To create a BRAHMAGYAN verification mission, issue the
`sudarshan.research.mission` action with `project_id` and `approval_id`.

**Do not** automatically decide that Gyan proposal, auto-apply coding
changes, generate an EXE, merge a PR or deploy KRISHNA based on these receipts.

## Validation

```bash
PYTHONPATH=core python -m unittest discover -s core/tests -p 'test_sudarshan_canonical_integration.py' -v
```

The tests use KRISHNA's actual project bootstrap, Shared Action Bus,
PermissionRuntime and PolicyKernel, with injected mock REA/MiroFish
results, Gyan queue and BRAHMAGYAN runtime. They prove wiring, scope and
blocking behavior, **not** the availability of live engines or a physical
Android device.

## Remaining gates

1. Supervisor-backed, authenticated per-action owner consent; local
   `approved=True` is currently caller-supplied on the existing API.
2. Run real REA and MiroFish instances on the authorized host; archive
   content-addressed raw evidence with privacy controls.
3. Join BRAHMAGYAN research outcomes to reviewed claims, existing
   Gyan-Bhandar knowledge and Rishi council evidence maturity.
4. Route approved engineering jobs through the *existing* canonical
   `GitWorktreeManager`; retire duplicate disposable-worktree helpers.
5. Connect UI Guardian and native Android verification, verified rollback,
   and independent post-deployment health checks.
6. End-to-end tests and owner's explicit merge/deploy authorization.

### Merge strategy

Draft PR targets the development branch
`feature/replica-audit-gates-20261018` so this bridge can be reviewed
separately from the earlier 63-commit adapter framework. It is **not** a
production promotion or a merge into the repository's actual default
branch `fix/krishna-ui-runtime-verification`.
