/* AI Learner: one existing SURYADEV worker, four read-only lanes.
 * No new browser window, executable, account, source approval or job replay.
 * Only explicit user interaction loads approved YouTube content into this page.
 */
"use strict";
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const el = id => document.getElementById(id);
    if (!el("ai-learner")) return;
    const lanes = ["youtube", "pdf", "website", "book"];
    const names = {youtube:"YouTube", pdf:"PDF documents",
                   website:"Websites", book:"Books"};
    let selected = "youtube", approved = [], refreshing = false, rerun = false;
    const results = el("ai-learner-lane-results");
    const summary = el("ai-learner-lane-summary");
    const preview = el("ai-learner-youtube-preview");
    const player = el("ai-learner-player");
    const choice = el("ai-learner-video-choice");
    const banner = el("ai-learner-worker");
    const start = el("ai-learner-start"), stop = el("ai-learner-stop");
    const line = (parent, value, tag="p") => {
      const node=document.createElement(tag);
      node.textContent=String(value);
      parent.append(node);
      return node;
    };
    const metric = (parent, name, counts) => {
      const card=document.createElement("article");
      card.className="ai-learner-metric";
      line(card, name, "strong");
      line(card, "Queued "+Number(counts?.queued||0)+" · Running "+
           Number(counts?.running||0)+" · Done "+Number(counts?.done||0)+
           " · Failed "+Number(counts?.failed||0));
      parent.append(card);
    };
    const localLink = (label, hash) => {
      const link=document.createElement("a");
      link.href=hash;link.textContent=label;
      link.className="ai-learner-evidence-link";
      results.append(link);
    };
    function stopPreview() {
      // Destroy the iframe, not merely hide it: no background video,
      // provider player, tracking request or media clock remains alive.
      player.replaceChildren();
    }
    function validVideoId(input) {
      try {
        const u=new URL(String(input));
        if (u.protocol!=="https:" ||
            !["www.youtube.com","youtube.com","m.youtube.com"].includes(u.hostname) ||
            u.pathname!=="/watch" || u.hash || u.username || u.password ||
            [...u.searchParams.keys()].some(k => k!=="v")) return null;
        const id=u.searchParams.getAll("v");
        return id.length===1 && /^[a-zA-Z0-9_-]{11}$/.test(id[0]) ? id[0] : null;
      } catch { return null; }
    }
    function drawVideos(jobs) {
      approved=jobs.filter(j => j && validVideoId(j.target) && typeof j.job_id==="string");
      const remembered=choice.value;
      choice.replaceChildren();
      for(const j of approved.slice(0,80)) {
        const o=document.createElement("option");
        o.value=j.job_id;
        o.textContent=j.job_id+" · "+(j.status||"not started");
        choice.append(o);
      }
      if(approved.some(j=>j.job_id===remembered))choice.value=remembered;
      el("ai-learner-open-preview").disabled=!approved.length;
      if(!approved.length)stopPreview();
    }
    function select(lane) {
      if (!lanes.includes(lane)) return;
      if (selected==="youtube" && lane!=="youtube")stopPreview();
      selected=lane;
      for(const name of lanes)
        el("ai-tab-"+name).setAttribute("aria-pressed", String(name===lane));
      el("ai-learner-lane-heading").textContent=names[lane]+" · recorded evidence";
      preview.hidden=lane!=="youtube";
      summary.textContent="Loading "+names[lane].toLowerCase()+" from the existing source ledger…";
      results.replaceChildren();
      refresh();
    }
    async function json(path) {
      const response=await window.suryadevRead(path,{cache:"no-store"});
      if(!response.ok)throw Error("HTTP "+response.status);
      return response.json();
    }
    async function refresh() {
      if(refreshing){rerun=true;return;}
      refreshing=true;
      try {
        const lane=selected;
        const [control,live]=await Promise.all([
          json("/api/learning/control"),json("/api/live")
        ]);
        start.disabled=!(control.can_start===true);
        stop.disabled=!(control.managed_running===true);
        banner.textContent=control.managed_running ? "One worker active · PID "+control.managed_pid :
          control.external_worker_active ? "External worker holds lock · do not duplicate" :
          "Learning paused · approved sources retained";
        const source=(live.sources||{})[lane]||{};
        results.replaceChildren();
        if(lane==="youtube") {
          const [review,audit]=await Promise.all([
            json("/api/video/review"),json("/api/youtube/audit")]);
          if(lane!==selected)return;
          metric(results,"YouTube jobs",source);
          drawVideos(Array.isArray(review.jobs)?review.jobs:[]);
          summary.textContent=(review.auto_enabled?"Approved-video observation enabled":"Video observation not enabled")+
            " · Active: "+(review.active_job||"none")+
            " · Browser evidence: "+(audit.browser_observations||[]).length+
            " · Rishi examination: not verified";
          for(const item of (audit.browser_observations||[]).slice(0,8)) {
            const wrap=document.createElement("article");
            wrap.className="ai-learner-record";
            line(wrap,(item.title||item.job_id||"Approved video")+" · "+(item.status||"unknown"),"strong");
            line(wrap,"Last player position: "+
              (item.last_playback_position_seconds??"not recorded")+
              "s · Caption lines: "+(item.captured_caption_lines??"unknown")+
              " · Reason: "+(item.stop_reason||"not recorded")+
              " · Rishi-verified: NO");
            results.append(wrap);
          }
          localLink("View complete video evidence in this dashboard","#video-review");
          line(results,"The embedded official YouTube player can display ads. FreeTube/Invidious are separate architectures, not installed here. Manual preview does not authorize new learning or produce an evidence receipt.");
        } else if(lane==="book") {
          const info=await json("/api/books");
          if(lane!==selected)return;
          const books=Array.isArray(info.books)?info.books:[];
          summary.textContent=books.length+" locally registered books · indexing and line-by-line reading are distinct from understanding.";
          for(const book of books.slice(0,15)){
            const card=document.createElement("article");card.className="ai-learner-record";
            line(card,String(book.title||book.name||book.book_id||"Approved book"),"strong");
            line(card,"Lines processed: "+(book.lines_processed??book.processed_lines??"see book ledger")+
              " · Comprehension: unverified");
            results.append(card);
          }
          localLink("Read line-level book evidence","#books-evidence");
        } else {
          metric(results,names[lane],source);
          summary.textContent=names[lane]+" · approved-source activity and recorded findings (not verified mastery).";
          localLink(lane==="pdf"?"Inspect PDF assignments":"Inspect website assignments","#assignments");
          localLink("Review source evidence","#sources");
        }
      } catch(error){
        summary.textContent="AI Learner read-only evidence unavailable: "+String(error.message||error);
        start.disabled=true; stop.disabled=true;
      } finally {
        refreshing=false;
        if(rerun){rerun=false;refresh();}
      }
    }
    function routePage() {
      const active=location.hash==="#ai-learner";
      const main=el("ai-learner").closest("main");
      if(!main)return;
      for(const child of main.children)
        if(child!==el("ai-learner"))child.hidden=active;
      if(!active)stopPreview();
      for(const link of document.querySelectorAll('.navigation a[href^="#"]'))
        link.classList.toggle("selected", link.getAttribute("href")===location.hash);
      if(active) {
        el("ai-learner").hidden=false;
        el("ai-learner").scrollIntoView({block:"start"});
        refresh();
      }
    }
    window.addEventListener("hashchange",routePage);
    for(const lane of lanes)el("ai-tab-"+lane).addEventListener("click",()=>select(lane));
    el("ai-learner-open-preview").addEventListener("click",()=>{
      const job=approved.find(item=>item.job_id===choice.value);
      const id=job?validVideoId(job.target):null;
      stopPreview();
      if(!id){el("ai-learner-preview-hint").textContent="No valid, approved YouTube video is selected.";return;}
      // Official iframe is intentionally created only on a real user click.
      // It is a preview; our supervised collector has separate authenticated
      // job acceptance and MUST NOT count iframe currentTime as learning.
      const frame=document.createElement("iframe");
      frame.title="Approved YouTube video preview · not learning evidence";
      frame.src="https://www.youtube-nocookie.com/embed/"+id;
      frame.setAttribute("sandbox","allow-scripts allow-same-origin allow-presentation");
      frame.setAttribute("allow","encrypted-media; picture-in-picture; fullscreen");
      frame.setAttribute("referrerpolicy","strict-origin-when-cross-origin");
      frame.setAttribute("loading","lazy");
      frame.allowFullscreen=true;
      player.append(frame);
      el("ai-learner-preview-hint").textContent=
        "Official YouTube preview · advertisements may appear · playback/comprehension not independently verified.";
    });
    el("ai-learner-close-preview").addEventListener("click",()=>stopPreview());
    start.addEventListener("click",()=>{
      const real=el("learning-start");
      if(!real||real.disabled){banner.textContent="The existing worker cannot start; check hardware guard or lock.";return;}
      real.click(); banner.textContent="Start requested through existing SURYADEV worker controls.";
    });
    stop.addEventListener("click",()=>{
      const real=el("learning-stop");
      if(!real||real.disabled){banner.textContent="There is no dashboard-managed worker to stop.";return;}
      real.click(); banner.textContent="Graceful stop requested through existing worker.";
    });
    el("ai-learner-refresh").addEventListener("click",()=>refresh());
    // Keep stopped/unavailable status honest; no source writes or auto launch.
    document.addEventListener("visibilitychange",()=>{
      if(document.hidden)stopPreview();
      else refresh();
    });
    select("youtube");
    routePage();
    setInterval(()=>{if(location.hash==="#ai-learner")refresh();},15000);
  });
})();
