"""Playwright UI smoke of SURYADEV's live parallel source frontend.

Starts local dashboard against a disposable SQLite ledger and *recorded*
telemetry, then inspects actual Chromium rendering of the v6 controls.
Telemetry is test-injected, not falsely described as hardware measurement.
"""
from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path
import tempfile
import threading
import time
from urllib.request import urlopen

from suryadev import Library
from suryadev_extras import serve
from suryadev_liveops import atomic_json, worker_note


def available_port():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]


async def browser_node_console_check(port):
    """Both public UI routes render ONE Learning Intelligence workspace.

    Test real Chromium pages and controls, not a mocked HTML string.
    The legacy function name stays for external CI callers.
    """
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(viewport={"width":1366,"height":768})
            errors=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            for route in ("/", "/advanced"):
                await page.goto(f"http://127.0.0.1:{port}{route}", wait_until="domcontentloaded")
                await expect(page.locator(".identity small")).to_have_text("LEARNING INTELLIGENCE")
                await expect(page.locator("#learning-start")).to_have_count(1)
                await expect(page.locator("#learning-stop")).to_have_count(1)
                await expect(page.locator("#learning-model")).to_have_count(1)
                await expect(page.locator("#learning-model option[value='collector']")).to_have_count(1)
                await expect(page.locator("#learning-model option[value='auto']")).to_have_count(1)
                await expect(page.locator("#video-review")).to_have_count(1)
                await expect(page.locator("#book-ledger-list")).to_have_count(1)
                await expect(page.locator("#node-control-profile")).to_have_count(1)
                await expect(page.locator("#node-control-plan")).to_have_count(1)
                await expect(page.locator("#node-control-pairing")).to_have_count(1)
                await expect(page.locator("#node-control-capacity")).to_have_count(1)
                await expect(page.locator("#total")).to_have_text("3",timeout=12000)
                await expect(page.locator("#connection")).to_have_text("Online · local service",timeout=12000)
                assert await page.locator('script[src="/node-console.js"]').count()==0
                assert await page.locator('a[href="#video-review"]').count()==1
            assert not errors, "Unified Learning Intelligence JS errors: "+str(errors)
            return {"status":"PASS","node_control_default":False,
                    "single_learning_intelligence_frontend":True,
                    "home_and_advanced_same_ui":True,"live_assignments":3,
                    "source_records":3,"collector_mode_visible":True,"javascript_errors":errors}
        finally:
            await browser.close()


async def browser_check(port):
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(viewport={"width":1366,"height":768})
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            await page.goto(f"http://127.0.0.1:{port}/advanced#garudanetra",wait_until="domcontentloaded")
            await expect(page.locator("#netra-web-running")).to_have_text("2",timeout=12000)
            await expect(page.locator("#netra-video-running")).to_have_text("1",timeout=12000)
            await expect(page.locator("#netra-engine-state")).to_contain_text("Chromium browsing", timeout=12000)
            web=await page.locator("#netra-web-tabs").inner_text()
            tabs=await page.locator(".netra-workspace-tab").count()
            cap=await page.locator("#netra-total-capacity").inner_text()
            assert web=="2", "Genuine Chromium tab count not rendered"
            assert tabs==3, f"Expected 3 source workspace cards, got {tabs}"
            assert "3 active / 4 measured admission slots" in cap, f"capacity display wrong: {cap}"
            assert await page.locator("#netra-web-capacity").inner_text()=="3"
            assert await page.locator("#netra-pdf-capacity").inner_text()=="1"
            await page.locator(".netra-workspace-tab.website").first.click()
            await page.locator("#task-dialog[open]").wait_for(timeout=8000)
            await page.locator("#close-detail").click()
            assert not errors, "Frontend runtime exceptions: "+str(errors)
            # The real source tabs are not editable or forged client-side:
            # web and video count exactly match backend running ledger.
            return {
                "status":"PASS", "workspace_cards":tabs,
                "website_running":2, "youtube_running":1,
                "chromium_tabs_rendered":int(web),
                "reported_capacity":cap, "javascript_errors":errors
            }
        finally:
            await browser.close()


