from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import time


@dataclass
class BrowserFinding:
    kind: str
    detail: str
    severity: str = "error"


@dataclass
class BrowserReport:
    url: str
    final_url: str
    title: str
    findings: list[dict] = field(default_factory=list)
    network: list[dict] = field(default_factory=list)
    visible_text: str = ""
    screenshot: str | None = None
    elapsed_ms: int = 0
    layout: dict = field(default_factory=dict)
    ok: bool = False


class BrowserOperator:
    """Chromium inspector used by KRISHNA to observe real frontend behavior."""

    def __init__(self, headless: bool = True, timeout_ms: int = 15000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    @staticmethod
    def summarize_findings(console_errors=None, page_errors=None,
                           failed_requests=None, bad_responses=None) -> list[dict]:
        findings: list[dict] = []
        for item in console_errors or []:
            findings.append(asdict(BrowserFinding("console_error", str(item))))
        for item in page_errors or []:
            findings.append(asdict(BrowserFinding("page_error", str(item), "critical")))
        for item in failed_requests or []:
            findings.append(asdict(BrowserFinding("request_failed", str(item))))
        for item in bad_responses or []:
            findings.append(asdict(BrowserFinding("http_error", str(item))))
        return findings

    def exhaustive_clickthrough(self, url: str, screenshot_dir: str | None = None, max_controls: int = 100) -> dict:
        """Testing-Lead live traversal of visible interactive controls with evidence."""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Chromium operator unavailable") from exc
        evidence=[]; findings=[]; started=time.perf_counter()
        with sync_playwright() as p:
            try: browser=p.chromium.launch(channel="chrome",headless=self.headless)
            except Exception: browser=p.chromium.launch(headless=self.headless)
            page=browser.new_page(); page.set_default_timeout(self.timeout_ms)
            page_errors=[]; page.on("pageerror",lambda e:page_errors.append(str(e)))
            page.goto(url,wait_until="networkidle")
            controls=page.locator("button, a[href], input[type=button], input[type=submit], [role=button]")
            count=min(controls.count(),max(1,int(max_controls)))
            for i in range(count):
                try:
                    control=controls.nth(i); label=(control.inner_text() or control.get_attribute("aria-label") or control.get_attribute("value") or "")[:160]
                    href=control.get_attribute("href"); before=page.url
                    if href and (href.startswith("http") and not href.startswith(url.split("/",3)[0]+"//"+url.split("/",3)[2])):
                        evidence.append({"index":i,"label":label,"skipped":"external_navigation"}); continue
                    control.click(timeout=min(self.timeout_ms,5000)); page.wait_for_timeout(150)
                    evidence.append({"index":i,"label":label,"before":before,"after":page.url,"ok":True})
                    if page.url!=before: page.go_back(wait_until="domcontentloaded")
                except Exception as exc:
                    evidence.append({"index":i,"ok":False,"error":str(exc)[:500]})
            findings.extend(self.summarize_findings(page_errors=page_errors))
            shot=None
            if screenshot_dir:
                target=Path(screenshot_dir).resolve();target.mkdir(parents=True,exist_ok=True);shot=target/"testing-lead-final.png";page.screenshot(path=str(shot),full_page=True)
            browser.close()
        failed=[x for x in evidence if not x.get("ok") and not x.get("skipped")]
        return {"url":url,"controls_checked":len(evidence),"evidence":evidence,"findings":findings,"screenshot":str(shot) if shot else None,"ok":not failed and not findings,"elapsed_ms":int((time.perf_counter()-started)*1000)}

    def perfection_scan(self, url: str, viewports: list[int] | None = None, screenshot_dir: str | None = None) -> dict:
        """Measure the rendered application across a responsive viewport matrix."""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Chromium operator unavailable") from exc
        widths = viewports or [375, 390, 430, 768, 1024, 1366, 1440, 1920, 2560]
        widths = sorted({max(320, min(int(x), 3840)) for x in widths})
        out=[]; started=time.perf_counter()
        with sync_playwright() as p:
            try: browser=p.chromium.launch(channel="chrome",headless=self.headless)
            except Exception: browser=p.chromium.launch(headless=self.headless)
            for width in widths:
                height=844 if width < 768 else 900
                page=browser.new_page(viewport={"width":width,"height":height})
                page.set_default_timeout(self.timeout_ms)
                console=[]; errors=[]; failed=[]; bad=[]
                page.on("console",lambda msg, bag=console: bag.append(msg.text) if msg.type=="error" else None)
                page.on("pageerror",lambda exc, bag=errors: bag.append(str(exc)))
                page.on("requestfailed",lambda req, bag=failed: bag.append(f"{req.method} {req.url} :: {req.failure}"))
                page.on("response",lambda resp, bag=bad: bag.append(f"{resp.status} {resp.url}") if resp.status>=400 else None)
                page.goto(url,wait_until="domcontentloaded"); page.wait_for_timeout(350)
                geometry=page.evaluate("""() => Array.from(document.querySelectorAll('body *')).filter(el => {
                  const s=getComputedStyle(el),r=el.getBoundingClientRect();
                  return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && r.height>0;
                }).slice(0,5000).map((el,i) => {
                  const r=el.getBoundingClientRect(),s=getComputedStyle(el);
                  let selector=el.id ? '#'+el.id : el.tagName.toLowerCase();
                  if(!el.id && el.classList.length) selector+='.'+Array.from(el.classList).slice(0,2).join('.');
                  return {selector:selector+'@'+i,x:r.x,y:r.y,width:r.width,height:r.height,visible:true,
                          text:(el.innerText||'').trim().slice(0,120),z_index:parseInt(s.zIndex)||0};
                })""")
                layout=page.evaluate("""() => ({viewport_width:innerWidth,viewport_height:innerHeight,
                    scroll_width:document.documentElement.scrollWidth,scroll_height:document.documentElement.scrollHeight,
                    horizontal_overflow:document.documentElement.scrollWidth>innerWidth+2})""")
                shot=None
                if screenshot_dir:
                    target=Path(screenshot_dir).resolve();target.mkdir(parents=True,exist_ok=True)
                    shot=target/f"viewport-{width}.png";page.screenshot(path=str(shot),full_page=True)
                findings=self.summarize_findings(console,errors,failed,bad)
                out.append({"width":width,"height":height,"url":page.url,"title":page.title(),
                            "layout":layout,"geometry":geometry,"findings":findings,
                            "screenshot":str(shot) if shot else None,"ok":not findings and not layout["horizontal_overflow"]})
                page.close()
            browser.close()
        return {"url":url,"viewports":out,"ok":all(x["ok"] for x in out),
                "elapsed_ms":int((time.perf_counter()-started)*1000)}

    def privacy_probe(self, url: str="about:blank", profile: str="BASELINE") -> dict:
        """Run a local, ephemeral browser privacy probe without activating sensors.

        The browser context is always temporary; no persistent profile is used by
        this method. Raw WebRTC candidate strings and cookie values are not retained.
        """
        from .privacy_guardian.browser import BROWSER_EXPOSURE_JS, WEBRTC_JS, summarize_browser_observation
        target=str(url or "about:blank").strip() or "about:blank"
        if target!="about:blank" and not target.startswith(("http://","https://")):
            raise ValueError("privacy probe URL must be about:blank, http:// or https://")
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Chromium operator unavailable for privacy probe") from exc

        started=time.perf_counter(); request_urls=[]
        with sync_playwright() as p:
            try: browser=p.chromium.launch(channel="chrome",headless=self.headless)
            except Exception: browser=p.chromium.launch(headless=self.headless)
            context=browser.new_context()
            page=context.new_page();page.set_default_timeout(self.timeout_ms)
            page.on("request",lambda req: request_urls.append(req.url) if len(request_urls)<500 else None)
            if target!="about:blank":
                page.goto(target,wait_until="domcontentloaded")
                page.wait_for_timeout(250)
            observation=page.evaluate(BROWSER_EXPOSURE_JS)
            webrtc=page.evaluate(WEBRTC_JS)
            result=summarize_browser_observation(
                observation,profile=str(profile or "BASELINE"),url=target,
                webrtc=webrtc,request_urls=request_urls,
            )
            result["elapsed_ms"]=int((time.perf_counter()-started)*1000)
            result["temporary_profile"]=True
            result["request_count"]=len(request_urls)
            result["context_cookie_count"]=len(context.cookies())
            context.close();browser.close()
            return result

    def inspect(self, url: str, actions: list[dict] | None = None,
                screenshot_path: str | None = None, viewport: dict | None = None) -> dict:
        if not url.startswith(("http://", "https://")):
            raise ValueError("browser inspection requires http:// or https:// URL")
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError(
                "Chromium operator unavailable. Install with: "
                "python -m pip install playwright && python -m playwright install chromium"
            ) from exc

        started = time.perf_counter()
        console_errors: list[str] = []
        page_errors: list[str] = []
        failed_requests: list[str] = []
        bad_responses: list[str] = []
        network: list[dict] = []
        actions = actions or []

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=self.headless)
            except Exception:
                browser = p.chromium.launch(headless=self.headless)
            viewport = viewport or {"width": 1440, "height": 900}
            width=max(320,min(int(viewport.get("width",1440)),3840))
            height=max(480,min(int(viewport.get("height",900)),2160))
            page = browser.new_page(viewport={"width":width,"height":height})
            page.set_default_timeout(self.timeout_ms)
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on("requestfailed", lambda req: failed_requests.append(
                f"{req.method} {req.url} :: {req.failure}"
            ))
            page.on("response", lambda resp: (
                network.append({"url": resp.url, "status": resp.status, "method": resp.request.method}),
                bad_responses.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None,
            ))
            # Live dashboards poll continuously, so Playwright's networkidle state can
            # legitimately never occur. DOM readiness plus a short bounded settle window
            # gives UI Guardian a deterministic inspection point without masking page errors.
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)

            for action in actions:
                kind = str(action.get("type", "")).lower()
                selector = str(action.get("selector", ""))
                if kind == "click":
                    page.locator(selector).click()
                elif kind == "fill":
                    page.locator(selector).fill(str(action.get("value", "")))
                elif kind == "press":
                    page.locator(selector).press(str(action.get("key", "Enter")))
                elif kind == "wait":
                    page.wait_for_timeout(int(action.get("ms", 500)))
                elif kind:
                    raise ValueError(f"unsupported browser action: {kind}")

            shot = None
            if screenshot_path:
                target = Path(screenshot_path).resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(target), full_page=True)
                shot = str(target)

            visible_text = page.locator("body").inner_text()[:12000]
            layout = page.evaluate("""() => {
              const de=document.documentElement, b=document.body;
              const vw=window.innerWidth, vh=window.innerHeight;
              const sw=Math.max(de?.scrollWidth||0,b?.scrollWidth||0);
              const sh=Math.max(de?.scrollHeight||0,b?.scrollHeight||0);
              return {
                viewport_width:vw, viewport_height:vh,
                scroll_width:sw, scroll_height:sh,
                document_width:Math.max(de?.clientWidth||0,b?.clientWidth||0),
                document_height:Math.max(de?.clientHeight||0,b?.clientHeight||0),
                horizontal_overflow:sw>vw+2
              };
            }""")
            report = BrowserReport(
                url=url,
                final_url=page.url,
                title=page.title(),
                findings=self.summarize_findings(
                    console_errors, page_errors, failed_requests, bad_responses
                ),
                network=network[-200:],
                visible_text=visible_text,
                screenshot=shot,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
                layout=layout,
            )
            report.ok = not report.findings and not layout.get("horizontal_overflow")
            out = asdict(report)
            out["layout"] = layout
            browser.close()
            return out
