# KRISHNA Security Operations Harness

This layer adapts useful architecture patterns from monitoring, defensive security,
domain operations and agent-harness projects without importing their full stacks.

## Components

- `security_soc.py`: defensive event normalization, IOC extraction and correlation.
- `threat_intel.py`: expiring advisory intelligence; never auto-blocks.
- `ops_monitor.py`: HTTP, TCP, DNS and TLS health primitives.
- `autonomy_harness.py`: persistent maker/checker verification state.

## Operating rules

1. Repository/runtime evidence is the source of truth.
2. Maker and checker roles are logically separated.
3. A change is not complete until deterministic checks pass.
4. External threat intelligence is advisory and must pass KABACH policy before action.
5. Active security testing is limited to explicitly authorized systems.
6. Secrets and credentials are never captured as evidence.
7. Heavy external service stacks are optional, not KRISHNA defaults.

## Next wiring

Sudarshan should publish health events to the event bus; KABACH/SOC consumes them.
Repair actions flow through existing approval and verification gates. Dependency/CVE
inventory should consume local manifests/SBOM data and produce remediation candidates,
not silently install or upgrade packages.