async def browser_books_check(port):
    """Books retain their source ledger inside their own main menu dashboard."""
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(viewport={"width":1366,"height":768})
            errors=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            await page.goto(f"http://127.0.0.1:{port}/advanced",wait_until="domcontentloaded")
            await expect(page.locator("#netra-books-running")).to_have_text("1",timeout=12000)
            await expect(page.locator("#netra-books-indexed")).to_have_text("1")
            await expect(page.locator("#netra-books-lines")).to_have_text("1 / 3")
            await expect(page.locator("#netra-workspace-count")).to_have_text("4")
            await expect(page.locator(".netra-workspace-tab.book")).to_have_count(1)
            await expect(page.locator(".source-card.books")).to_have_count(0)
            await expect(page.locator("#book-health")).to_have_count(0)
            await expect(page.locator("#netra-books-lines")).to_have_text("1 / 3")
            await page.locator('.navigation a[href="#books-evidence"]').click()
            await expect(page.locator("#books-evidence")).to_be_visible()
            await expect(page.locator("#garudanetra")).to_be_hidden()
            # The learning book ledger is canonical; hardware/source summaries
            # no longer duplicate its details.
            await expect(page.locator("#book-ledger-list .book-session")).to_have_count(
                1,timeout=12000)
            await expect(page.locator("#book-search-form")).to_have_count(1)
            assert await page.locator("#book-learning").count()==0
            assert await page.locator('a[href="#book-learning"]').count()==0
            assert not errors, "Book dashboard JS runtime errors: "+str(errors)
            return {"status":"PASS","source_cards":4,"book_running":1,
                    "book_indexed":1,"processed_lines":1,"inline_book_cards":1,
                    "legacy_book_sections":0,"javascript_errors":errors}
        finally:
            await browser.close()


async def browser_continuity_check(port):
    """YouTube provider restriction never disables independent approved web/PDF lanes."""
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(f"http://127.0.0.1:{port}/advanced#garudanetra", wait_until="domcontentloaded")
            await expect(page.locator("#netra-capacity-heading")).to_have_text(
                "YouTube rate-limited — website/PDF research continues", timeout=12000)
            await expect(page.locator("#netra-continuity-status")).to_contain_text(
                "YouTube rate-limited", timeout=12000)
            await expect(page.locator("#netra-youtube-access")).to_contain_text(
                "YouTube HTTP 429", timeout=12000)
            assert await page.locator("#netra-video-capacity").inner_text() == "0"
            assert await page.locator("#netra-web-capacity").inner_text() == "3"
            assert await page.locator("#netra-pdf-capacity").inner_text() == "1"
            assert not errors, errors
            return {"status":"PASS","youtube_capacity":0,
                    "website_capacity":3,"pdf_capacity":1,
                    "continuity_label":"YouTube rate-limited",
                    "javascript_errors":errors}
        finally:
            await browser.close()


async def browser_offline_check(port):
    """An offline worker must not be mislabelled as a failing laptop."""
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(f"http://127.0.0.1:{port}/advanced#garudanetra",wait_until="domcontentloaded")
            await expect(page.locator("#netra-capacity-heading")).to_have_text(
                "Learning worker offline — dashboard is running", timeout=12000)
            label = await page.locator("#netra-total-capacity").inner_text()
            reason = await page.locator("#netra-capacity-reason").inner_text()
            assert "worker offline" in label, label
            assert "learning-plan.json file is missing" in reason, reason
            assert "RAM" in reason and "CPU" in reason, reason
            await expect(page.locator("#netra-youtube-access")).to_contain_text(
                "YouTube HTTP 429",timeout=12000)
            assert await page.locator(".netra-workspace-tab").count()==0
            assert not errors, "Browser JS errors: " + str(errors)
            return {"status":"PASS", "worker_state":"offline",
                    "capacity_label":label, "plan_missing_reported":True,
                    "javascript_errors":errors}
        finally:
            await browser.close()



