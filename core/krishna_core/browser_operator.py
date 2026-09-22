from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from hashlib import sha256
import os
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
                geometry=page.evaluate("""() => {
                  const els=Array.from(document.querySelectorAll('body *')).filter(el => {
                    const s=getComputedStyle(el),r=el.getBoundingClientRect();
                    return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && r.height>0;
                  }).slice(0,5000);
                  const indexes=new Map(els.map((el,i)=>[el,i]));
                  const selectorOf=(el,i)=>{
                    let selector=el.id ? '#'+el.id : el.tagName.toLowerCase();
                    if(!el.id && el.classList.length) selector+='.'+Array.from(el.classList).slice(0,2).join('.');
                    return selector+'@'+i;
                  };
                  return els.map((el,i) => {
                    const r=el.getBoundingClientRect(),s=getComputedStyle(el),ancestors=[];
                    let p=el.parentElement,hops=0;
                    while(p && hops<12){
                      const pi=indexes.get(p);
                      if(pi!==undefined) ancestors.push(selectorOf(p,pi));
                      p=p.parentElement;hops++;
                    }
                    const tag=el.tagName.toLowerCase(),role=(el.getAttribute('role')||'').toLowerCase();
                    const interactive=['button','a','input','select','textarea','summary'].includes(tag) ||
                      ['button','link','checkbox','radio','textbox','combobox','switch','menuitem','tab'].includes(role) ||
                      el.hasAttribute('tabindex');
                    return {selector:selectorOf(el,i),x:r.x,y:r.y,width:r.width,height:r.height,visible:true,
                            text:(el.innerText||el.value||'').trim().slice(0,120),z_index:parseInt(s.zIndex)||0,
                            ancestors,scroll_width:el.scrollWidth||0,scroll_height:el.scrollHeight||0,
                            client_width:el.clientWidth||0,client_height:el.clientHeight||0,
                            overflow_x:s.overflowX||'visible',overflow_y:s.overflowY||'visible',
                            interactive,pointer_events:s.pointerEvents||'auto',opacity:parseFloat(s.opacity||'1')};
                  });
                }""")
                layout=page.evaluate("""() => ({viewport_width:innerWidth,viewport_height:innerHeight,
                    scroll_width:document.documentElement.scrollWidth,scroll_height:document.documentElement.scrollHeight,
                    horizontal_overflow:document.documentElement.scrollWidth>innerWidth+2})""")
                perf=page.evaluate("""() => {
                  const nav=performance.getEntriesByType('navigation')[0]||{};
                  const paints=Object.fromEntries(performance.getEntriesByType('paint').map(x=>[x.name,x.startTime]));
                  const load=(nav.loadEventEnd||nav.duration||0)-(nav.startTime||0);
                  return {
                    ttfb_ms:Math.max(0,(nav.responseStart||0)-(nav.requestStart||nav.startTime||0)),
                    dom_content_loaded_ms:Math.max(0,(nav.domContentLoadedEventEnd||0)-(nav.startTime||0)),
                    load_ms:Math.max(0,load),
                    first_paint_ms:paints['first-paint']??null,
                    first_contentful_paint_ms:paints['first-contentful-paint']??null,
                    resource_count:performance.getEntriesByType('resource').length
                  };
                }""")
                shot=None
                if screenshot_dir:
                    target=Path(screenshot_dir).resolve();target.mkdir(parents=True,exist_ok=True)
                    shot=target/f"viewport-{width}.png";page.screenshot(path=str(shot),full_page=True)
                findings=self.summarize_findings(console,errors,failed,bad)
                if not geometry:
                    findings.append({"kind":"empty_render","severity":"error",
                                     "detail":"No visible rendered elements were detected in body"})
                out.append({"width":width,"height":height,"url":page.url,"title":page.title(),
                            "layout":layout,"geometry":geometry,"performance":perf,"findings":findings,
                            "screenshot":str(shot) if shot else None,"ok":not findings and not layout["horizontal_overflow"]})
                page.close()
            browser.close()
        return {"url":url,"viewports":out,"ok":all(x["ok"] for x in out),
                "elapsed_ms":int((time.perf_counter()-started)*1000)}

    @staticmethod
    def _same_origin(base: str, candidate: str) -> bool:
        try:
            a=urlparse(base); b=urlparse(candidate)
            return (a.scheme,a.hostname,a.port or (443 if a.scheme=="https" else 80)) == (b.scheme,b.hostname,b.port or (443 if b.scheme=="https" else 80))
        except Exception:
            return False

    def crawl_application(self, url: str, screenshot_dir: str | None = None,
                          max_pages: int = 40, max_depth: int = 4,
                          max_controls_per_page: int = 80,
                          allow_mutating: bool = False) -> dict:
        """Bounded same-origin route/state crawler with deterministic evidence.

        Destructive-looking controls are observed but not activated unless
        allow_mutating=True. This keeps discovery safe by default.
        """
        if not url.startswith(("http://","https://")):
            raise ValueError("crawl requires http:// or https:// URL")
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Chromium operator unavailable") from exc
        max_pages=max(1,min(int(max_pages),250)); max_depth=max(0,min(int(max_depth),8))
        max_controls_per_page=max(1,min(int(max_controls_per_page),300))
        mutating_labels=(
            "delete","remove","logout","sign out","purchase","pay","send","submit","save","create","add ",
            "update","confirm","approve","reject","publish","deploy","restart","stop ","start ","run ","execute",
            "upload","import","reset","clear all","terminate","destroy","drop","pair","connect","disconnect",
        )
        queue=[(url,0)]; visited=set(); nodes=[]; edges=[]; findings=[]; skipped=[]; started=time.perf_counter()
        shot_root=Path(screenshot_dir).resolve() if screenshot_dir else None
        if shot_root: shot_root.mkdir(parents=True,exist_ok=True)
        with sync_playwright() as p:
            try: browser=p.chromium.launch(channel="chrome",headless=self.headless)
            except Exception: browser=p.chromium.launch(headless=self.headless)
            context=browser.new_context()
            while queue and len(visited)<max_pages:
                target,depth=queue.pop(0)
                target=urldefrag(target)[0]
                if target in visited or depth>max_depth or not self._same_origin(url,target): continue
                visited.add(target)
                page=context.new_page();page.set_default_timeout(self.timeout_ms)
                console=[];errors=[];failed=[];bad=[]
                page.on("console",lambda msg,bag=console:bag.append(msg.text) if msg.type=="error" else None)
                page.on("pageerror",lambda exc,bag=errors:bag.append(str(exc)))
                page.on("requestfailed",lambda req,bag=failed:bag.append(f"{req.method} {req.url} :: {req.failure}"))
                page.on("response",lambda resp,bag=bad:bag.append(f"{resp.status} {resp.url}") if resp.status>=400 else None)
                try:
                    page.goto(target,wait_until="domcontentloaded");page.wait_for_timeout(250)
                    current=urldefrag(page.url)[0]
                    anchors=page.locator("a[href]")
                    for i in range(min(anchors.count(),500)):
                        href=anchors.nth(i).get_attribute("href")
                        if not href: continue
                        absolute=urldefrag(urljoin(current,href))[0]
                        if self._same_origin(url,absolute) and absolute not in visited and depth<max_depth:
                            queue.append((absolute,depth+1))
                            edges.append({"source":current,"target":absolute,"action":"navigate","label":(anchors.nth(i).inner_text() or "")[:120]})
                    fields=page.locator("input:not([type=hidden]):not([type=file]):not([type=button]):not([type=submit]):not([type=reset]), textarea, select")
                    field_rows=[]
                    for fi in range(min(fields.count(),max_controls_per_page)):
                        field=fields.nth(fi)
                        try:
                            tag=(field.evaluate("(el)=>el.tagName.toLowerCase()") or "").lower()
                            ftype=(field.get_attribute("type") or tag or "text").lower()
                            name=(field.get_attribute("name") or field.get_attribute("id") or field.get_attribute("aria-label") or f"{tag}-{fi}")[:160]
                            row={"index":fi,"name":name,"type":ftype,"visible":field.is_visible(),"disabled":field.is_disabled()}
                            if row["visible"] and not row["disabled"]:
                                before_valid=field.evaluate("(el)=>typeof el.checkValidity==='function'?el.checkValidity():true")
                                field.focus(timeout=min(self.timeout_ms,2000))
                                values={
                                    "email":"krishna.qa@example.invalid","url":"https://example.invalid/test",
                                    "number":"1","date":"2026-01-15","datetime-local":"2026-01-15T12:00",
                                    "time":"12:00","month":"2026-01","week":"2026-W03",
                                    "password":"Krishna-QA-123!","tel":"+910000000000",
                                }
                                if allow_mutating:
                                    if tag=="select":
                                        options=field.locator("option:not([disabled])")
                                        if options.count():
                                            value=options.first.get_attribute("value")
                                            if value is not None:field.select_option(value=value)
                                    elif ftype in {"checkbox","radio"}:
                                        field.check(timeout=min(self.timeout_ms,2000))
                                    elif ftype not in {"color","range","image"}:
                                        field.fill(values.get(ftype,"KRISHNA_QA_TEST"))
                                    after_valid=field.evaluate("(el)=>typeof el.checkValidity==='function'?el.checkValidity():true")
                                    row.update({"focus_tested":True,"input_tested":True,"interaction_mode":"events",
                                                "valid_before":bool(before_valid),"valid_after":bool(after_valid)})
                                else:
                                    probe=field.evaluate("""(el, args)=>{
                                      const old={value:el.value,checked:el.checked,selectedIndex:el.selectedIndex};
                                      try{
                                        if(el.tagName.toLowerCase()==='select'){
                                          if(el.options.length)el.selectedIndex=0;
                                        }else if(['checkbox','radio'].includes((el.type||'').toLowerCase())){
                                          el.checked=!el.checked;
                                        }else if(!['color','range','image'].includes((el.type||'').toLowerCase())){
                                          el.value=args.value;
                                        }
                                        return {valid:typeof el.checkValidity==='function'?el.checkValidity():true};
                                      } finally {
                                        try{el.value=old.value;}catch(e){}
                                        try{el.checked=old.checked;}catch(e){}
                                        try{if(old.selectedIndex!==undefined)el.selectedIndex=old.selectedIndex;}catch(e){}
                                      }
                                    }""",{"value":values.get(ftype,"KRISHNA_QA_TEST")})
                                    row.update({"focus_tested":True,"input_tested":True,"interaction_mode":"property_probe_no_events",
                                                "valid_before":bool(before_valid),"valid_after":bool(probe.get("valid",True))})
                            field_rows.append(row)
                        except Exception as exc:
                            field_rows.append({"index":fi,"ok":False,"error":str(exc)[:500]})
                            findings.append({"kind":"field_interaction_failure","severity":"error","url":current,
                                             "field_index":fi,"detail":str(exc)[:500]})
                    if field_rows:
                        page.goto(current,wait_until="domcontentloaded");page.wait_for_timeout(100)
                    controls=page.locator("button, [role=button], input[type=button], input[type=submit]")
                    control_count=min(controls.count(),max_controls_per_page)
                    state_rows=[]
                    for i in range(control_count):
                        control=controls.nth(i)
                        try:
                            label=(control.inner_text() or control.get_attribute("aria-label") or control.get_attribute("value") or "").strip()[:160]
                            row={"index":i,"label":label,"disabled":control.is_disabled(),"visible":control.is_visible()}
                            state_rows.append(row)
                            if not row["visible"] or row["disabled"]: continue
                            low=label.lower()
                            tag=(control.evaluate("(el)=>el.tagName.toLowerCase()") or "").lower()
                            ctype=(control.get_attribute("type") or "").lower()
                            in_form=bool(control.evaluate("(el)=>!!el.closest('form')"))
                            default_submit=(tag=="button" and in_form and ctype in {"","submit"}) or (tag=="input" and ctype=="submit")
                            risky_label=any(x in low for x in mutating_labels)
                            if not allow_mutating and (default_submit or risky_label):
                                skipped.append({
                                    "url":current,"label":label,
                                    "reason":"potentially_mutating_control",
                                    "type":ctype or ("submit-default" if default_submit else tag),
                                });continue
                            before=page.url
                            try:
                                control.click(timeout=min(self.timeout_ms,2500))
                                page.wait_for_timeout(120)
                                after=urldefrag(page.url)[0]
                                sig=page.evaluate("""() => {
                                  const t=(document.body?.innerText||'').slice(0,6000);
                                  const c=Array.from(document.querySelectorAll('button,a[href],input,[role=button]'))
                                    .slice(0,300).map(x=>[(x.innerText||x.getAttribute('aria-label')||x.getAttribute('value')||'').trim(),x.tagName]).flat().join('|');
                                  return t+'::'+c;
                                }""")
                                state_id=sha256((after+"|"+sig).encode()).hexdigest()[:20]
                                edges.append({"source":current,"target":after,"action":"click","label":label,"state_id":state_id})
                                if after!=current and self._same_origin(url,after) and after not in visited and depth<max_depth:
                                    queue.append((after,depth+1))
                                if page.url!=before:
                                    page.goto(current,wait_until="domcontentloaded")
                                else:
                                    page.reload(wait_until="domcontentloaded")
                            except Exception as exc:
                                findings.append({"kind":"control_failure","severity":"error","url":current,"label":label,"detail":str(exc)[:500]})
                        except Exception as exc:
                            findings.append({"kind":"control_inspection_failure","severity":"warning","url":current,"detail":str(exc)[:500]})
                    signature=page.evaluate("""() => (document.body?.innerText||'').slice(0,12000)""")
                    state_hash=sha256((current+"|"+signature).encode()).hexdigest()[:20]
                    shot=None
                    if shot_root:
                        shot=shot_root/f"{len(nodes)+1:03d}-{state_hash}.png";page.screenshot(path=str(shot),full_page=True)
                    local_findings=self.summarize_findings(console,errors,failed,bad)
                    findings.extend([{**x,"url":current} for x in local_findings])
                    nodes.append({"url":current,"title":page.title(),"depth":depth,"state_id":state_hash,
                                  "controls":state_rows,"control_count":len(state_rows),
                                  "fields":field_rows,"field_count":len(field_rows),
                                  "screenshot":str(shot) if shot else None})
                except Exception as exc:
                    findings.append({"kind":"page_crawl_failure","severity":"critical","url":target,"detail":str(exc)[:700]})
                finally:
                    page.close()
            context.close();browser.close()
        return {"url":url,"nodes":nodes,"edges":edges,"skipped":skipped,"findings":findings,
                "visited_pages":len(nodes),"edge_count":len(edges),
                "ok":not any(x.get("severity") in {"error","critical"} for x in findings),
                "elapsed_ms":int((time.perf_counter()-started)*1000)}

    def accessibility_scan(self, url: str, viewport: dict | None = None) -> dict:
        """Automated semantic/accessibility sanity checks without claiming full WCAG coverage."""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Chromium operator unavailable") from exc
        viewport=viewport or {"width":1440,"height":900}
        with sync_playwright() as p:
            try: browser=p.chromium.launch(channel="chrome",headless=self.headless)
            except Exception: browser=p.chromium.launch(headless=self.headless)
            page=browser.new_page(viewport={"width":int(viewport["width"]),"height":int(viewport["height"])})
            page.set_default_timeout(self.timeout_ms);page.goto(url,wait_until="domcontentloaded");page.wait_for_timeout(200)
            result=page.evaluate("""() => {
              const issues=[]; const rows=[];
              const nodes=Array.from(document.querySelectorAll('button,a[href],input,select,textarea,[role],img'));
              for (const [i,el] of nodes.entries()) {
                const tag=el.tagName.toLowerCase(), role=el.getAttribute('role')||'';
                const text=(el.innerText||el.value||'').trim().slice(0,160);
                const name=(el.getAttribute('aria-label')||el.getAttribute('alt')||text||'').trim();
                const disabled=!!el.disabled || el.getAttribute('aria-disabled')==='true';
                const r=el.getBoundingClientRect();
                rows.push({i,tag,role,name,disabled,x:r.x,y:r.y,width:r.width,height:r.height});
                if ((tag==='button'||tag==='a'||tag==='input'||role==='button') && !name && !disabled)
                  issues.push({kind:'missing_accessible_name',index:i,tag,role});
                if (tag==='img' && !el.hasAttribute('alt'))
                  issues.push({kind:'image_missing_alt',index:i});
                if ((tag==='button'||role==='button') && r.width>0 && r.height>0 && (r.width<24||r.height<24))
                  issues.push({kind:'small_interactive_target',index:i,width:r.width,height:r.height});
              }
              const html=document.documentElement;
              if (!html.getAttribute('lang')) issues.push({kind:'html_missing_lang'});
              return {elements:rows,issues};
            }""")
            axe={"available":False,"violations":[]}
            candidates=[
                os.getenv("KRISHNA_AXE_CORE_JS",""),
                str(Path.cwd()/"node_modules"/"axe-core"/"axe.min.js"),
                str(Path(__file__).resolve().parents[2]/"node_modules"/"axe-core"/"axe.min.js"),
            ]
            axe_path=next((Path(x).resolve() for x in candidates if x and Path(x).is_file()),None)
            if axe_path:
                try:
                    page.add_script_tag(path=str(axe_path))
                    raw=page.evaluate("""async () => {
                      const out=await axe.run(document,{resultTypes:['violations']});
                      return out.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,
                        help:v.help,helpUrl:v.helpUrl,nodes:v.nodes.slice(0,20).map(n=>({
                          target:n.target,failureSummary:n.failureSummary,html:(n.html||'').slice(0,500)
                        }))}));
                    }""")
                    axe={"available":True,"path":str(axe_path),"violations":raw}
                except Exception as exc:
                    axe={"available":False,"path":str(axe_path),"violations":[],
                         "error":f"{type(exc).__name__}: {exc}"}
            page.close();browser.close()
        passed=not result["issues"] and not axe.get("violations")
        return {"url":url,"issues":result["issues"],"elements":result["elements"],"axe":axe,
                "passed":passed,"scope":"automated_semantic_plus_axe" if axe.get("available") else "automated_semantic_sanity"}

    def chaos_scan(self, url: str) -> dict:
        """Execute safe browser-level failure injection in ephemeral contexts."""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Chromium operator unavailable") from exc
        scenarios=[]; started=time.perf_counter()
        with sync_playwright() as p:
            try: browser=p.chromium.launch(channel="chrome",headless=self.headless)
            except Exception: browser=p.chromium.launch(headless=self.headless)

            def run(name, setup=None, action=None):
                context=browser.new_context(permissions=[])
                page=context.new_page();page.set_default_timeout(min(self.timeout_ms,7000))
                errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
                try:
                    if setup: setup(context,page)
                    page.goto(url,wait_until="domcontentloaded")
                    page.wait_for_timeout(180)
                    if action: action(context,page)
                    body_ok=page.locator("body").count()>0
                    scenarios.append({"name":name,"executed":True,"survived":body_ok and not errors,"page_errors":errors[:20]})
                except Exception as exc:
                    scenarios.append({"name":name,"executed":True,"survived":False,"error":f"{type(exc).__name__}: {exc}","page_errors":errors[:20]})
                finally: context.close()

            run("baseline")
            run("permission_denied")
            run("api_500",lambda c,p:p.route("**/*",lambda route: route.fulfill(status=500,body="KRISHNA_CHAOS") if route.request.resource_type in {"xhr","fetch"} else route.continue_()))
            run("api_abort",lambda c,p:p.route("**/*",lambda route: route.abort() if route.request.resource_type in {"xhr","fetch"} else route.continue_()))
            def offline_action(context,page):
                context.set_offline(True)
                try: page.reload(wait_until="domcontentloaded",timeout=3500)
                except Exception: pass
                context.set_offline(False)
            run("offline_reload",action=offline_action)
            def double_action(context,page):
                controls=page.locator("button:not([disabled]), [role=button]")
                if controls.count(): controls.first.dblclick(timeout=2500)
            run("double_click",action=double_action)
            browser.close()
        return {"url":url,"scenarios":scenarios,
                "passed":all(x.get("survived") for x in scenarios if x["name"]=="baseline"),
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
