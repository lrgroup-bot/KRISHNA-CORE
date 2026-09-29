"""Render the real desktop shell; assert controls are reachable, not just present."""
import json
import os
import unittest
from pathlib import Path


@unittest.skipUnless(os.getenv("KRISHNA_WINDOWS_UI_E2E") == "1", "desktop browser E2E disabled")
class WindowsUIBrowserTests(unittest.TestCase):
    def test_desktop_layout_and_observed_load(self):
        from playwright.sync_api import sync_playwright
        html = (Path(__file__).resolve().parents[1] / "web_validation.html").read_text(encoding="utf-8")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page()
                sample = {"cpu_percent": 14.5, "memory_percent": 75, "checked_at": 9999999999, "pressure": {"memory": True}}
                systems = [{"id": key, "name": name, "logo": "◈", "state": "handling" if key == "brahma" else "idle", "color": "yellow" if key == "brahma" else "red", "detail": "Checking a failed step" if key == "brahma" else "Idle", "updated_at": 9999999999} for key, name in [
                    ("krishna", "KRISHNA"), ("brahma", "BRAHMA"), ("sudarshan", "Sudarshan"), ("hawkeye", "Hawkeye"), ("kabach", "KABACH"), ("garuda", "Garuda"),
                    ("garudanetra", "Garudanetra"), ("narad", "NARAD"), ("brahmagyan", "BRAHMAGYAN"), ("gyan", "Gyan-Bhandar"), ("rishi", "Rishi Council"), ("amcc", "aMCC")]]
                def respond(route):
                    path = route.request.url.split("desktop.test", 1)[-1]
                    if path == "/":
                        return route.fulfill(content_type="text/html", body=html)
                    data = {}
                    if path == "/api/dashboard":
                        data = {"pc_observer": sample, "resources": {"max_concurrent_jobs": 2}}
                    elif path == "/api/working-gods":
                        data = {"gods": systems, "latest_color": "yellow"}
                    elif path == "/api/runtime/integrity":
                        data = {"status": "SYNCED"}
                    if path.startswith("/api/"):
                        return route.fulfill(content_type="application/json", body=json.dumps(data))
                    route.fulfill(status=404, body="")
                page.route("**/*", respond)
                page.goto("http://desktop.test/")
                for width, height in [(1280,720), (1366,768), (1440,900), (1920,1080)]:
                    page.set_viewport_size({"width": width, "height": height})
                    page.get_by_role("button", name="☸Sudarshan", exact=True).click()
                    for selector in ["#input", 'button[aria-label="Send message"]']:
                        box = page.locator(selector).bounding_box()
                        self.assertIsNotNone(box)
                        self.assertGreaterEqual(box["x"], 0)
                        self.assertLessEqual(box["x"] + box["width"], width)
                        self.assertLessEqual(box["y"] + box["height"], height)
                        self.assertTrue(page.locator(selector).evaluate("(el)=>{const b=el.getBoundingClientRect();return el.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2))}"), selector+" is covered")
                    page.get_by_role("button", name="ॐKRISHNA", exact=True).click()
                    self.assertTrue(page.get_by_role("button",name="Open KRISHNA AI assistant").is_visible())
                    self.assertEqual(page.locator("#krishnaAvatar").count(),0)
                    box = page.get_by_role("button",name="Open KRISHNA AI assistant").bounding_box()
                    self.assertGreaterEqual(box["y"], 0)
                    self.assertLessEqual(box["y"] + box["height"], height)
                    page.get_by_role("button",name="Open KRISHNA AI assistant").click()
                    self.assertTrue(page.locator("#krishnaPopup").is_visible())
                    page.get_by_role("button",name="Close",exact=True).click()
                    self.assertTrue(page.locator("#opsInformer").is_visible())
                    self.assertEqual(page.locator("#workingGodsMini .miniGodRow").count(),12)
                    self.assertTrue(page.locator(".sideFoot .opsVitals").is_visible())
                page.evaluate("refreshCommandCenter()")
                self.assertEqual(page.locator("#opsLoadText").inner_text(), "CPU 15% · RAM 75%")
                self.assertIn("warn", page.locator("#opsLoadDot").get_attribute("class"))
                sample.clear()
                page.evaluate("refreshCommandCenter()")
                self.assertEqual(page.locator("#opsLoadText").inner_text(), "CPU —% · RAM —% · stale")
                self.assertIn("idle", page.locator("#opsLoadDot").get_attribute("class"))
                page.get_by_role("button",name="Show BRAHMA details").click()
                self.assertTrue(page.get_by_role("dialog",name="BRAHMA").is_visible())
                self.assertIn("Checks work",page.locator("#godDetailRole").inner_text())
                self.assertEqual(page.locator("#godDetailActivity").inner_text(),"Checking a failed step")
            finally:
                browser.close()
