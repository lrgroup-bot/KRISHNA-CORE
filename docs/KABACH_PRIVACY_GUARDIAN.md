# KABACH Privacy Guardian

KABACH Privacy Guardian is an internal KRISHNA capability for defensive privacy measurement, regression testing, release gating and self-protection. It is **not** a separate app, is **not** a permanent MAIN MENU item, and is **not** an anti-detection or tracking-evasion system.

## Runtime ownership

```
KRISHNA
  -> KABACH Privacy Guardian
      -> Garudanetra Browser Fabric (browser probes)
      -> optional KRISHNA-controlled Network Probe (IP/header/TLS observation)
      -> KRISHNA Mobile APK audit / optional external MobSF service
      -> Privacy Evidence Store
      -> Gyan-Bhandar safe evidence summary
  -> Sudarshan (action verification / release decision evidence)
```

The Privacy Guardian deliberately reuses KRISHNA's existing Shared Action Bus, Permission Runtime, Sudarshan control plane, Garudanetra browser implementation, DPAPI secure-storage primitives, memory/Gyan-Bhandar, and event bus.

## Implemented executable lanes

### Browser

The canonical Garudanetra/Playwright engine can run a temporary isolated context and collect browser-visible privacy surfaces:

- User-Agent and User-Agent Client Hints
- language/platform/timezone/screen
- hardware concurrency/device memory/touch surface
- WebGL availability and renderer exposure
- local canvas rendering sample (stored only as a hash in normalized evidence)
- AudioContext sample (hashed in normalized evidence)
- DOMRect and TextMetrics
- GPC/DNT state
- browser permission-query states without activating sensors
- storage/API availability
- WebRTC candidate **types** and mDNS state without retaining raw candidate values
- third-party request domains
- local SHA-256 self-linkability identifier; never uploaded by default

A single result never claims that a fingerprint is stable, randomized or anonymous. Stability/linkability requires compatible repeated/profile runs.

### Tracking

- known tracking-parameter cleaner with before/after output
- unknown/functional query parameters preserved by default
- local tracker-provider abstraction
- evidence-only cross-site behavior learner; one observation never auto-blocks a domain

No licensing-restricted tracker database is bundled.

### Web endpoint

Owned endpoints can be checked for:

- HTTPS and redirects
- HSTS
- CSP
- Referrer-Policy
- Permissions-Policy
- X-Content-Type-Options
- frame protections
- COOP/CORP/COEP/CORS observations
- Set-Cookie security metadata without retaining cookie values

Third-party endpoints may be observed but are not graded as if KRISHNA controls them.

### KRISHNA Mobile

The local APK audit performs:

- SHA-256 identity
- conservative DEX tracker-signature observation
- cleartext non-loopback HTTP host-string observation
- manifest permission inventory when Android aapt/aapt2 is available

The real mobile build workflow gates the generated APK through this scanner. Static evidence is not treated as equivalent to real-device dynamic testing.

### Baselines / regression

Privacy history stores test-suite and test-case provenance. Baselines can be compared before/after browser updates, KRISHNA changes, profile changes, VPN changes or configuration changes. Incompatible test-suite versions are marked rather than silently compared.

### Local-first evidence

Normalized history is redacted. Sensitive network/device/fingerprint evidence is persisted only through Windows DPAPI; where secure persistence is unavailable, raw sensitive evidence is deliberately discarded and only a digest/reference is kept. General Gyan-Bhandar receives only compact privacy-safe summaries/evidence references.

## Conditional/external lanes

These cannot be truthfully completed by source code alone:

- **Public IP / remote header / TLS or base-JA4 observation** — requires an explicitly configured `KRISHNA_PRIVACY_PROBE_URL`. Remote probes must use HTTPS.
- **DNS resolver leak test** — requires an owner-controlled authoritative DNS service/domain with short-lived test tokens.
- **MobSF dynamic/static service integration** — MobSF remains an independent GPL service. The current adapter reports configuration honestly and does not embed it.
- **OpenWPM research mode** — external isolated Linux/WSL/Docker service only; GPL code is not merged into KRISHNA Core.
- **Exodus / AmIUnique / EXADPrinter** — methodology/provider boundaries only; restrictive code is not copied into core.
- **Full mobile release acceptance** — requires a real generated KRISHNA APK plus real-device dynamic traffic/permission testing.
- **Normal-profile vs incognito vs fresh-profile equivalence claims** — invasive tests default to isolated contexts. The owner's normal profile is not modified unless explicitly authorized.

## Actions

All operational calls go through Shared Action Bus / Sudarshan:

- `kabach.privacy.audit`
- `kabach.privacy.clean_url`
- `kabach.privacy.baseline.save`
- `kabach.privacy.baseline.compare`
- `kabach.privacy.release_gate`

Capabilities are scoped to `privacy.read`, `privacy.write` and `release.verify`.

## Contextual HTTP API

- `GET /api/kabach/privacy/status`
- `GET /api/kabach/privacy/history`
- `GET /api/kabach/privacy/metrics`
- `POST /api/kabach/privacy/audit`
- `POST /api/kabach/privacy/clean-url`
- `POST /api/kabach/privacy/baseline`
- `POST /api/kabach/privacy/compare`
- `POST /api/kabach/privacy/release-gate`

These are internal contextual APIs; no Privacy Guardian sidebar item is added.

## Release-policy semantics

Privacy findings use descriptive classes rather than a fake universal score:

- LOW EXPOSURE
- MODERATE EXPOSURE
- HIGH LINKABILITY
- CONFIGURATION INCONSISTENCY
- PRIVACY REGRESSION
- UNSUPPORTED
- INCONCLUSIVE

An audit can execute correctly and still report a privacy problem. Sudarshan verifies that the audit/action executed correctly; the configured privacy release gate decides whether the observed result blocks a release. Informational findings do not block unless the policy says they are required.

## Acceptance evidence

Repository CI includes:

1. unit tests for redaction, link cleaning, browser normalization, regression, release policy and synthetic APK parsing;
2. live HTTP integration against the actual KRISHNA server routes;
3. a dedicated Windows Playwright job that launches the real browser privacy route against the KRISHNA dashboard;
4. the KRISHNA Mobile build workflow scanning the actual generated APK before artifact upload.

User-machine/full Definition of Done still requires:

- run `scripts/CHECK_KABACH_PRIVACY.ps1` against the deployed E: runtime;
- configure and verify an owner-controlled external network/DNS probe before claiming IP/DNS/TLS leak coverage;
- scan and dynamically exercise the real installed KRISHNA Mobile APK on the owner's device;
- retain the exact audit evidence and Sudarshan release decision.

Never report "fully anonymous", "untraceable", "impossible to fingerprint" or "100% private". Report what was tested, what was observed, what remains unknown, and what can realistically be improved.
