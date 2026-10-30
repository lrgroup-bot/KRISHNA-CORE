"""One local GARUDANETRA browser engine policy for the SURYADEV fleet.

The application owns browser sessions, workspace isolation, source approvals and
observer diagnostics. Playwright's *open-source Chromium* build supplies the
rendering engine; branded Chrome/Edge binaries and user browser profiles are
never selected. No browser binary is silently installed or downloaded.
"""
from __future__ import annotations

import os

GARUDANETRA_CHANNEL = "chromium"
GARUDANETRA_ENGINE = "garudanetra-owned-playwright-chromium"


def browser_channel():
    """Ignore obsolete branded-browser hints, never falling back to Chrome.

    The old SURYADEV_VIDEO_BROWSER_CHANNEL=chrome configuration can remain
    inherited from a pre-migration dashboard. It must not select Chrome.
    """
    return GARUDANETRA_CHANNEL


def require_garudanetra(channel=None):
    """Validate any explicitly requested engine (for CLI/probe safety)."""
    if channel is not None and channel != GARUDANETRA_CHANNEL:
        raise ValueError(
            "Only GARUDANETRA's managed Chromium engine is permitted; "
            "Google Chrome and Microsoft Edge channels are disabled")
    return GARUDANETRA_CHANNEL


def browser_identity():
    """Public, credential-free metadata for dashboard and evidence."""
    return {
        "browser_owner":"GARUDANETRA",
        "engine":GARUDANETRA_ENGINE,
        "browser_channel":GARUDANETRA_CHANNEL,
        "branded_browser_required":False,
        "obsolete_branded_channel_hint_ignored":(
            str(os.getenv("SURYADEV_VIDEO_BROWSER_CHANNEL") or "").strip().lower()
            in ("chrome","msedge")),
        "video_codec_verified":False,
        "source_learning_verified":False,
    }
