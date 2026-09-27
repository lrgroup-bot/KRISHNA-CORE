from __future__ import annotations

CURRICULUM = {
    "Taste Skill": ("design judgment", "variance-motion-density", "redesign audit", "selective skill loading"),
    "web-design": ("spec-first design", "PRD/reference-to-design-spec", "token extraction", "responsive-accessibility"),
    "Awesome Claude Design": ("design-system inspiration", "DESIGN.md patterns", "brand-IP separation"),
    "image-to-code": ("reference decomposition", "visual-to-token translation", "render-compare-repair"),
    "Playwright CLI": ("deterministic browser QA", "screenshots-snapshots", "interaction verification"),
    "Storybook": ("isolated component states", "component regression", "accessibility states"),
    "Stagehand": ("optional agentic browser recovery", "self-healing exploration", "deterministic fallback"),
    "electronics-repair": ("board identification", "power-path tracing", "rail sequencing", "component datasheets", "schematics-boardviews", "multimeter-oscilloscope measurements", "fault isolation", "microsoldering", "repair verification"),
    "electrical-repair": ("safe isolation", "power supplies", "motors", "relays", "protection devices", "wiring", "measurement practice", "post-repair load testing"),
    "salvage-reuse": ("donor compatibility", "harvestable parts", "repair-vs-parts decision", "reuse engineering", "failure-history learning"),
}

RULES = (
    "do-not-vendor-blindly",
    "preserve-provenance",
    "preserve-license",
    "no-protected-brand-copy",
    "candidate-before-verified",
    "store-success-and-failure",
    "retrieve-task-relevant-only",
    "never-invent-pinouts-or-rail-values",
    "measure-before-replace",
    "store-real-repair-success-and-failure",
    "verify-repair-under-safe-post-repair-test",
)
