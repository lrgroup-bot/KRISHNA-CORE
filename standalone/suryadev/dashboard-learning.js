/* Learning control and read-only approved source status. No manual source entry. */
"use strict";
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const el = id => document.getElementById(id);
    const start = el("learning-start");
    const stop = el("learning-stop");
    const delegation = el("learning-core-delegation");
    const coreStatus = el("learning-core-status");
    if (!start || !stop || !delegation || !coreStatus) return;
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
        if (typeof d.can_start !== "boolean" ||
            typeof d.external_worker_active !== "boolean") {
          throw Error("Dashboard backend is outdated; reinstall and restart SURYADEV to enable Start Learning");
        }
        const core = d.core_dispatch || {};
        const paired = core.ready === true;
        const delegated = d.paired_core_host_delegation === true;
        const workspace = el("learning-workspace-state");
        if (workspace) {
          workspace.textContent = d.workspace_mode === "fresh"
            ? "FRESH WORKSPACE ACTIVE · Previous learning retained outside this session · " +
              "Maximum " + Number(d.workspace_active_task_limit || 3) +
              " simultaneous tasks total · 85% hardware guard"
            : "EXISTING WORKSPACE · Earlier assignments are still in this data directory. " +
              "Run start-fresh-workspace.ps1 from the updated installation to begin a blank session.";
        }
        coreStatus.textContent = paired
          ? "KRISHNA fleet credentials validated locally · " +
            (delegated ? "Delegated sources on " + (d.paired_core_approved_host_count || 0) +
             " approved hosts" : "Exact approved URLs only") + " · Live connection unverified"
          : "KRISHNA feed not paired: " + (core.reason || "verified device pairing required") +
            " · local fallback remains available";
        delegation.disabled = !paired || operation;
        delegation.textContent = !paired ? "KRISHNA delegation unavailable" :
          delegated ? "Disable Core source delegation" : "Allow KRISHNA to select approved-host sources";
        const running = Boolean(d.managed_running);
        // An old heartbeat is diagnostic history, not proof of a running worker.
        const manual = !running && Boolean(d.external_worker_active);
        state.textContent = running ? "Learning active · local worker" :
          manual ? "Learning active · external worker" : "Learning paused · ready";
        note.textContent = running
          ? ((paired ? "KRISHNA fleet polling configured" : "Local-only research") +
             " · Worker PID " + d.managed_pid)
          : manual
            ? (d.blocked_reason || "A separate research/video worker holds the OS lock.")
            : d.plan_exists
              ? "Ready for continuous approved-source research. No Core pairing required."
              : "No learning plan yet. Start processes existing queued tasks; configure the approved curriculum outside this read-only frontend.";
        el("activity-short-state").textContent = running ? "Worker active" : manual ? "External worker" : "Paused";
        start.disabled = !d.can_start || operation;
        stop.disabled = !running || operation;
        model.disabled = running || manual || operation;
      } catch (err) {
        state.textContent = "Worker control unavailable";
        note.textContent = "Cannot read worker status: " + String(err.message || err) +
          ". Check /api/learning/control and restart the updated dashboard if needed.";
        start.disabled = true; stop.disabled = true; delegation.disabled = true; delegation.disabled = true;
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
    delegation.addEventListener("click", async () => {
      const enabling = !delegation.textContent.startsWith("Disable");
      if (enabling && !window.confirm(
        "Authorize paired KRISHNA to choose new public HTTPS URLs ONLY on the current approved host list? This does not authorize new hosts, logins, paid services or evidence acceptance.")) return;
      await execute("/api/operator/learning/delegate-core", {enabled:enabling});
    });
    start.addEventListener("click", () => execute("/api/operator/learning/start", {model:model.value}));
    stop.addEventListener("click", () => execute("/api/operator/learning/stop", {}));
    refresh();
    setInterval(refresh, 5000);
  });
})();
