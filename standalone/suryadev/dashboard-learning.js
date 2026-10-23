/* One local dashboard worker controller. Never auto-start without an explicit
 * owner click; subsequent source discovery is automatic within the approved plan.
 */
"use strict";
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const el = id => document.getElementById(id);
    const start = el("learning-start");
    const stop = el("learning-stop");
    if (!start || !stop) return;
    const state = el("learning-service-state");
    const note = el("learning-service-note");
    const responseText = el("learning-action-status");
    const model = el("learning-model");
    let csrf = null;
    let operation = false;

    async function auth() {
      if (csrf) return csrf;
      const res = await window.suryadevRead("/api/operator/settings");
      if (!res.ok) throw Error("Cannot obtain local authorization: HTTP " + res.status);
      csrf = (await res.json()).csrf_token;
      if (!csrf) throw Error("Local authorization unavailable");
      return csrf;
    }
    async function post(path, payload) {
      const token = await auth();
      const res = await fetch(path, {
        method:"POST", credentials:"same-origin",
        headers:{"Content-Type":"application/json","X-SURYADEV-CSRF":token},
        body:JSON.stringify(payload)
      });
      const body = await res.json();
      if (!res.ok) throw Error(body.error || "HTTP " + res.status);
      return body;
    }
    async function refresh() {
      try {
        const res = await window.suryadevRead("/api/learning/control");
        if (!res.ok) throw Error("HTTP " + res.status);
        const d = await res.json();
        const running = Boolean(d.managed_running);
        const manual = !running && Boolean(d.worker_heartbeat_recent);
        state.textContent = running ? "Learning active · local worker" :
          manual ? "Learning active · external worker" : "Learning paused · ready";
        note.textContent = running
          ? "Researching approved sources; 30-second idle checks. Worker PID " + d.managed_pid
          : manual
            ? "Another worker is active. This dashboard will not start a duplicate."
            : d.plan_exists
              ? "Ready for continuous approved-source research. No Core pairing required."
              : "No learning plan yet. Start processes existing queued tasks; add approved sources for automatic replenishment.";
        el("activity-short-state").textContent = running ? "Worker active" : manual ? "External worker" : "Paused";
        start.disabled = running || manual || operation;
        stop.disabled = !running || operation;
        model.disabled = running || manual || operation;
      } catch (err) {
        state.textContent = "Worker control unavailable";
        note.textContent = String(err.message || err);
        start.disabled = true; stop.disabled = true;
      }
    }
    async function execute(path, data) {
      operation = true;
      start.disabled = true; stop.disabled = true;
      try {
        const result = await post(path, data);
        responseText.textContent = result.note || result.status || "Operation accepted";
      } catch (err) {
        responseText.textContent = "Learning control: " + (err.message || err);
      } finally {
        operation = false;
        await refresh();
      }
    }
    start.addEventListener("click", () => execute("/api/operator/learning/start", {model:model.value}));
    stop.addEventListener("click", () => execute("/api/operator/learning/stop", {}));
    refresh();
    setInterval(refresh, 5000);
  });
})();
