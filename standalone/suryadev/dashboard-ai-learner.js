/* AI Learner: one canonical SURYADEV worker, four active learning workspaces.
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
    let selectionGeneration = 0, previewJobId = null;
    const results = el("ai-learner-lane-results");
    const summary = el("ai-learner-lane-summary");
    const preview = el("ai-learner-youtube-preview");
    const player = el("ai-learner-player");
    const choice = el("ai-learner-video-choice");
    const banner = el("ai-learner-worker");
    const laneStatus=el("ai-learner-lane-status");
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
      // Keep the sidebar as the unique canonical navigation link for each
      // page: existing smoke/UI contracts expect exactly one per section.
      const link=document.createElement("button");
      link.type="button";link.textContent=label;
      link.className="ai-learner-evidence-link";
      link.addEventListener("click",()=>{location.hash=hash;});
      results.append(link);
    };
    function stopPreview() {
      // Destroy the iframe, not merely hide it: no background video,
      // provider player, tracking request or media clock remains alive.
      player.replaceChildren();
      previewJobId = null;
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
      // An old inbox record is not permanent permission to preview a URL.
      approved=jobs.filter(j => j && j.source_currently_approved===true &&
        validVideoId(j.target) && typeof j.job_id==="string");
      if(previewJobId && !approved.some(j=>j.job_id===previewJobId)) {
        stopPreview();
        el("ai-learner-preview-hint").textContent=
          "The previous video is no longer in the current approved source plan; preview closed.";
      }
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
      if(!approved.length) {
        stopPreview();
        el("ai-learner-preview-hint").textContent=
          "No currently approved YouTube video is available for in-page preview.";
      }
    }
    function select(lane) {
      if (!lanes.includes(lane)) return;
      selectionGeneration++;
      if (selected==="youtube" && lane!=="youtube")stopPreview();
      selected=lane;
      for(const name of lanes)
        el("ai-tab-"+name).setAttribute("aria-pressed", String(name===lane));
      el("ai-learner-lane-heading").textContent=names[lane]+" · recorded evidence";
      preview.hidden=lane!=="youtube";
      el("ai-learner-book-tools").hidden=lane!=="book";
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
      const lane=selected, generation=selectionGeneration;
      try {
        const [control,live,readiness]=await Promise.all([
          json("/api/learning/control"),json("/api/live"),
          json("/api/learning/readiness")
        ]);
        if(lane!==selected || generation!==selectionGeneration)return;
        const readinessBox=el("ai-learner-readiness");
        readinessBox.replaceChildren();
        const active=readiness.worker_managed_running || readiness.worker_external_lock;
        line(readinessBox,(active?"Learning worker active":"No confirmed active worker")+
          " · Approved videos "+Number(readiness.approved_videos||0)+
          " · Eligible fresh "+(readiness.unattempted_approved_videos??"unverified")+
          " · Trial selected "+(readiness.selected_videos??"unverified")+
          " · Approved books "+Number(readiness.approved_books||0)+
          " · Active books "+(readiness.book_runtime_fresh?
              readiness.reported_active_books:"stale/unverified"),"strong");
        for(const reason of (readiness.reasons||[]).slice(0,5))
          line(readinessBox,"• "+reason);
        for(const error of (readiness.errors||[]).slice(0,2))
          line(readinessBox,"Verification error: "+error);
        banner.textContent=control.managed_running ? "● Active · Worker "+control.managed_pid :
          control.external_worker_active ? "◉ External worker holds lock · no duplicate" :
          "○ Paused · approved sources retained";
        banner.dataset.state=control.managed_running?"running":
          control.external_worker_active?"blocked":"paused";
        const stamp=el("ai-studio-last-update");
        if(stamp)stamp.textContent=live.time?
          "Last evidence update · "+new Date(Number(live.time)*1000).toLocaleTimeString():
          "Worker status received · timestamps unverified";
        laneStatus.replaceChildren();
        for(const kind of ["youtube","pdf","website","book"]) {
          const stats=(live.sources||{})[kind]||{};
          const node=document.createElement("div");
          node.className="ai-studio-lane-tile";
          const label=document.createElement("strong");
          label.textContent=names[kind];
          const detail=document.createElement("span");
          detail.textContent=kind==="book"?
            "Indexed/reading checkpoints below":
            "Running "+Number(stats.running||0)+" · Queued "+Number(stats.queued||0)+
            " · Recorded "+Number(stats.total||0);
          node.append(label,detail);
          laneStatus.append(node);
        }
        const source=(live.sources||{})[lane]||{};
        results.replaceChildren();
        if(lane==="youtube") {
          const [review,audit]=await Promise.all([
            json("/api/video/review"),json("/api/youtube/audit")]);
          if(lane!==selected || generation!==selectionGeneration)return;
          metric(results,"YouTube jobs",source);
          if (review.media_health) {
            const media=review.media_health;
            line(results,"Latest GARUDANETRA media observation · player: "+
              (media.player_state||"unverified")+" · position: "+
              (media.source_position_seconds??"not recorded")+"s · measured speed ceiling: "+
              (media.measured_speed_ceiling_x??"unverified")+"× · learning not verified");
          }
          drawVideos(Array.isArray(review.jobs)?review.jobs:[]);
          summary.textContent=(review.auto_enabled?"Approved-video observation enabled":"Video observation not enabled")+
            " · Active: "+(review.active_job||"none")+
            " · Browser evidence: "+(audit.browser_observations||[]).length+
            " · Rishi examination: not verified";
          for(const item of (audit.browser_observations||[]).slice(0,30)) {
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
          line(results,"Observer records above are historical. Continuous video learning uses the single supervised worker; a successful short playback test does not verify a complete lecture.");
          line(results,"The embedded official YouTube player can display ads. FreeTube/Invidious are separate architectures, not installed here. Manual preview does not authorize new learning or produce an evidence receipt.");
        } else if(lane==="book") {
          const info=await json("/api/books");
          if(lane!==selected || generation!==selectionGeneration)return;
          const books=Array.isArray(info.books)?info.books:[];
          summary.textContent=books.length+" locally registered books · indexing and line-by-line reading are distinct from understanding.";
          for(const book of books.slice(0,30)){
            const card=document.createElement("article");card.className="ai-learner-record";
            line(card,String(book.title||book.name||book.book_id||"Approved book"),"strong");
            const sessions=book.sessions && typeof book.sessions==="object"?book.sessions:{};
            const modes=Object.keys(sessions).filter(mode=>mode.startsWith("ollama:"));
            if(!modes.length)line(card,"Indexed "+(book.lines_indexed??"unknown")+
              " lines · AI reading not recorded · Rishi exam pending");
            for(const mode of modes) {
              const reading=sessions[mode]||{};
              line(card,mode+" · Lines: "+(reading.lines_processed??"unknown")+
                " / "+(reading.lines_total??book.lines_indexed??"unknown")+
                " · Steps: "+(reading.model_steps_completed??0)+
                " · Last line reached: "+(reading.reached_end===true?"yes":"unverified")+
                " · Understanding: unverified");
              if(reading.last_error)line(card,"Last error: "+reading.last_error);
            }
            line(card,"Visual items examined: "+(book.visual_items_examined??"unverified")+
              " · BRAHMAGYAN candidate receipts: "+(book.brahmagyan_candidate_receipts??0)+
              " · Independent Rishi exam: unverified");
            results.append(card);
          }
          line(results,"Use the source-line search directly below; progress and journal steps remain separate from verified comprehension.");
        } else {
          const records=await json("/api/tasks?kind="+lane+"&limit=12");
          if(lane!==selected || generation!==selectionGeneration)return;
          metric(results,names[lane],source);
          const jobs=Array.isArray(records.tasks)?records.tasks:[];
          summary.textContent=names[lane]+" · "+(records.total??jobs.length)+
            " recorded assignments (newest 12); extraction is not whole-source mastery.";
          if(!jobs.length)line(results,"No recorded "+names[lane].toLowerCase()+" assignments.");
          for(const job of jobs) {
            const card=document.createElement("article");card.className="ai-learner-record";
            line(card,(job.title||"Source task #"+job.id)+" · "+(job.status||"unknown"),"strong");
            line(card,"Source: "+(job.url||"not recorded"));
            line(card,"Extraction method: "+(job.method||"not recorded")+
              " · Coverage and comprehension: unverified");
            if(job.error)line(card,"Recorded error: "+job.error);
            const inspect=document.createElement("button");
            inspect.type="button"; inspect.className="ai-learner-evidence-link";
            inspect.textContent="Inspect source evidence in this workspace";
            const detail=document.createElement("div");
            inspect.addEventListener("click",async()=>{
              const id=Number(job.id);
              if(!Number.isSafeInteger(id)||id<1)return;
              inspect.disabled=true;
              detail.replaceChildren();line(detail,"Reading local task provenance…");
              try {
                const entry=await json("/api/tasks/"+id);
                if(entry.id!==id || entry.kind!==lane)throw Error("Task identity mismatch");
                if(lane!==selected || generation!==selectionGeneration)return;
                detail.replaceChildren();
                line(detail,"Evidence hash integrity: "+(entry.evidence_state||"not recorded"));
                if(entry.sha256)line(detail,"SHA-256: "+entry.sha256);
                const coverage=entry.coverage||{};
                line(detail,"Extraction: "+(coverage.coverage_status||"not verified")+
                  " · Browser: "+(coverage.browser_engine||"not recorded"));
                if(lane==="pdf")line(detail,"Text pages extracted: "+
                  (coverage.pages_extracted??"unknown")+" / "+
                  (coverage.pages_total??"unknown")+" · Visual coverage: unverified");
                if(lane==="website")line(detail,"Rendered text characters: "+
                  (coverage.rendered_visible_characters??"unknown")+
                  " · Full site coverage: unverified");
                if(entry.summary)line(detail,"Saved finding: "+entry.summary);
                if(entry.excerpt)line(detail,
                  "Recorded source excerpt (not full-source verification): "+
                  String(entry.excerpt).slice(0,2400));
                if(entry.error)line(detail,"Error: "+entry.error);
                line(detail,"BRAHMAGYAN/Rishi factual acceptance: not verified");
              } catch(error) {
                if(lane===selected && generation===selectionGeneration) {
                  detail.replaceChildren();
                  line(detail,"Cannot verify task evidence: "+String(error.message||error));
                }
              } finally {inspect.disabled=false;}
            });
            card.append(inspect,detail);
            results.append(card);
          }
          line(results,"Showing recent source tasks. The separate Evidence dashboard retains the full read-only archive; learning control remains here.");
        }
      } catch(error){
        if(lane===selected && generation===selectionGeneration){
          summary.textContent="AI Learner evidence unavailable: "+String(error.message||error)+
            ". The live worker control remains independent and can be checked above.";
        }
      } finally {
        refreshing=false;
        if(rerun){rerun=false;refresh();}
      }
    }
    // Dashboard-pages.js owns all main-menu navigation and visibility.
    // Close provider playback whenever the owner navigates elsewhere.
    document.addEventListener("suryadev-page-change",event=>{
      if(event.detail?.page!=="ai-learner")stopPreview();
      else refresh();
    });
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
      previewJobId=job.job_id;
      el("ai-learner-preview-hint").textContent=
        "Official YouTube preview · advertisements may appear · playback/comprehension not independently verified.";
    });
    el("ai-learner-close-preview").addEventListener("click",()=>stopPreview());
    el("ai-learner-refresh").addEventListener("click",()=>refresh());
    // Keep stopped/unavailable status honest; no source writes or auto launch.
    document.addEventListener("visibilitychange",()=>{
      if(document.hidden)stopPreview();
      else refresh();
    });
    select("youtube");
    setInterval(()=>{if(location.hash==="#ai-learner")refresh();},15000);
  });
})();
