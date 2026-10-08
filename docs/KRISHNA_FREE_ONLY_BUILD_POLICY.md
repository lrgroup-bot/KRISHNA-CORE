# KRISHNA Free-Only Build Policy

This policy governs the 50-gap implementation program and all future external-tool adoption.

## Hard rule

KRISHNA will not depend on paid, subscription-only, closed-source, cloud-only, or license-restricted capabilities that conflict with the owner's free-only/local-first policy.

When a required capability is not available under acceptable free/open-source terms:

1. Do **not** copy proprietary or restricted source code.
2. Study only lawful public material such as documentation, papers, standards, public behavior, public APIs, benchmarks, and freely licensed examples.
3. Search for a genuinely free/open-source equivalent and verify its license, security, privacy, maintenance, and unique value.
4. If no acceptable free equivalent exists, implement the **capability** natively in KRISHNA using KRISHNA's own architecture, interfaces, tests, evidence model, and Sudarshan governance.
5. Reproduce the requirement and acceptance behavior, not another product's protected implementation.

## External-tool boundary

A free/open-source external tool may be retained only when it provides specialist machinery that is uneconomical or unsafe to recreate and when it passes all acceptance tests.

External tools are untrusted/read-only evidence engines. They never own policy, approval, repair, promotion, deployment, spending, credentials, or system authority.

All state-changing actions continue through:

KRISHNA reasoning -> Sudarshan control plane -> Shared Action Bus -> policy/permission/approval -> bounded execution -> verification/rollback.

## Native-first decision order

For every capability gap:

1. ALREADY COVERED -> use the existing KRISHNA implementation.
2. EXTEND NATIVE -> strengthen the existing KRISHNA subsystem.
3. BUILD NATIVE -> implement the missing capability in KRISHNA.
4. FREE OSS INSTRUMENT -> install only if the specialist engine adds measurable unique value.
5. PAID/RESTRICTED -> reject as a dependency and return to steps 2-4.
6. DUPLICATE/NO UNIQUE VALUE -> reject.

## No cloning rule

KRISHNA may learn algorithms, failure modes, benchmark methods, architecture principles, standards, and public research from other systems, but KRISHNA must keep its own structure. We do not vendor or paste another project's implementation merely to obtain its feature.

If code is reused from a free/open-source project at all, it must be legally compatible, deliberately selected, minimal, attributable as required by its license, security-reviewed, and preferable to a native implementation. Whole-repository copying is not an implementation strategy.

## Free-only acceptance gate

Before an external tool can be installed permanently, record:

- exact project/version/commit;
- license and compatibility verdict;
- free-use verdict for KRISHNA's actual use case;
- local/offline capability;
- telemetry/account/cloud requirements;
- source/provenance/hash verification;
- isolation path under E:\Krishna-The GOD\tools;
- resource cost;
- benchmark against native KRISHNA;
- unique evidence it adds;
- acceptance-test results.

If any mandatory field is unknown, the tool remains unverified and cannot become a required KRISHNA dependency.

## Owner policy

Paid fallback is forbidden for this program. A paid product may be studied only through lawful public information to understand the problem it solves. The resulting KRISHNA implementation must be independently designed or use an acceptable free/open-source substitute.