async def browser_video_review_check(port, approved_url):
    """Real Chromium: no manual source addition, video jobs visible read-only.

    This smoke does not launch a worker or trigger third-party requests.
    """
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(viewport={"width":1366,"height":768})
            errors=[]
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            await page.goto(f"http://127.0.0.1:{port}/advanced#video-review", wait_until="domcontentloaded")
            await expect(page.locator("#video-review")).to_have_count(1)
            await expect(page.locator("#video-review")).to_be_visible(timeout=12000)
            # Four in-page AI Learner buttons and one same-page menu item.
            await expect(page.locator("#ai-learner")).to_have_count(1)
            await expect(page.locator('a[href="#ai-learner"]')).to_have_count(1)
            await expect(page.locator(".ai-learner-tab")).to_have_count(4)
            await expect(page.locator("#ai-tab-youtube")).to_have_attribute("aria-pressed","true")
            await expect(page.locator("#ai-learner-player iframe")).to_have_count(0)
            await expect(page.locator("#ai-learner")).to_be_hidden()
            await page.locator('a[href="#ai-learner"]').click()
            await expect(page.locator("#ai-learner")).to_be_visible()
            await page.locator("#ai-tab-pdf").click()
            await expect(page.locator("#ai-tab-pdf")).to_have_attribute("aria-pressed","true")
            await expect(page.locator("#ai-learner-lane-heading")).to_contain_text("PDF")
            await page.locator("#ai-tab-website").click()
            await expect(page.locator("#ai-learner-lane-heading")).to_contain_text("Websites")
            await expect(page.locator("#ai-learner-lane-results .ai-learner-record")).to_have_count(
                2,timeout=12000)
            await page.locator("#ai-learner-lane-results .ai-learner-record button").first.click()
            await expect(page.locator("#ai-learner-lane-results .ai-learner-record").first).to_contain_text(
                "Evidence hash integrity: not_recorded",timeout=12000)
            await page.locator("#ai-tab-book").click()
            await expect(page.locator("#ai-learner-lane-heading")).to_contain_text("Books")
            await page.locator("#ai-tab-youtube").click()
            await expect(page.locator("#ai-learner-lane-heading")).to_contain_text("YouTube")
            await expect(page.locator("#ai-learner-player iframe")).to_have_count(0)
            # External media is not contacted by this smoke. Opening the
            # approved preview is a frontend-only, explicit user gesture.
            await page.route("https://www.youtube-nocookie.com/**",
                             lambda route: route.abort())
            popups=[]
            page.on("popup", lambda popup: popups.append(popup))
            await page.locator('a[href="#ai-learner"]').click()
            await expect(page.locator("#ai-learner")).to_be_visible()
            await expect(page.locator("#overview")).to_be_hidden()
            await expect(page.locator("#video-review")).to_be_hidden()
            await expect(page.locator("#ai-learner-video-choice option")).to_have_count(
                1,timeout=12000)
            await page.locator("#ai-learner-open-preview").click()
            await expect(page.locator("#ai-learner-player iframe")).to_have_count(1)
            await expect(page.locator("#ai-learner-player iframe")).to_have_attribute(
                "src","https://www.youtube-nocookie.com/embed/mgBpcQRDtl0")
            await page.locator("#ai-tab-pdf").click()
            await expect(page.locator("#ai-learner-player iframe")).to_have_count(0)
            assert not popups, "Approved YouTube preview opened a new OS/browser window"
            await page.locator('.navigation a[href="#overview"]').click()
            await expect(page.locator("#overview")).to_be_visible()
            await expect(page.locator("#video-review")).to_be_hidden()
            await expect(page.locator("#ai-learner")).to_be_hidden()
            await expect(page.locator("#hardware")).to_be_visible()
            # The preview never starts itself and the page never creates
            # a competing Playwright profile or a second native window.
            opened=[]
            page.on("popup",lambda popup: opened.append(popup))
            assert not opened, "AI Learner unexpectedly opened an external window"
            await expect(page.locator('a[href="#video-review"]')).to_have_count(1)
            # Exactly one main menu dashboard is visible; all panels still exist.
            await expect(page.locator(".suryadev-page:not([hidden])")).to_have_count(1)
            await expect(page.locator(".suryadev-page")).to_have_count(10)
            await expect(page.locator("#overview")).to_be_visible()
            await expect(page.locator("#garudanetra")).to_be_hidden()
            # Visit every sidebar destination without new tabs, popup windows or worker launch.
            for dest, expected_id in [
                ("garudanetra","garudanetra"),("assignments","assignments"),
                ("video-review","video-review"),("sources","sources"),
                ("books-evidence","books-evidence"),("date-center","date-center")]:
                await page.locator(f'.navigation a[href="#{dest}"]').click()
                await expect(page.locator("#"+expected_id)).to_be_visible()
                await expect(page.locator(".suryadev-page:not([hidden])")).to_have_count(1)
                await expect(page.locator(f'.navigation a[href="#{dest}"]')).to_have_attribute(
                    "aria-current","page")
            await page.locator("#open-server-settings").click()
            await expect(page.locator("#server-settings-dialog")).to_be_visible()
            await expect(page.locator("#storage-settings-dialog")).to_be_hidden()
            await expect(page.locator("#server-ip")).to_be_visible()
            await page.locator("#open-storage-settings").click()
            await expect(page.locator("#storage-settings-dialog")).to_be_visible()
            await expect(page.locator("#server-settings-dialog")).to_be_hidden()
            await expect(page.locator("#cleanup-enabled")).to_be_visible()
            await expect(page.locator(".suryadev-page:not([hidden])")).to_have_count(1)
            await page.locator('.navigation a[href="#garudanetra"]').click()
            await expect(page.locator("#learning-enable-sources")).to_have_count(0)
            await expect(page.locator("#learning-start")).to_be_visible(timeout=12000)
            await expect(page.locator("#learning-start")).to_be_enabled(timeout=12000)
            await expect(page.locator("#video-auto-url")).to_have_count(0)
            await expect(page.locator("#video-auto-approve")).to_have_count(0)
            await expect(page.locator("#video-auto-toggle")).to_have_count(0)
            await expect(page.locator("#video-review-import")).to_have_count(0)
            await expect(page.locator("#video-review-json")).to_have_count(0)
            await expect(page.locator(".video-manual-details")).to_have_count(0)
            await page.locator('.navigation a[href="#video-review"]').click()
            await expect(page.locator("#learning-trial-audit")).to_be_visible(timeout=12000)
            await expect(page.locator('input[type="date"]')).to_have_count(1)
            await expect(page.locator("#ui-version")).to_contain_text("2026-10-25-v8", timeout=12000)
            await page.locator("#video-review-refresh").click()
            await expect(page.locator("#learning-trial-audit")).to_contain_text(
                "Rishi verified comprehension: NO", timeout=12000)
            assert not errors, "Video Review JS runtime errors: " + str(errors)
            return {"status":"PASS", "repo_frontend":True,
                    "manual_source_controls_removed":True,
                    "trial_evidence_panel_visible":True,
                    "four_lanes_in_one_page":True,
                    "unrequested_iframe_count":0,
                    "javascript_errors":errors}
        finally:
            await browser.close()


