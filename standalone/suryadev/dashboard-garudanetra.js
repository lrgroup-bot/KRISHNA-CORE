"use strict";
/* Source lanes reflect real SQLite running jobs and observed browser tabs. */
(() => {
  const el = id => document.getElementById(id);
  const num = n => Math.max(0, Number(n || 0)).toLocaleString();
  function refresh(data) {
    const capacity = data.capacity || {};
    const netra = data.garudanetra || {};
    const processing = data.processing || {};
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
    const healthy = capacity.safe === true;
    el("netra-capacity-heading").textContent =
      healthy ? "Automatic hardware admission enabled" : "New tasks paused for laptop safety";
    const cpu = Number.isFinite(Number(capacity.cpu_percent)) && capacity.cpu_percent != null ?
       Math.round(Number(capacity.cpu_percent)) + "% CPU" : "CPU unavailable";
    const ram = Number.isFinite(Number(capacity.ram_percent)) && capacity.ram_percent != null ?
       Math.round(Number(capacity.ram_percent)) + "% RAM" : "RAM unavailable";
    el("netra-capacity-reason").textContent =
      cpu + " · " + ram + " · " +
      (capacity.browser_error || capacity.reason || "Waiting for worker telemetry") +
      " · Local AI model: 1 generation at a time";
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
      empty.textContent = healthy
          ? "No source jobs running. SURYADEV will open approved queued work when capacity permits."
          : "No jobs active. Check worker and hardware admission status above.";
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
