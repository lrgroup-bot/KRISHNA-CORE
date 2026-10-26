/* SURYADEV independent dashboard pages.
 * One local server and DOM: route existing panels, never copy evidence, spawn
 * processes, or request a new source. This file runs deferred before DOM ready.
 */
"use strict";
(() => {
  const main=document.querySelector(".app-shell > main");
  const nav=document.querySelector(".sidebar .navigation");
  if(!main||!nav)return;
  const pages=[
    {key:"overview", icon:"⌂", title:"Mission Overview",
     eyebrow:"SURYADEV · COMMAND CENTRE",
     description:"Live mission totals, node health and capacity from the existing learning ledger.",
     items:["#overview",".overview","#hardware"]},
    {key:"garudanetra",icon:"◉",title:"Live Learning",
     eyebrow:"GARUDANETRA · OPERATIONS",
     description:"Monitor the one learning worker, measured admission, research lanes and live assignments.",
     items:["#garudanetra"]},
    {key:"ai-learner",icon:"✦",title:"AI Learner",
     eyebrow:"FOUR LEARNING LANES",
     description:"One approved learning engine: YouTube, PDF, Websites and Books, with evidence kept separate from comprehension.",
     items:["#ai-learner"]},
    {key:"assignments",icon:"▣",title:"Assignments",
     eyebrow:"TASK INSPECTION",
     description:"Search assignments and inspect saved source hashes, extraction coverage and actual outcomes.",
     items:["#assignments"]},
    {key:"video-review",icon:"▶",title:"Video Review",
     eyebrow:"MEDIA OBSERVATION",
     description:"Review actual playback and caption records. Browser progress never becomes automatic comprehension.",
     items:["#video-review"]},
    {key:"sources",icon:"◈",title:"Evidence",
     eyebrow:"SOURCE PROVENANCE",
     description:"Verify records by source type. Completed jobs are evidence, not certified mastery.",
     items:["#sources"]},
    {key:"books-evidence",icon:"▧",title:"Books",
     eyebrow:"READING CHECKPOINTS",
     description:"Read original indexed lines, inspect progress and preserve every model-reading checkpoint.",
     items:["#books-evidence"]},
    {key:"date-center",icon:"◷",title:"History",
     eyebrow:"LEARNING HISTORY",
     description:"Explore original daily activity, source findings and recorded assignments.",
     items:["#date-center","#diary"]},
    {key:"server-settings",icon:"◉",title:"KRISHNA Server",
     eyebrow:"SECURE CONNECTION",
     description:"Review a local server candidate and diagnostics; connectivity is not authenticated pairing.",
     items:["#server-settings-dialog"]},
    {key:"storage-settings",icon:"▤",title:"Storage & Cleanup",
     eyebrow:"LOCAL DATA SAFETY",
     description:"Inspect disk status and existing evidence-safe storage and cleanup controls.",
     items:["#storage-settings-dialog"]}
  ];
  const alias={
    "live-learning":"garudanetra",
    "hardware":"overview",
    "diary":"date-center",
    "server-settings-dialog":"server-settings",
    "storage-settings-dialog":"storage-settings"
  };
  // Keep references before moving a parent (Books belongs to Garudanetra).
  // This avoids transient detached-node lookups during the one-time reflow.
  const original=new Map();
  for(const spec of pages)for(const selector of spec.items){
    if(!original.has(selector))original.set(selector,
      main.querySelector(selector)||document.querySelector(selector));
  }
  const panels=new Map();
  const content=document.createDocumentFragment();
  for(const spec of pages){
    const page=document.createElement("div");
    page.className="suryadev-page";
    page.dataset.page=spec.key;
    page.setAttribute("role","region");
    page.setAttribute("aria-label",spec.title+" dashboard");
    page.hidden=true;
    const banner=document.createElement("header");
    banner.className="dashboard-page-banner";
    banner.tabIndex=-1;
    const copy=document.createElement("div");
    copy.className="dashboard-page-copy";
    const eyebrow=document.createElement("span");
    eyebrow.className="dashboard-page-eyebrow";
    eyebrow.textContent=spec.eyebrow;
    const title=document.createElement("h1");
    title.className="dashboard-page-title";
    const symbol=document.createElement("span");
    symbol.className="dashboard-page-icon";
    symbol.setAttribute("aria-hidden","true");
    symbol.textContent=spec.icon;
    title.append(symbol,document.createTextNode(spec.title));
    const description=document.createElement("p");
    description.className="dashboard-page-description";
    description.textContent=spec.description;
    copy.append(eyebrow,title,description);
    const signal=document.createElement("div");
    signal.className="dashboard-page-signal";
    signal.textContent="ONE WORKER · LOCAL FIRST";
    banner.append(copy,signal);
    page.append(banner);
    for(const selector of spec.items){
      const element=original.get(selector);
      if(!element)throw Error("Missing existing SURYADEV page: "+selector);
      page.append(element);
    }
    panels.set(spec.key,page);
    content.append(page);
  }
  // AI Learner is the only operational workspace. Move the canonical
  // controls and real queue DOM nodes, never clone them or create a worker.
  // Existing dashboard-learning.js and activity handlers retain the same IDs,
  // CSRF protection and API paths because their original elements are moved.
  function into(targetId,selectors) {
    const host=document.getElementById(targetId);
    if(!host)throw Error("Missing AI Learner workspace mount: "+targetId);
    for(const selector of selectors){
      const node=document.querySelector(selector);
      if(!node)throw Error("Missing existing learning workspace: "+selector);
      host.append(node);
    }
  }
  into("ai-learner-control-mount",["#garudanetra .learning-controls"]);
  into("ai-learner-status-mount",[
    "#learning-action-status","#learning-workspace-state","#learning-core-status"
  ]);
  into("ai-learner-operations-mount",["#live-learning"]);
  const queue=document.getElementById("live-learning");
  if(queue)queue.open=true;
  // Original-book source-line search remains one live form and one listener.
  // Historical book progress may still be inspected in its read-only menu.
  into("ai-learner-book-tools",["#book-search-form","#book-search-results"]);
  const monitor=document.getElementById("garudanetra");
  const notice=document.createElement("p");
  notice.className="netra-disclaimer";
  notice.textContent="This page is read-only fleet telemetry. Start/stop, source lanes, " +
    "current queue and book line search operate in the AI Learner workspace.";
  monitor.append(notice);
  // Remove layout scaffolding left empty when Evidence/Health move to pages.
  const formerMiddle=main.querySelector(".middle-grid");
  if(formerMiddle && !formerMiddle.children.length)formerMiddle.remove();
  const footer=main.querySelector("footer");
  main.prepend(content);
  if(footer)main.append(footer);
  const routes=pages.map(x=>x.key);
  function route(){
    const requested=decodeURIComponent(location.hash.slice(1));
    const key=routes.includes(requested)?requested:(alias[requested]||"overview");
    for(const [name,panel] of panels)
      panel.hidden=name!==key;
    for(const element of nav.querySelectorAll(".nav-item")){
      const target=element.getAttribute("href")?.slice(1) ||
        (element.id==="open-server-settings"?"server-settings":
         element.id==="open-storage-settings"?"storage-settings":"");
      const active=target===key;
      element.classList.toggle("selected",active);
      if(active)element.setAttribute("aria-current","page");
      else element.removeAttribute("aria-current");
    }
    document.body.dataset.currentPage=key;
    document.dispatchEvent(new CustomEvent("suryadev-page-change",
      {detail:{page:key,requested}}));
    const anchor=requested!==key && alias[requested]
      ?document.getElementById(requested):null;
    // The destination is already visible. No external tab or page reload.
    if(anchor)anchor.scrollIntoView({block:"start"});
    else window.scrollTo({top:0,behavior:"instant"});
  }
  window.addEventListener("hashchange",route);
  route();
})();
