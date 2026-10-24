"use strict";
/* Source lanes reflect real SQLite running jobs and observed browser tabs. */
(() => {
  const el = id => document.getElementById(id);
  const num = n => Math.max(0, Number(n || 0)).toLocaleString();
  function refresh(data) {
    const capacity = data.capacity || {};
    const netra = data.garudanetra || {};
    const processing = data.processing || {};
    const worker = data.worker || {};
    const hardware = data.hardware || {};
    const plan = data.research_plan || {};
    const continuity = data.continuity || {};
    const books = data.book_learning || {};
    const bookPool = data.concurrent_books || {};
    const videoPool = data.concurrent_videos || {};
    const bookActivity = books.activity || {};
    const bookActive = bookActivity.active === true;
    const workerOnline = !!worker.state &&
      !["offline", "stopped"].includes(worker.state);
    const schedulerOnline = workerOnline && capacity.state !== "offline";
    const limits = capacity.limits || {};
    const web = processing.website || {}, video = processing.youtube || {},
          pdf = processing.pdf || {};
    for (const [key,values,name] of [
      ["web",web,"website"], ["video",video,"youtube"],["pdf",pdf,"pdf"]
    ]) {
      el("netra-"+key+"-running").textContent = num(values.running);
      el("netra-"+key+"-capacity").textContent =
        schedulerOnline ? num(limits[name]) : "— · worker offline";
      el("netra-"+key+"-queued").textContent = num(values.queued);
    }
    el("netra-web-tabs").textContent = num(web.browser_tabs);
    const activeBooks = Number(bookPool.active || 0);
    const activeVideos = Number(videoPool.active || 0);
    el("netra-books-running").textContent = num(
      Math.max(bookActive ? 1 : 0, activeBooks));
    el("netra-video-observers").textContent = num(activeVideos);
    el("netra-books-approved").textContent = num(books.approved);
    el("netra-books-indexed").textContent = num(books.indexed);
    el("netra-books-lines").textContent =
      num(books.lines_processed) + " / " + num(books.lines_total);
    const bookNote = el("netra-books-state");
    if (books.error) {
      bookNote.textContent = books.error;
    } else if (activeBooks > 0) {
      bookNote.textContent = num(activeBooks) +
        " distinct approved books progressing · model calls serialized";
    } else if (bookActive) {
      bookNote.textContent =
        (bookActivity.state === "book_visual_in_progress"
          ? "Local vision audit in progress" : "Local Ollama reading in progress") +
        (bookActivity.title ? " · " + bookActivity.title : "");
    } else if (books.indexed) {
      bookNote.textContent = num(books.completed) + " text-complete · " +
        num(books.reading) + " partly read · " + num(books.visual_items_examined) +
        " visuals examined · understanding unverified";
    } else {
      bookNote.textContent = books.plan_present
        ? "Approved book plan found; no matching indexed book yet"
        : "No books indexed in this learning library yet.";
    }
    const ytAccess = capacity.youtube_access || {};
    const ytNote = el("netra-youtube-access");
    if (ytAccess.state === "rate_limited") {
      const until = Number(ytAccess.cooldown_until || 0);
      const time = Number.isFinite(until) && until > 0
        ? new Date(until * 1000).toLocaleTimeString() : "later";
      ytNote.textContent = "YouTube HTTP 429 · New captions paused until " + time +
        ". Failed jobs require manual retry.";
      ytNote.className = "netra-access-note rate-limited";
    } else {
      ytNote.textContent = "One requested caption language per job · provider access unverified";
      ytNote.className = "netra-access-note";
    }
    const badge = el("netra-engine-state");
    const alive = netra.state === "running";
    const activeTabs = Number(netra.open_tabs || 0);
    badge.textContent = alive && activeTabs > 0 ? "● Chromium browsing · " + num(activeTabs) + " tabs" :
      alive ? "○ Chromium ready · 0 active tabs" :
      capacity.browser_error ? "◉ Browser unavailable" :
      workerOnline ? "○ Chromium ready · no website tab" :
      "○ Browser standby · worker offline";
    badge.className = "netra-live-pill" +
      (alive && activeTabs > 0 ? " live" : capacity.browser_error ? " paused" : "");
    const active = Number(capacity.active_total || 0) + activeBooks + activeVideos;
    const max = Number(capacity.max_total || 0);
    const targets = capacity.target_slots || {website:10,youtube:10,pdf:100,book:5};
    el("netra-total-capacity").textContent = num(active) + " active / " + num(max) +
      " currently admitted · at most 3 concurrent tasks · 85% guard";
    el("netra-parallel-targets").textContent =
      "Workload ceilings (NOT guaranteed running): " + num(targets.website) + " websites · " +
      num(targets.youtube) + " approved video observers · " +
      num(targets.pdf) + " PDFs · " + num(targets.book) +
      " books queued as needed. Fresh-session execution limit: 3 total tasks, never 3 per source. Admitted now: " + num(max) + " total CPU/RAM slots; " +
      num(capacity.source_execution_slots || 0) + " sources, " +
      num(capacity.reserved_video_slots || 0) + " videos, " +
      num(capacity.reserved_book_slots || 0) + " books. " +
      "The three-task ceiling is an upper bound; actual admission drops with CPU/RAM headroom. Browser video and PDF completion remain evidence-based; YouTube rate limits are respected.";
    const healthy = schedulerOnline && capacity.safe === true;
    const reported = schedulerOnline ? capacity : hardware;
    const measured = key => reported[key] != null && Number.isFinite(Number(reported[key]))
      ? Math.round(Number(reported[key])) + "%" : "Unavailable";
    const cpu = measured("cpu_percent") + " CPU";
    const ram = measured("ram_percent") + " RAM";
    const continuityOnline = workerOnline && continuity.active === true;
    const ytBlocked = ytAccess.state === "rate_limited";
    const alternatives = Number(processing.website?.queued || 0) +
      Number(processing.website?.running || 0) +
      Number(processing.pdf?.queued || 0) +
      Number(processing.pdf?.running || 0);
    const continuityBar = el("netra-continuity-status");
    if (!workerOnline) {
      continuityBar.lastElementChild.textContent =
        "Inactive: start one learning worker or mission with an approved plan.";
    } else if (continuityOnline) {
      continuityBar.lastElementChild.textContent =
        (ytBlocked ? "YouTube rate-limited; approved websites and PDFs remain eligible. " :
         "Approved-source discovery active. ") +
        "Next source refresh: " +
        (continuity.next_refresh
          ? new Date(continuity.next_refresh * 1000).toLocaleTimeString()
          : "not reported") +
        " · New sources last cycle: " + num(continuity.added_total) +
        (continuity.publisher_recovered
          ? " · Publisher timed-caption recovery: " + num(continuity.publisher_recovered) +
            " (video visuals unverified)" : "") +
        (continuity.feed_error_count ? " · Feed errors: " + num(continuity.feed_error_count) : "") +
        ". Independent sources are not a substitute for the blocked video.";
    } else {
      continuityBar.lastElementChild.textContent =
        "Disabled. Start the worker with --plan or use the six-hour mission; " +
        "only manually queued sources will be processed.";
    }
    const missingPlan = !plan.present;
    const noSources = !Number(data.queued_total || 0) && !Number(data.running_total || 0);
    let heading, reason;
    if (!workerOnline) {
      heading = "Learning worker offline — dashboard is running";
      reason = cpu + " · " + ram +
        " · No active scheduler. Start one worker or the six-hour mission." +
        (missingPlan ? " The learning-plan.json file is missing." : "");
    } else if (!schedulerOnline) {
      heading = "Worker starting — awaiting fresh capacity readings";
      reason = cpu + " · " + ram +
        " · No recent scheduler sample. Check worker console for errors.";
    } else if (!healthy) {
      heading = "New research paused by live hardware guard";
      reason = cpu + " · " + ram + " · " +
        (capacity.reason || "Insufficient safe processing headroom");
    } else if (ytBlocked && alternatives > 0) {
      heading = "YouTube rate-limited — website/PDF research continues";
      reason = cpu + " · " + ram +
        " · Only approved independent sources are being studied; blocked video remains unverified.";
    } else if (bookActive) {
      heading = bookActivity.state === "book_visual_in_progress"
        ? "Book image/page inspection in progress"
        : "Book reading in progress on local Ollama";
      reason = cpu + " · " + ram + " · " +
        (bookActivity.title || "Approved local book") +
        " · Website browser remains idle unless a website is queued.";
    } else if (noSources || (ytBlocked && alternatives === 0 &&
               Number(processing.youtube?.queued || 0) > 0)) {
      heading = ytBlocked ? "YouTube paused — no independent source ready" :
                 "No live source jobs — previous research remains saved";
      reason = cpu + " · " + ram +
        " · History: " + num(data.by_source?.website?.done) + " web done, " +
        num(data.by_source?.pdf?.done) + " PDF done, " +
        num(data.by_source?.youtube?.done) + " YouTube done. " +
        (books.indexed ? num(books.indexed) + " indexed books. " : "") +
        (continuityOnline
           ? "Approved source refill is scheduled."
           : "No approved source refill is active.");
    } else {
      heading = "Automatic hardware admission enabled";
      reason = cpu + " · " + ram + " · " +
        (capacity.browser_error || capacity.reason || "Within hardware limits");
    }
    el("netra-capacity-heading").textContent = heading;
    el("netra-capacity-reason").textContent = reason +
      " · Local AI model: 1 generation at a time";
    if (!workerOnline) {
      const slots = Number(hardware.potential_total_if_worker_started || 0);
      el("netra-total-capacity").textContent =
        "0 active / worker offline" + (hardware.available ? " · " + num(slots) + " possible" : "");
    }
    el("netra-tab-heading").textContent =
      "Garudanetra Chromium: " + num(netra.open_tabs) +
      " actual browser tabs · limit " + num(netra.tab_limit || 4);
    el("netra-browser-detail").textContent = alive
      ? "Lightweight isolated headless Chromium; images, media, fonts and unrelated sites blocked"
      : "Browser opens automatically only for approved queued websites, when capacity permits.";
    const realTabs = new Map((netra.tabs || []).map(t=>[Number(t.job_id),t]));
    const running = Array.isArray(data.current) ? data.current : [];
    const tabs = el("netra-workspace-tabs");
    tabs.replaceChildren();
    el("netra-workspace-count").textContent =
      num(running.length + (bookActive ? 1 : 0));
    if (!running.length && !bookActive) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = !workerOnline
          ? "No learning worker is running. The dashboard observes activity but does not start a worker."
          : noSources
          ? "No live work right now: " +
            num(data.by_source?.website?.done) + " websites, " +
            num(data.by_source?.pdf?.done) + " PDFs and " +
            num(data.by_source?.youtube?.done) + " YouTube sources previously completed. " +
            num(books.indexed) + " books indexed. Historical work is not a running tab."
          : healthy
          ? "No sources running yet. The worker will open approved queued work when slots are available."
          : "No jobs active. Resource limits or worker startup are preventing new tasks.";
      tabs.append(empty);
      return;
    }
    if (bookActive) {
      const card = document.createElement("div");
      card.className = "netra-workspace-tab book";
      const ico = document.createElement("span");
      ico.className = "tab-icon";
      ico.textContent = "▧";
      const details = document.createElement("div");
      details.className = "tab-info";
      const title = document.createElement("strong");
      title.textContent = bookActivity.title || "Approved local book";
      const stage = document.createElement("small");
      stage.textContent = (bookActivity.state === "book_visual_in_progress"
        ? "Examining PDF pages / EPUB artwork using local vision"
        : "Reading original book lines on local Ollama") +
        " · " + num(bookActivity.processed_lines) + " / " +
        num(bookActivity.total_lines) + " lines at last checkpoint";
      const tag = document.createElement("span");
      tag.className = "tab-badge";
      tag.textContent = "Local book";
      details.append(title,stage);
      card.append(ico,details,tag);
      tabs.append(card);
    }
    for (const job of running) {
      const type = ["website","youtube","pdf"].includes(job.kind) ? job.kind : "other";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "netra-workspace-tab " + type;
      button.title = "Inspect recorded evidence for assignment #" + job.id;
      const icon = document.createElement("span");
      icon.className = "tab-icon";
      icon.textContent = ({website:"◎",youtube:"▶",pdf:"▤",other:"◇"})[type];
      const info = document.createElement("div");
      info.className = "tab-info";
      const title = document.createElement("strong");
      title.textContent = "#" + job.id + " · " + job.url;
      const description = document.createElement("small");
      const real = realTabs.get(Number(job.id));
      description.textContent = real ? "Garudanetra Chromium tab open · " +
          (real.stage || "rendering") :
          (type === "youtube" ? "YouTube caption extraction (not video playback)" :
           type === "pdf" ? "PDF pages being processed (not a Chromium tab)" :
           "Processing / awaiting Chromium render");
      info.append(title, description);
      const badge = document.createElement("span");
      badge.className = "tab-badge";
      badge.textContent = real ? "Browser open" : "Processing";
      button.append(icon, info, badge);
      button.addEventListener("click", () => {
        if (typeof openDetail === "function") openDetail(job.id);
      });
      tabs.append(button);
    }
  }
  // Reuse the single operations request issued by dashboard.js.
  document.addEventListener("suryadev:operations", event => refresh(event.detail));
  document.addEventListener("suryadev:operations-error", () => {
    el("netra-capacity-heading").textContent = "Parallel learning telemetry unavailable";
    el("netra-capacity-reason").textContent =
        "Cannot verify active source tabs or hardware admission until the local API responds.";
    el("netra-engine-state").textContent = "○ Offline / unknown";
  });
})();
