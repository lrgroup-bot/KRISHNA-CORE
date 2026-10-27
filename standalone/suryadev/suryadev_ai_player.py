"""Read-only, opt-in AI Learner embedded player adapter.

A FreeTube Electron .exe cannot be embedded in the existing local dashboard.
An owner-operated Invidious HTTP service may instead expose /embed/<video-id>
inside the existing AI Learner page. No software installation, proxying,
hidden account sessions, media download, source approval or learning credit.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

SCHEMA = "suryadev.ai-learner-player.v1"
ENV_KEY = "SURYADEV_LOCAL_INVIDIOUS_ORIGIN"


def local_invidious_origin(raw):
    """Permit explicit loopback service origins; reject arbitrary websites."""
    if not isinstance(raw, str):
        raise ValueError("Invidious origin must be text")
    raw = raw.strip()
    if not raw or len(raw) > 110:
        raise ValueError("Expected a short explicit loopback origin")
    try:
        u = urlsplit(raw)
        host = (u.hostname or "").casefold()
        port = u.port
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid Invidious origin") from exc
    if (u.scheme != "http" or host not in ("127.0.0.1", "localhost", "::1")
            or port is None or port < 1024 or port > 65535 or
            u.username or u.password or u.path not in ("", "/")
            or u.query or u.fragment):
        raise ValueError(
            "Invidious must be an owner-controlled loopback HTTP origin with a port")
    return "http://127.0.0.1:" + str(port)


def player_config(env=None):
    """No backend is enabled unless the owner explicitly configures its origin."""
    env = os.environ if env is None else env
    raw = str(env.get(ENV_KEY, "") or "").strip()
    result = {
        "schema": SCHEMA, "provider": "none", "configured": False,
        "in_page_only": True, "new_browser_window": False,
        "origin": "", "service_reachability_verified": False,
        "ad_free_claim_verified": False,
        "source_observation_verified": False,
        "study_evidence_verified": False,
        "reason": "No local Invidious service configured",
    }
    if not raw:
        return result
    try:
        origin = local_invidious_origin(raw)
    except ValueError as exc:
        return {**result, "reason": "Invalid player configuration: " + str(exc)}
    return {**result,
            "provider": "invidious-local",
            "configured": True,
            "origin": origin,
            "reason": "Configured local service; playback and ad-free behavior NOT yet verified"}


if __name__ == "__main__":
    import json
    print(json.dumps(player_config(), indent=2))
