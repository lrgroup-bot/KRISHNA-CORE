"""GARUDANETRA Media Lite: one supervised, source-approved YouTube browser lane.

Not a second scheduler or browser engine. Playwright owns a local Chrome/
Chromium context. This layer validates the source, refuses unsafe redirects,
observes player state, and turns media teardown into explicit diagnostics.
It never downloads media, bypasses ads, seeks past content, or asserts mastery.
No account cookies or credentials are exported in evidence.
"""
from __future__ import annotations

import ipaddress
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit


def approved_youtube_watch(url):
    """Accept a single HTTPS public watch URL; caller must separately approve it."""
    value = str(url or "").strip()
    try:
        u = urlsplit(value)
        query = parse_qs(u.query, strict_parsing=True)
        ok = (u.scheme == "https" and u.hostname in
              ("www.youtube.com", "youtube.com", "m.youtube.com")
              and u.path == "/watch" and u.port in (None, 443)
              and not u.username and not u.password and not u.fragment
              and set(query) == {"v"} and len(query["v"]) == 1
              and len(query["v"][0]) == 11 and
              all(ch.isalnum() or ch in "_-" for ch in query["v"][0]))
    except (ValueError, TypeError):
        ok = False
    if not ok:
        raise ValueError("GARUDANETRA Media needs exact approved HTTPS YouTube watch URL")
    return value


def blocked_private_resource(url):
    """Disallow direct navigation to local networks; don't block Google media hosts."""
    try:
        u = urlsplit(str(url or ""))
        host = (u.hostname or "").lower().rstrip(".")
        if u.scheme in ("blob", "data", "chrome-extension"):
            # Locally installed, previously reviewed extension resources.
            # External HTTP and private-network destinations still fail closed.
            return False
        if u.scheme != "https" or not host or u.username or u.password:
            return True
        if host in ("localhost", "localhost.localdomain") or host.endswith(".localhost"):
            return True
        if host.endswith((".local", ".internal", ".lan")):
            return True
        try:
            return not ipaddress.ip_address(host.strip("[]")).is_global
        except ValueError:
            return False
    except ValueError:
        return True


class MediaContinuity:
    """Conservative per-session state; no fabricated video progress."""

    def __init__(self, *, empty_tolerance=2):
        if empty_tolerance < 1:
            raise ValueError("empty tolerance must be positive")
        self.empty_tolerance = empty_tolerance
        self.last_ready = None
        self.empty_samples = 0
        self.last_event = None
        self.last_content_seconds = 0.0
        self.transitions = []

    def observe(self, sample, *, wall_seconds=None):
        if not isinstance(sample, dict) or not sample:
            return "snapshot_unavailable"
        if sample.get("ad_showing") is True:
            self.empty_samples = 0
            return "advertisement"
        try:
            sec = float(sample.get("seconds", 0) or 0)
        except (TypeError, ValueError):
            sec = 0.0
        ready = sample.get("video_ready_state")
        network = sample.get("video_network_state")
        if sample.get("video_error_code"):
            return "media_error"
        if sample.get("ended") is True:
            return "ended"
        if (ready is not None and ready >= 2 and
                network in (1, 2) and sec >= 0):
            self.empty_samples = 0
            if self.last_ready is not None and (
                    sample.get("media_element_generation") !=
                    self.last_ready.get("media_element_generation")):
                self.last_event = self._event("video_element_replaced", sample, wall_seconds)
                return "video_element_replaced"
            if sec > self.last_content_seconds:
                self.last_content_seconds = sec
            self.last_ready = dict(sample)
            return "playing_or_buffered"
        if self.last_ready is not None and (ready == 0 and network == 0
                and sec <= 0.1):
            self.empty_samples += 1
            if self.empty_samples >= self.empty_tolerance:
                self.last_event = self._event("media_unloaded_after_playback", sample,
                                               wall_seconds)
                return "media_unloaded_after_playback"
        else:
            self.empty_samples = 0
        return "waiting_for_media"

    def _event(self, kind, sample, wall_seconds):
        event = {
            "reason": kind,
            "wall_seconds": round(float(wall_seconds), 2)
                if wall_seconds is not None else None,
            "last_source_seconds": round(float(self.last_content_seconds), 2),
            "ready_state_before": self.last_ready.get("video_ready_state")
                if self.last_ready else None,
            "network_state_before": self.last_ready.get("video_network_state")
                if self.last_ready else None,
            "ready_state_after": sample.get("video_ready_state"),
            "network_state_after": sample.get("video_network_state"),
            "video_element_replaced": (
                self.last_ready.get("media_element_generation") !=
                sample.get("media_element_generation")
                if self.last_ready and
                self.last_ready.get("media_element_generation") is not None and
                sample.get("media_element_generation") is not None else None),
            "ad_showing": False,
            "provider_cause_unverified": True,
        }
        self.transitions.append(event)
        self.transitions = self.transitions[-20:]
        return event


