# LR Group Company OS

## Scope locked by owner

Active shared LR Group functions:
- LR Commerce — successor boundary for MANIBHADRA commerce/CRM capabilities.
- LR Sales — successor boundary for VANIJYA sales capabilities.
- LR HR — shared people, roles, recruitment, attendance/leave and worker lifecycle.
- LR CA — accounting/tax/GST preparation and compliance workflow; filing remains approval-gated.
- LR Legal — shared legal research/review based on NARADA legal capabilities; external filings/signatures remain approval-gated.
- LR Technology — software, infrastructure, security and internal automation.
- LR Production — delivery/production work management.
- LR Advertisement — campaign/content planning and approved publishing workflows.

Frozen until the owner supplies each project's own idea:
- LR Social Science
- LR Mines & Minerals
- LR FinTech
- LRS Motors

Frozen means no generated business architecture, no autonomous workflow, no UI assumptions and no mutation by LR Group OS.

## Architecture

Use a local-first modular monolith for the first production version. Keep one canonical identity/permissions/audit/workflow layer, with domain modules around it. This avoids duplicating auth, approvals, audit, tasks and company records while preserving module boundaries for later extraction.

KRISHNA remains supervisor/orchestrator, not the company database. LR Group owns company records. KRISHNA can dispatch governed work to LR Group through a narrow interface.

Core flow:

`request -> department boundary -> policy decision -> approval if required -> execution adapter -> audit receipt -> result`

The `lr_group_os.py` foundation implements the boundary, zero-spend gate, external-write gate, work queue, approval queue and hash-linked audit receipts.

## Migration map

Copy and adapt before removing anything from KRISHNA:
- `manibhadra_crm.py` -> LR Commerce CRM
- `manibhadra_commerce.py` -> LR Commerce Core
- `manibhadra_advisor.py` -> LR Commerce Advisor
- `commerce_expansion*.py`, `marketplace_adapters.py`, `affiliate_intent.py`, `revenue_engine.py` -> LR Commerce extensions
- `vanijya_sales.py`, `vanik_netra*.py` -> LR Sales
- `narada_legal.py` -> LR Legal
- shared `narad/` connector/runtime patterns stay reusable infrastructure until LR Group has equivalent tested connectors
- `zero_spend_policy.py`, approval and audit patterns remain enforced at both KRISHNA and LR Group boundaries during migration

Do not delete the KRISHNA originals until parity tests prove the LR Group copy works and KRISHNA references have been changed safely.

## Governance invariants

1. Autonomous spend limit is INR 0.
2. Any positive spend requires exact owner approval.
3. Tax/GST filing, legal filing/signature, financial writes, employee termination, publishing, external messaging, credential changes and destructive record actions require approval.
4. Read-only research and internal drafting may proceed without owner interruption.
5. Free-only AI remains the default. No automatic paid fallback.
6. Connectors report truthful state: connected, not configured, degraded/error; never fake success.
7. Every consequential action gets an audit receipt.
8. Frozen companies fail closed.

## Backend before UI

Do not build the final LR Group UI until backend migration/parity tests are green. UI research direction: human-readable attention-first home, compact navigation, command/search palette, role-aware views, progressive disclosure, Kanban only for staged workflows, tables for precise financial/legal/HR records, and explicit approval/audit surfaces.

Useful current open-source patterns reviewed before implementation include modular CRM/ERP systems with multi-tenancy/RBAC/audit, and agent runtimes with durable approvals and verifiable run journals. We use the patterns, not their code, unless license/dependency review explicitly approves reuse.

## Next implementation gates

1. Foundation governance tests green.
2. Create LR Commerce package and parity tests against MANIBHADRA CRM/commerce.
3. Create LR Sales package and parity tests against VANIJYA.
4. Create LR Legal package and parity tests against NARADA legal.
5. Implement LR HR and LR CA canonical schemas/workflows.
6. Implement LR Technology, Production and Advertisement task boundaries.
7. Add integration contract from KRISHNA to LR Group.
8. Run regression suite and only then begin final frontend implementation.
