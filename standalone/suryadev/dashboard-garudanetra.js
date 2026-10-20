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
      el("netra-"+key+"-capacity").textContent = num(limits[name]);
      el("netra-"+key+"-queued").textContent = num(values.queued);
    }
    el("netra-web-tabs").textContent = num(web.browser_tabs);
    const badge = el("netra-engine-state");
    const alive = netra.state === "running";
    badge.textContent = alive ? "● Chromium browser ready" :
      capacity.browser_error ? "◉ Browser unavailable" : "○ Browser standby";
    badge.className = "netra-live-pill" + (alive ? " live" : capacity.browser_error ? " paused" : "");
    const active = Number(capacity.active_total || 0);
    const max = Number(capacity.max_total || 0);
    el("netra-total-capacity").textContent = num(active) + " active / " + num(max) + " allowed";
    const healthy = schedulerOnline && capacity.safe === true;
    const reported = schedulerOnline ? capacity : hardware;
    const measured = key => reported[key] != null && Number.isFinite(Number(reported[key]))
      ? Math.round(Number(reported[key])) + "%" : "Unavailable";
    const cpu = measured("cpu_percent") + " CPU";
    const ram = measured("ram_percent") + " RAM";
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
    } else if (noSources) {
      heading = "Learning worker ready — approved queue is empty";
      reason = cpu + " · " + ram +
        " · Add approved sources or run the six-hour mission with a valid research plan.";
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
    el("netra-workspace-count").textContent = num(running.length);
    if (!running.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = !workerOnline
          ? "No learning worker is running. The dashboard observes activity but does not start a worker."
          : noSources
          ? "The learning queue is empty. Add approved sources or start the research mission."
          : healthy
          ? "No sources running yet. The worker will open approved queued work when slots are available."
          : "No jobs active. Resource limits or worker startup are preventing new tasks.";
      tabs.append(empty);
      return;
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
  async function poll() {
    try {
      const response = await fetch("/api/operations", {cache:"no-store"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      refresh(await response.json());
    } catch (_err) {
      el("netra-capacity-heading").textContent = "Parallel learning telemetry unavailable";
      el("netra-capacity-reason").textContent =
          "Cannot verify active source tabs or hardware admission until the dashboard API responds.";
      el("netra-engine-state").textContent = "○ Offline / unknown";
    }
  }
  poll();
  setInterval(poll, 5000);
})();