class GarudanetraMediaSession:
    """Canonical single Playwright context in an existing, isolated job workspace."""

    def __init__(self, workspace, approved_url, *, channel=None, headless=False,
                 browser_args=()):
        self.workspace = Path(workspace).expanduser().resolve()
        self.source_url = approved_youtube_watch(approved_url)
        if channel not in (None, "chrome", "msedge", "chromium"):
            raise ValueError("Invalid local Playwright browser channel")
        self.channel = channel
        self.headless = bool(headless)
        self.browser_args = list(browser_args)
        self.context = None
        self.page = None
        self.main_frame_navigations = 0
        self.unexpected_navigation = False
        self.failed_media_requests = []
        self.media_http_errors = []

    async def route(self, route):
        # The media lane needs Google video/manifest assets that the website
        # lane intentionally blocks. Only direct local/private destinations
        # are disallowed, not ordinary HTTPS media streams.
        if blocked_private_resource(route.request.url):
            await route.abort()
        else:
            await route.continue_()

    def _frame_navigated(self, frame):
        if self.page is None or frame != self.page.main_frame:
            return
        self.main_frame_navigations += 1
        try:
            u = urlsplit(frame.url)
            expected = parse_qs(urlsplit(self.source_url).query).get("v")
            actual = parse_qs(u.query).get("v")
            self.unexpected_navigation |= not (
                u.scheme == "https" and
                u.hostname in ("youtube.com", "www.youtube.com", "m.youtube.com")
                and u.path == "/watch" and actual == expected)
        except ValueError:
            self.unexpected_navigation = True

    def _request_failed(self, request):
        # Never store signed streaming URLs, cookies, headers or query tokens.
        try:
            kind = request.resource_type
            if kind not in ("media","fetch","xhr","manifest"):
                return
            self.failed_media_requests.append({
                "host": (urlsplit(request.url).hostname or "")[:100],
                "resource_type":kind,
                "failure":str(request.failure or "")[:140],
            })
            self.failed_media_requests = self.failed_media_requests[-20:]
        except (ValueError,AttributeError):
            pass

    def _response(self, response):
        try:
            status = int(response.status)
            kind = response.request.resource_type
            if status < 400 or kind not in ("media","fetch","xhr","manifest"):
                return
            self.media_http_errors.append({
                "host": (urlsplit(response.url).hostname or "")[:100],
                "status":status,"resource_type":kind,
            })
            self.media_http_errors = self.media_http_errors[-20:]
        except (TypeError,ValueError,AttributeError):
            pass

    def launch(self, playwright):
        if self.context:
            raise RuntimeError("GARUDANETRA Media context already launched")
        profile = self.workspace / "browser-profile"
        profile.mkdir(parents=True, exist_ok=True)
        args = ["--autoplay-policy=no-user-gesture-required"] + self.browser_args
        self.context = playwright.chromium.launch_persistent_context(
            str(profile), headless=self.headless,
            **({"channel": self.channel} if self.channel else {}),
            args=args, viewport={"width":1280, "height":800})
        try:
            self.context.route("**/*", self.route_sync)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self.page.on("framenavigated", self._frame_navigated)
            self.page.on("requestfailed", self._request_failed)
            self.page.on("response", self._response)
            self.page.goto(self.source_url, wait_until="domcontentloaded", timeout=90000)
            if self.unexpected_navigation:
                raise RuntimeError("GARUDANETRA Media navigated away from approved video")
            return self.context, self.page
        except Exception:
            self.close()
            raise

    def route_sync(self, route):
        if blocked_private_resource(route.request.url):
            route.abort()
        else:
            route.continue_()

    def close(self):
        context = self.context
        self.context = None
        self.page = None
        if context:
            context.close()

    def diagnostics(self):
        return {
            "engine": "garudanetra-media-lite-playwright",
            "browser_channel": self.channel or "bundled_chromium_default",
            "main_frame_navigations": self.main_frame_navigations,
            "unexpected_navigation": self.unexpected_navigation,
            "failed_media_requests":list(self.failed_media_requests[-20:]),
            "media_http_errors":list(self.media_http_errors[-20:]),
            "logged_in_verified": False,
            "profile_isolated": True,
            "source_learning_verified": False,
        }
