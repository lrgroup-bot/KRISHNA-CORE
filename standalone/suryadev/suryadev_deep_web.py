"""Opt-in full-scroll browser text, media and local visual observation audit.

Works inside the existing Garudanetra canonical Playwright context; never
starts another browser, ignores no robots/access restrictions, and never
automatically follows discovered links. Cross-host assets remain blocked.
"""
from __future__ import annotations

import asyncio
from io import BytesIO
import os


def deep_web_settings(env=None):
    env = os.environ if env is None else env
    enabled = str(env.get("SURYADEV_DEEP_WEB", "")).strip().lower() in ("1","true","yes")
    model = str(env.get("SURYADEV_VISION_MODEL", "")).strip()
    return enabled, model


async def inspect_page(page, *, model="", max_viewports=24,
                       vision=None, pause_ms=100):
    """Scroll from top to bottom, collecting reachable images/links and OCR-like
    model observations on EACH visited viewport when model is specified.
    A 24-viewport bound prevents unbounded JavaScript or screenshot loops.
    """
    if not 1 <= max_viewports <= 64:
        raise ValueError("web viewport budget must be 1..64")
    if not 0 <= pause_ms <= 2000:
        raise ValueError("invalid scroll delay")
    if model and vision is None:
        from PIL import Image
        from suryadev_deep_pdf import ollama_vision
        def vision(raw):
            image = Image.open(BytesIO(raw)).convert("RGB")
            return ollama_vision(image, model)
    viewport = await page.evaluate("""() => ({
      height:window.innerHeight, documentHeight:Math.max(
       document.documentElement.scrollHeight,document.body.scrollHeight)
    })""")
    height = max(1, int(viewport["height"]))
    full = max(height, int(viewport["documentHeight"]))
    # Visit every viewport (not merely first-screen text); page may grow as
    # lazy content loads. Fail closed if it exceeds configured safe budget.
    images = []
    observations = []
    positions = list(range(0,full,height))
    if len(positions) > max_viewports:
        raise ValueError("webpage requires more than " + str(max_viewports) +
                         " viewports; review/split source without claiming completeness")
    for number, pos in enumerate(positions):
        await page.evaluate("(y) => window.scrollTo(0,y)", pos)
        await page.wait_for_timeout(pause_ms)
        if model:
            # Playwright returns a PNG screenshot of exactly this viewport.
            png = await page.screenshot(type="png", full_page=False,
                                        animations="disabled")
            observation = await asyncio.to_thread(vision, png)
            if not isinstance(observation, str) or not observation.strip():
                raise RuntimeError("Local vision model failed at page viewport " + str(number + 1))
            observations.append({"viewport":number+1,"scroll_y":pos,
                                 "observation":observation.strip()[:2200]})
    # Dynamic pages may append more sections after a viewport scroll.
    end_height = await page.evaluate("""() => Math.max(
      document.documentElement.scrollHeight,document.body.scrollHeight)""")
    if int(end_height) > full + height:
        raise ValueError("lazy webpage grew after scroll; cannot claim all sections inspected")
    await page.evaluate("(y) => window.scrollTo(0,y)", 0)
    meta = await page.evaluate("""() => ({
      images: Array.from(document.images).slice(0,2000).map(i => ({
        src:i.currentSrc||i.src||'', alt:i.alt||'', width:i.naturalWidth||0,
        height:i.naturalHeight||0, complete:!!i.complete
      })),
      links: Array.from(document.querySelectorAll('a[href]')).slice(0,2000)
        .map(a=>({href:a.href, label:(a.innerText||a.title||'').slice(0,180)})),
      embeds: Array.from(document.querySelectorAll('video,audio,iframe'))
        .slice(0,300).map(e=>({tag:e.tagName,src:e.currentSrc||e.src||''})),
      tables:document.querySelectorAll('table').length,
      canvas:document.querySelectorAll('canvas').length,
      svg:document.querySelectorAll('svg').length
    })""")
    image_rows = meta["images"]
    return {
        "viewports_visited":len(positions), "total_height_px":full,
        "every_bounded_viewport_visited":True,
        "viewports_interpreted_by_local_vision":len(observations),
        "visual_model_coverage":"every_viewport_model_attempted_unverified" if model else "no_visual_model",
        "images_in_DOM":len(image_rows),
        "images_with_alternative_text":sum(1 for i in image_rows if i["alt"]),
        "images_loaded":sum(1 for i in image_rows if i["complete"] and i["width"]),
        "image_sources":[{"src":i["src"][:500],"alt":i["alt"][:500],
                          "loaded":bool(i["complete"] and i["width"])}
                         for i in image_rows[:200]],
        "links_discovered":len(meta["links"]),
        "links":[{"href":i["href"][:600],"label":i["label"][:180]}
                 for i in meta["links"][:500]],
        "embedded_media":meta["embeds"][:80], "tables_count":meta["tables"],
        "canvas_count":meta["canvas"], "svg_count":meta["svg"],
        "vision_observations":observations,
        "linked_pages_followed":0, "external_media_understood":False,
        "semantic_comprehension_verified":False,
        "note":"DOM and viewport inspection is bounded. Discovered links are NOT crawled "
               "without owner approval, and blocked third-party assets are not interpreted.",
    }
