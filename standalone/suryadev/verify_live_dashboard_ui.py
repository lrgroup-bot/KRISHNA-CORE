"""Read-only live SURYADEV sidebar and tactile-UI acceptance check.

Uses a fresh, headless Playwright Chromium page to visit only the existing
loopback SURYADEV dashboard. Never clicks worker, cleanup, storage migration,
server save, approved-media preview or source-approval actions. No data writes.
The currently managed SURYADEV worker can remain running.
"""
from __future__ import annotations

import argparse
import json
from urllib.parse import urlsplit
from urllib.request import urlopen


# All destinations are in the same app, not ten OS windows or workers.
ROUTES = (
    ("overview", "overview", "link"),
    ("garudanetra", "garudanetra", "link"),
    ("ai-learner", "ai-learner", "link"),
    ("assignments", "assignments", "link"),
    ("video-review", "video-review", "link"),
    ("sources", "sources", "link"),
    ("books-evidence", "books-evidence", "link"),
    ("date-center", "date-center", "link"),
    ("server-settings", "server-settings-dialog", "open-server-settings"),
    ("storage-settings", "storage-settings-dialog", "open-storage-settings"),
)


def _read_control(base):
    with urlopen(base + "/api/learning/control", timeout=8) as response:
        data = json.load(response)
    if not isinstance(data, dict) or "managed_running" not in data:
        raise RuntimeError("The loopback URL does not expose SURYADEV worker controls")
    return data


def verify(base="http://127.0.0.1:8872"):
    """Verify rendered pages and UX while leaving worker/data unchanged."""
    from playwright.sync_api import sync_playwright
    parsed = urlsplit(base)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or (
            parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise ValueError("Audit is restricted to local http://127.0.0.1:PORT")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid local dashboard port") from exc
    if port is None or not 1024 <= port <= 65535:
        raise ValueError("Specify an explicit local dashboard port")
    base = "http://127.0.0.1:" + str(port)
    before = _read_control(base)
    pages = []
    errors = []
    popup_count = [0]
    nonlocal_requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.on("popup", lambda popup: popup_count.__setitem__(0,popup_count[0]+1))

            def restrict_request(route):
                destination = urlsplit(route.request.url)
                if destination.scheme == "http" and destination.hostname == "127.0.0.1" and (
                        destination.port == port):
                    route.continue_()
                else:
                    nonlocal_requests.append(destination.hostname or destination.scheme)
                    route.abort()
            page.route("**/*", restrict_request)
            page.goto(base + "/advanced#overview", wait_until="domcontentloaded",
                      timeout=20000)
            page.locator('.suryadev-page[data-page="overview"]:not([hidden])').wait_for(
                state="visible", timeout=12000)
            for destination, panel_id, kind in ROUTES:
                if kind == "link":
                    page.locator('.navigation a[href="#' + destination + '"]').click()
                    selected = page.locator('.navigation a[href="#' + destination + '"]')
                else:
                    page.locator("#" + kind).click()
                    selected = page.locator("#" + kind)
                page.locator('.suryadev-page[data-page="' + destination + '"]:not([hidden])').wait_for(
                    state="visible", timeout=12000)
                selected.wait_for(state="visible")
                page.locator("#" + panel_id).wait_for(state="visible", timeout=12000)
                measured = page.evaluate("""() => {
                    const visible=[...document.querySelectorAll('.suryadev-page')]
                       .filter(n=>!n.hidden);
                    const current=visible[0];
                    const banner=current?.querySelector('.dashboard-page-banner');
                    const button=[...current.querySelectorAll('button')]
                       .find(n=>!n.disabled&&getComputedStyle(n).display!=='none');
                    return {
                        count:visible.length,
                        page:current?.dataset.page||null,
                        title:banner?.querySelector('h1')?.textContent?.trim()||'',
                        bannerVisible:!!banner&&getComputedStyle(banner).display!=='none',
                        buttonHas3DDepth:button?getComputedStyle(button).boxShadow!=='none':null,
                        iframeCount:document.querySelectorAll('#ai-learner-player iframe').length
                    };
                }""")
                if measured["count"] != 1 or measured["page"] != destination:
                    raise AssertionError("More than one page, or wrong page visible: "
                                         + repr(measured))
                if not measured["bannerVisible"] or not measured["title"]:
                    raise AssertionError("Missing visible page header: " + destination)
                if measured["buttonHas3DDepth"] is False:
                    raise AssertionError("Tactile button styling missing: " + destination)
                if measured["iframeCount"]:
                    raise AssertionError("Unexpected playback iframe during navigation")
                if selected.get_attribute("aria-current") != "page":
                    raise AssertionError("Active navigation indicator missing: " + destination)
                pages.append({"route": destination, "title": measured["title"],
                              "panel_visible": True,
                              "tactile_button_checked": measured["buttonHas3DDepth"]})
            page.go_back(wait_until="domcontentloaded")
            page.locator(".suryadev-page:not([hidden])").wait_for(state="visible")
            if page.locator(".suryadev-page:not([hidden])").count() != 1:
                raise AssertionError("Browser Back did not restore one visible page")
            if errors or popup_count[0] or nonlocal_requests:
                raise AssertionError("Browser errors/popups/external requests: " + repr({
                    "errors": errors, "popups": popup_count[0],
                    "external_requests": nonlocal_requests}))
        finally:
            browser.close()
    after = _read_control(base)
    # This diagnostic never sends a POST, so it cannot start a second worker.
    # A managed worker may independently progress/stop between measurements.
    return {
        "schema": "suryadev.live-page-acceptance.v1",
        "status": "PASS",
        "base": base,
        "pages_passed": len(pages),
        "pages": pages,
        "javascript_errors": errors,
        "popups": popup_count[0],
        "external_requests": nonlocal_requests,
        "worker_before": {
            "managed_running": bool(before.get("managed_running")),
            "external_worker_active": bool(before.get("external_worker_active"))},
        "worker_after": {
            "managed_running": bool(after.get("managed_running")),
            "external_worker_active": bool(after.get("external_worker_active"))},
        "source_write_requests": 0,
        "full_video_comprehension_verified": False,
        "brahmagyan_rishi_exam_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only live ten-dashboard Playwright check")
    parser.add_argument("--base", default="http://127.0.0.1:8872")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify(args.base), indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, AssertionError, ImportError) as exc:
        print("SURYADEV LIVE UI CHECK FAILED: " + type(exc).__name__ + ": " + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