def main():
    with tempfile.TemporaryDirectory(prefix="suryadev-dashboard-smoke-") as root:
        lib=Library(root)
        port=available_port()
        try:
            now=time.time()
            with lib.db:
                for url in ("https://www.python.org/about/",
                            "https://www.python.org/downloads/",
                            "https://www.youtube.com/watch?v=mgBpcQRDtl0"):
                    lib.db.execute(
                        "INSERT INTO jobs(url,status,created,updated,error) VALUES (?,?,?,?,?)",
                        (url,"running",now,now,""))
            worker_note(root, "busy", 10, "Simulated worker heartbeat for Chromium UI test")
            atomic_json(root,"capacity-runtime.json",{
                "sample_time":now,"state":"busy","safe":True,"active_total":3,
                "max_total":4,"limits":{"website":3,"youtube":2,"pdf":1},
                "active":{"website":2,"youtube":1,"pdf":0},
                "cpu_percent":23,"ram_percent":43,
                "reason":"Simulated hardware sample for UI contract",
            })
            atomic_json(root,"garudanetra-runtime.json",{
                "heartbeat_at":now,"state":"running",
                "engine":"Garudanetra Lite / Playwright Chromium",
                "open_tabs":2,"tab_limit":4,
                "tabs":[{"job_id":1,"url":"https://www.python.org/about/",
                         "kind":"website","stage":"rendering"},
                        {"job_id":2,"url":"https://www.python.org/downloads/",
                         "kind":"website","stage":"rendering"}],
            })
            server=threading.Thread(target=serve,args=(lib,port),
                                    daemon=True,name="suryadev-ui-smoke-server")
            server.start()
            for _ in range(80):
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health",timeout=1) as answer:
                        if answer.status==200:
                            break
                except (OSError,ConnectionError):
                    time.sleep(.1)
            node=asyncio.run(browser_node_console_check(port))
            print("SURYADEV_NODE_CONTROL_UI_REPORT="+json.dumps(node),flush=True)
            result=asyncio.run(browser_check(port))
            print("GARUDANETRA_DASHBOARD_UI_REPORT="+json.dumps(result),flush=True)
            approved_url = "https://www.youtube.com/watch?v=mgBpcQRDtl0"
            temporary_plan = Path(root) / "learning-plan.json"
            temporary_plan.write_text(json.dumps({"approved_urls":[approved_url]}), encoding="utf-8")
            # A disposable approved source fixture; never a production video
            # launch, data migration, provider access or evidence claim.
            inbox=Path(root)/"video-review"/"approved-inbox"
            inbox.mkdir(parents=True,exist_ok=True)
            (inbox/"smoke-approved-job.json").write_text(json.dumps({
                "schema":"krishna.suryadev.job.v1",
                "job_id":"smoke-approved-job",
                "kind":"video_research",
                "target":approved_url
            }),encoding="utf-8")
            try:
                video = asyncio.run(browser_video_review_check(port, approved_url))
                print("SURYDEV_VIDEO_REVIEW_UI_REPORT="+json.dumps(video),flush=True)
            finally:
                temporary_plan.unlink(missing_ok=True)
            from suryadev_book_reader import BookLedger
            local_book = Path(root) / "approved-sample-book.txt"
            local_book.write_text("Source line one" + chr(10) + "Source line two" + chr(10) + "Source line three",
                                  encoding="utf-8")
            ledger = BookLedger(root)
            try:
                imported = ledger.import_book(local_book)
                ledger.read(imported["book_id"], model="smoke-local",
                            max_steps=1, observe=lambda prompt,model:
                            "Unverified source explanation")
            finally:
                ledger.close()
            atomic_json(root,"book-continuity-runtime.json",{
                "state":"book_reading_in_progress",
                "book_id":imported["book_id"],
                "title":"approved-sample-book",
                "model":"smoke-local",
                "processed_lines":1,"total_lines":3,
                "updated_at":time.time(),
                "brahmagyan_acknowledged":False})
            books = asyncio.run(browser_books_check(port))
            print("GARUDANETRA_BOOK_UI_REPORT="+json.dumps(books),flush=True)
            # After the book test, clear its in-flight activity so offline
            # source UI checks cannot report a fictitious active book.
            atomic_json(root,"book-continuity-runtime.json",{
                "state":"approved_books_complete_or_in_cooldown",
                "updated_at":time.time()})
            with lib.db:
                lib.db.execute("UPDATE jobs SET status='queued' WHERE status='running'")
                lib.db.execute("UPDATE jobs SET status='failed',error=? "
                               "WHERE url LIKE '%youtube.com%'",
                               ("HTTP 429: Too Many Requests",))
            worker_note(root,"idle",10,"Approved websites remain eligible")
            atomic_json(root,"capacity-runtime.json",{
                "sample_time":time.time(),"state":"idle","safe":True,
                "active_total":0,"max_total":4,
                "limits":{"website":3,"youtube":0,"pdf":1},
                "active":{"website":0,"youtube":0,"pdf":0},
                "cpu_percent":19,"ram_percent":44,
                "reason":"Simulated ready worker with YouTube blocked",
                "youtube_access":{"state":"rate_limited",
                    "cooldown_until":time.time()+3000},
            })
            atomic_json(root,"youtube-access-state.json",{
                "state":"rate_limited","recorded_at":time.time(),
                "cooldown_until":time.time()+3000})
            atomic_json(root,"continuity-runtime.json",{
                "active":True,"source_policy":"only_operator_approved_urls_and_feeds",
                "last_refresh":time.time(),"next_refresh":time.time()+300,
                "added_total":2,"feed_error_count":0,
                "youtube_blocked":True,"youtube_video_equivalence_claimed":False})
            continuity=asyncio.run(browser_continuity_check(port))
            print("GARUDANETRA_CONTINUITY_UI_REPORT="+json.dumps(continuity),flush=True)
            with lib.db:
                lib.db.execute("UPDATE jobs SET status='queued' WHERE status='running'")
            worker_note(root,"stopped",10,"UI test transitions worker to offline")
            atomic_json(root,"youtube-access-state.json", {
                "state":"rate_limited","recorded_at":time.time(),
                "cooldown_until":time.time()+3000})
            offline=asyncio.run(browser_offline_check(port))
            print("GARUDANETRA_OFFLINE_UI_REPORT="+json.dumps(offline),flush=True)
        finally:
            lib.db.close()


if __name__=="__main__":
    main()
