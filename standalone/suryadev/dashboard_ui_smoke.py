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


async def browser_check(port):
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        try:
            page=await browser.new_page(viewport={"width":1366,"height":768})
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            await page.goto(f"http://127.0.0.1:{port}/",wait_until="domcontentloaded")
            await expect(page.locator("#netra-web-running")).to_have_text("2",timeout=12000)
            await expect(page.locator("#netra-video-running")).to_have_text("1",timeout=12000)
            web=await page.locator("#netra-web-tabs").inner_text()
            tabs=await page.locator(".netra-workspace-tab").count()
            cap=await page.locator("#netra-total-capacity").inner_text()
            assert web=="2", "Genuine Chromium tab count not rendered"
            assert tabs==3, f"Expected 3 source workspace cards, got {tabs}"
            assert "3 active / 4 allowed" in cap, f"capacity display wrong: {cap}"
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


async def browser_offline_check(port):
    """An offline worker must not be mislabelled as a failing laptop."""
    from playwright.async_api import async_playwright, expect
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(f"http://127.0.0.1:{port}/",wait_until="domcontentloaded")
            await expect(page.locator("#netra-capacity-heading")).to_have_text(
                "Learning worker offline — dashboard is running", timeout=12000)
            label = await page.locator("#netra-total-capacity").inner_text()
            reason = await page.locator("#netra-capacity-reason").inner_text()
            assert "worker offline" in label, label
            assert "learning-plan.json file is missing" in reason, reason
            assert "RAM" in reason and "CPU" in reason, reason
            assert await page.locator(".netra-workspace-tab").count()==0
            assert not errors, "Browser JS errors: " + str(errors)
            return {"status":"PASS", "worker_state":"offline",
                    "capacity_label":label, "plan_missing_reported":True,
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
            result=asyncio.run(browser_check(port))
            print("GARUDANETRA_DASHBOARD_UI_REPORT="+json.dumps(result),flush=True)
            with lib.db:
                lib.db.execute("UPDATE jobs SET status='queued' WHERE status='running'")
            worker_note(root,"stopped",10,"UI test transitions worker to offline")
            offline=asyncio.run(browser_offline_check(port))
            print("GARUDANETRA_OFFLINE_UI_REPORT="+json.dumps(offline),flush=True)
        finally:
            lib.db.close()


if __name__=="__main__":
    main()
