"""Lightweight standalone Garudanetra observer for SURYADEV.

Uses KRISHNA's canonical Playwright/Chromium engine and isolated incognito
context; not a competing browser or an authenticated KRISHNA Core session.
Only the exact owner-approved HTTPS site may load. Deep mode is explicitly
opt-in and permits SAME-HOST styles/images for vision; cross-host requests,
YouTube media and unapproved linked-page navigation remain blocked.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import Future
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from suryadev_liveops import atomic_json
from suryadev_browser_engine import browser_channel, browser_identity
from suryadev_deep_web import deep_web_settings, inspect_page

MAX_VISIBLE_CHARS = 220_000
MAX_BROWSER_TABS = 10
BROWSER_STATUS_FILE = "garudanetra-runtime.json"
_ENGINE = "Garudanetra Lite / canonical Playwright Chromium"


class GarudanetraLite:
    def __init__(self, root, *, max_tabs=1):
        if type(max_tabs) is not int or not (1 <= max_tabs <= MAX_BROWSER_TABS):
            raise ValueError("Garudanetra tabs must be between 1 and 10")
        self.root = Path(root).expanduser().resolve()
        self.max_tabs = max_tabs
        self.deep_mode, self.vision_model = deep_web_settings()
        self._lock = threading.RLock()
        self._tabs = {}
        self._allowed_hosts = set()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._loop = None
        self._thread = None
        self._error = None
        self._context = None
        self._semaphore = None
        self._started = None

    def _status(self, state="running"):
        with self._lock:
            atomic_json(self.root, BROWSER_STATUS_FILE, {
                "engine": _ENGINE, "canonical_core_engine": "playwright",
                "browser_identity":browser_identity(),
                "standalone_adapter": True, "state": state,
                "headless": True, "private_context": True,
                "process_owns_browser": state == "running",
                "heartbeat_at": time.time(), "started_at": self._started,
                "tab_limit": self.max_tabs, "open_tabs": len(self._tabs),
                "tabs": list(self._tabs.values())[:MAX_BROWSER_TABS],
                "network_policy": ("approved HTTPS SAME HOST, deep images/styles; no media/fonts"
                                   if self.deep_mode else "approved-https-same-host, no media/image/font/css"),
                "full_video_visuals_verified": False,
            })

    def start(self):
        if self._thread is not None:
            return self
        self.root.mkdir(parents=True, exist_ok=True)
        self._started = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="garudanetra-playwright-runtime")
        self._thread.start()
        if not self._ready.wait(timeout=25):
            raise RuntimeError("Garudanetra Lite Chromium did not start within 25 seconds")
        if self._error:
            raise RuntimeError("Garudanetra Lite unavailable: " + str(self._error))
        return self

    def _run(self):
        try:
            asyncio.run(self._serve())
        except Exception as exc:
            self._error = type(exc).__name__ + ": " + str(exc)[:300]
            self._status("unavailable")
        finally:
            self._ready.set()

    async def _serve(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Install Garudanetra engine: python -m pip install playwright "
                               "and python -m playwright install chromium") from exc
        self._loop = asyncio.get_running_loop()
        self._semaphore = asyncio.Semaphore(self.max_tabs)
        async with async_playwright() as p:
            # Use Playwright-managed Chromium only; never fallback to the user's
            # Chrome/Edge profile or attach to their personal browser.
            browser = await p.chromium.launch(headless=True, channel=browser_channel())
            try:
                self._context = await browser.new_context(
                    viewport={"width":1024,"height":768}, locale="en-US",
                    accept_downloads=False, service_workers="block",
                    permissions=[], java_script_enabled=True)
                try:
                    await self._context.route("**/*", self._route)
                    self._status()
                    self._ready.set()
                    while not self._stop.is_set():
                        self._status()
                        await asyncio.sleep(2)
                    # Close all pending pages, even after a job failure.
                finally:
                    await self._context.close()
            finally:
                await browser.close()
        self._status("stopped")

    async def _route(self, route):
        address = route.request.url
        parsed = urlsplit(address)
        with self._lock:
            approved = parsed.hostname in self._allowed_hosts
        blocked_types = {"media", "font", "websocket", "manifest"}
        if not self.deep_mode:
            blocked_types |= {"image", "stylesheet"}
        if (parsed.scheme != "https" or not approved or parsed.username or
                parsed.password or parsed.port not in (None,443) or
                route.request.resource_type in blocked_types):
            await route.abort()
        else:
            await route.continue_()

    async def _render(self, url, job_id):
        from suryadev import validate_url
        validate_url(url)
        parsed = urlsplit(url)
        async with self._semaphore:
            with self._lock:
                self._allowed_hosts.add(parsed.hostname)
            page = None
            key = str(job_id or "preview-" + str(time.time_ns()))
            try:
                page = await self._context.new_page()
                with self._lock:
                    self._tabs[key] = {
                        "job_id": job_id, "url": url, "kind": "website",
                        "opened_at": time.time(), "stage": "rendering",
                    }
                self._status()
                response = await page.goto(url, wait_until="domcontentloaded",
                                           timeout=25000)
                if not response or response.status >= 400:
                    raise RuntimeError("Garudanetra site returned HTTP " +
                                       str(response.status if response else "no response"))
                # Same-host only, including redirects. Never follow a browser
                # navigation to a different host.
                final = urlsplit(page.url)
                if final.scheme != "https" or final.hostname != parsed.hostname:
                    raise ValueError("Garudanetra navigated outside the approved HTTPS host")
                # Deep research scans all bounded scroll positions and records
                # same-origin image/link metadata and actual local-vision attempts.
                deep_report = None
                if self.deep_mode:
                    deep_report = await inspect_page(page, model=self.vision_model)
                else:
                    await page.wait_for_timeout(450)
                try:
                    main = page.locator("main").first
                    selected = main if await main.count() else page.locator("body")
                    text = (await selected.inner_text(timeout=5000)).strip()
                except Exception:
                    text = (await page.locator("body").inner_text(timeout=5000)).strip()
                if not text:
                    raise ValueError("Garudanetra found no visible text on the page")
                if deep_report is not None:
                    from urllib.parse import urlsplit as split_link
                    fragments = ["[PAGE LINKS — discovered, not automatically followed]"]
                    for link in deep_report["links"]:
                        if split_link(link["href"]).hostname == parsed.hostname:
                            fragments.append(str(link["label"]) + ": " + str(link["href"]))
                    fragments.append("[PAGE IMAGE DESCRIPTIONS / ALT TEXT]")
                    fragments.extend(
                        str(x["alt"]) + " " + str(x["src"])
                        for x in deep_report["image_sources"] if x["alt"])
                    fragments.append("[LOCAL VISUAL OBSERVATIONS — UNVERIFIED]")
                    fragments.extend(
                        "Viewport {}: {}".format(x["viewport"], x["observation"])
                        for x in deep_report["vision_observations"])
                    text += "\n\n" + "\n".join(fragments)
                if len(text) > MAX_VISIBLE_CHARS:
                    raise ValueError("Rendered website exceeds supported extraction budget")
                # Capture bounded same-host reference links as citations, not
                # as silently authorized new crawling assignments.
                # Visible text and link labels may contain untrusted content.
                try:
                    raw_refs = await page.evaluate("""() => Array.from(
                        document.querySelectorAll('a[href]')).slice(0,100)
                        .map(a => ({href:a.href, label:(a.innerText||a.textContent||'').trim().slice(0,150)}))""")
                except Exception:
                    raw_refs = []
                source_links = []
                for item in (raw_refs if isinstance(raw_refs,list) else []):
                    if not isinstance(item,dict):
                        continue
                    href = str(item.get("href") or "")
                    link = urlsplit(href)
                    if link.scheme == "https" and link.hostname == parsed.hostname:
                        source_links.append({"href": href[:600],
                                             "label": str(item.get("label") or "")[:150]})
                    if len(source_links) >= 25:
                        break
                title = (await page.title()) or url
                with self._lock:
                    self._tabs[key]["stage"] = "text_extracted"
                    self._tabs[key]["title"] = title[:160]
                report = {
                    "kind": "website", "browser_engine": _ENGINE,
                    "browser_tab_opened": True,
                    "rendered_visible_characters": len(text),
                    "extracted_characters": len(text),
                    "browser_final_url": page.url,
                    "source_reference_url": page.url,
                    "extracted_text_lines": len(text.splitlines()),
                    "same_host_links_discovered_not_followed": source_links,
                    "linked_pages_followed": 0,
                    "reference_scope": "one approved page; linked pages require distinct approval",
                    "coverage_status": ("deep_web_dom_scroll_visuals_attempted_unverified"
                                        if deep_report else
                                        "garudanetra_rendered_text_unverified"),
                    "full_rendered_page_verified": False,
                    "embedded_video_audio_verified": False,
                    "note": ("Garudanetra deep inspected bounded full-scroll DOM and visual "
                             "viewports on the approved host; off-host media and arbitrary linked "
                             "pages remain excluded." if deep_report else
                             "Garudanetra rendered visible text only; scripts or external assets "
                             "blocked for privacy/lightness, and no video, image or linked page "
                             "was comprehensively learned."),
                    "deep_web": deep_report,
                }
                return title[:500], text, report
            finally:
                try:
                    if page:
                        await page.close()
                finally:
                    with self._lock:
                        self._tabs.pop(key, None)
                        # Other concurrent tabs may still need this same hostname.
                        active_hosts = {urlsplit(row["url"]).hostname for row in self._tabs.values()}
                        self._allowed_hosts = active_hosts
                    self._status()

    def render(self, url, *, job_id=None):
        from suryadev import validate_url
        validate_url(url)
        self.start()
        if self._stop.is_set():
            raise RuntimeError("Garudanetra Lite is already stopping")
        task = asyncio.run_coroutine_threadsafe(self._render(url, job_id), self._loop)
        try:
            return task.result(timeout=(3600 if self.deep_mode and self.vision_model
                                        else 90 if self.deep_mode else 45))
        except Exception:
            task.cancel()
            raise

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                self._status("stopping")
        else:
            self._status("stopped")

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.stop()


def render_website(url, *, root=None, job_id=None):
    """Single-task Garudanetra observer; parallel missions reuse one adapter."""
    from pathlib import Path
    with GarudanetraLite(root or Path.home() / "SURYADEV-DATA", max_tabs=1) as engine:
        return engine.render(url, job_id=job_id)
