# KRISHNA Spatial Command OS — UI Contract

Status: candidate only. This document does not authorize deployment or promotion.

## Purpose

KRISHNA must be understandable to the owner without exposing backend implementation details by default. Every internal system uses one visual grammar, one status language and one owner-facing dashboard pattern.

## Visual identity

- Deep black/navy canvas
- KRISHNA gold as identity/accent
- Cyan for intelligence/active information
- Emerald for working/success
- Gold for idle/ready
- Blue for healing/recovery
- Amber for waiting on Partha
- Red only for blocked/error/attention
- Layered dark glass surfaces
- Professional shallow 3D system controls
- No decorative motion that does not communicate state
- Reduced-motion support is mandatory

## System rail contract

Every upper KRISHNA system button must show:

1. Distinct short mark/glyph
2. Human-readable system name
3. Current state label
4. Current-state light
5. Keyboard focus and hover state
6. Owner-readable tooltip

The upper system rail may horizontally scroll on smaller widths but system names must remain visible on desktop.

## Universal system dashboard

Clicking any system opens the same information grammar:

1. What this system does
2. Working now
3. Progress
4. Completed recently
5. Problems
6. Needs Partha
7. Next
8. Recent history
9. Advanced / evidence

Technical JSON, internal IDs and raw telemetry remain under Advanced / evidence by default.

## Status language

- WORKING — green
- IDLE — gold
- HEALING — blue
- WAITING — amber
- BLOCKED — red
- UNKNOWN — grey

A healthy idle system must never appear red.

## Sudarshan command surface

The default composer is command-first. Manual File, Plugin, Project, Investigate and Research mode buttons are hidden from the normal command surface. KRISHNA decides when research/investigation is needed and may expose secondary controls in the appropriate workspace when required.

Default placeholder:

`Tell KRISHNA what you want done…`

Primary action:

`RUN`

## Authority boundary

The Spatial Command OS is presentation only. It must never mint approval, execute a mutating action, bypass Sudarshan, promote code, deploy runtime changes or elevate an internal worker to decision authority.

## Promotion gate

The candidate UI may replace the current dashboard only after:

- build passes
- operational dashboard Playwright contract passes
- UI Guardian desktop/tablet/mobile viewport matrix passes
- no regression in KRISHNA/Sudarshan functionality
- owner review and explicit promotion approval

The verified existing dashboard remains rollback authority until promotion is complete.
