"use strict";
/* SURYADEV operator settings: only same-origin local API, never automatic pairing. */
(() => {
  const node = id => document.getElementById(id);
  let csrf = "";
  let activeData = "";
  let latestStorageCheck = null;

  const result = (id, message, type="") => {
    const target = node(id);
    target.textContent = String(message);
    target.className = "settings-result" + (type ? " " + type : "");
  };
  const gb = value => Number.isFinite(Number(value)) ?
    (Number(value) / 1073741824).toFixed(2) + " GiB" : "Unavailable";
  const fail = error => error instanceof Error ? error.message : String(error);
  const busy = async (button, task) => {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "Working…";
    try { return await task(); }
    finally { button.disabled = false; button.textContent = original; }
  };
  async function readSettings() {
    const response = await fetch("/api/operator/settings", {cache:"no-store"});
    if (!response.ok) throw Error("Cannot read local operator settings ("+response.status+")");
    const data = await response.json();
    csrf = data.csrf_token || "";
    activeData = data.active_data_root || "";
    node("server-ip").value = data.server?.ip || "";
    node("server-port").value = data.server?.port || 8766;
    node("active-data-root").textContent = activeData || "Unknown";
    const storage = data.storage || {};
    const enough = storage.sufficient_space === true;
    const badge = node("active-disk-space");
    badge.textContent = gb(storage.free_bytes) + " free · " +
                        (enough ? "Healthy" : "Low/unknown space");
    badge.className = "space-pill" + (enough ? "" : " low");
    node("cleanup-enabled").checked = data.cleanup?.enabled === true;
    node("cleanup-hours").value = String(data.cleanup?.retention_hours ?? 0);
    if (data.pending_data_root) {
      result("storage-result", "Verified copy exists at: " + data.pending_data_root +
        ". The original is still active. Restart all SURYADEV processes with --data set to the new directory.",
        "success");
    }
    return data;
  }
  async function post(path, payload) {
    if (!csrf) await readSettings();
    const response = await fetch(path, {
      method:"POST", cache:"no-store",
      headers:{"Content-Type":"application/json", "X-SURYADEV-CSRF":csrf},
      body:JSON.stringify(payload)
    });
    let body;
    try { body = await response.json(); }
    catch { throw Error("Unexpected local server response"); }
    if (!response.ok) throw Error(body.error || "Request failed: " + response.status);
    return body;
  }
  function open(id) {
    const dialog = node(id);
    if (!dialog.open) dialog.showModal();
    readSettings().catch(err => result(
      id === "server-settings-dialog" ? "server-save-result" : "storage-result",
      fail(err), "error"
    ));
  }
  node("open-server-settings").addEventListener("click", () => open("server-settings-dialog"));
  node("open-storage-settings").addEventListener("click", () => open("storage-settings-dialog"));
  node("close-server-settings").addEventListener("click", () => node("server-settings-dialog").close());
  node("close-storage-settings").addEventListener("click", () => node("storage-settings-dialog").close());
  const coreValues = () => ({
    ip:node("server-ip").value.trim(), port:Number(node("server-port").value)
  });
  node("save-server-ip").addEventListener("click", () => busy(node("save-server-ip"), async () => {
    try {
      const data = await post("/api/operator/server/save", coreValues());
      result("server-save-result",
         "Saved locally: " + data.server.ip + ":" + data.server.port +
         " · Not paired. Diagnose next to check network reachability.", "success");
    } catch(err) { result("server-save-result", fail(err), "error"); }
  }));
  node("diagnose-server").addEventListener("click", () => busy(node("diagnose-server"), async () => {
    const fields = ["diag-tcp","diag-health","diag-identity","diag-pairing"];
    for (const id of fields) node(id).textContent = "Checking…";
    try {
      const info = await post("/api/operator/server/diagnose", coreValues());
      node("diag-tcp").textContent = info.tcp_open ? "Open ✓" : "Unreachable";
      node("diag-health").textContent = info.health_reachable ? "Responding ✓" :
                        (info.health_status ? "HTTP " + info.health_status : "Not verified");
      node("diag-identity").textContent = "Unverified";
      node("diag-pairing").textContent = "Not paired";
      node("diagnosis-message").textContent = info.message +
        (info.reported_instance_id ? " · Reported candidate ID: " + info.reported_instance_id : "");
    } catch(err) {
      for (const id of fields) node(id).textContent = "Not verified";
      node("diag-pairing").textContent = "Not paired";
      node("diagnosis-message").textContent = fail(err);
    }
  }));
  node("browse-storage").addEventListener("click", () => busy(node("browse-storage"), async () => {
    result("storage-result", "Opening Windows folder selector on the laptop…");
    try {
      const data = await post("/api/operator/storage/browse", {});
      if (data.selected_path) {
        node("storage-location").value = data.selected_path;
        latestStorageCheck = null;
        result("storage-result", "Folder selected. Click Check free disk space before copying.");
      } else {
        result("storage-result", "Folder selection cancelled. You may type a local path instead.");
      }
    } catch(err) { result("storage-result", fail(err), "error"); }
  }));
  node("storage-location").addEventListener("input", () => { latestStorageCheck = null; });
  async function checkStorage() {
    const data = await post("/api/operator/storage/check", {
      path:node("storage-location").value.trim()
    });
    latestStorageCheck = data;
    result("storage-result",
      "Target: " + data.path + " · Available: " + gb(data.free_bytes) +
      " · Required: " + gb(data.minimum_required_bytes) +
      " · Research data to copy: " + gb(data.bytes_to_copy) +
      " · " + (data.ready_to_migrate ? "Ready for safe migration" :
         "Not ready: select an empty folder with sufficient free space"),
      data.ready_to_migrate ? "success" : "error");
    return data;
  }
  node("check-storage").addEventListener("click", () => busy(node("check-storage"), async () => {
    try { await checkStorage(); }
    catch(err) { result("storage-result", fail(err), "error"); }
  }));
  node("migrate-storage").addEventListener("click", () => busy(node("migrate-storage"), async () => {
    const path = node("storage-location").value.trim();
    try {
      const info = await checkStorage();
      if (!info.ready_to_migrate) throw Error("Disk validation failed; nothing copied.");
      if (info.is_active) {
        result("storage-result", "This directory is already active. No migration needed.", "success");
        return;
      }
      if (!window.confirm("Create a verified COPY of SURYADEV's entire data directory at:\n"+
          info.path+"\n\nThe live dashboard will stay on its current folder until you manually "+
          "restart all SURYADEV processes. No original data will be deleted. Proceed?")) {
        return;
      }
      result("storage-result", "Copying and checking research data…");
      const data = await post("/api/operator/storage/migrate", {path,confirm:"MIGRATE"});
      result("storage-result", data.message, "success");
      const display = node("storage-restart-info");
      if (data.restart_required) {
        display.hidden = false;
        display.textContent = "Verified destination: " + data.copied_to +
          "\nEvidence files verified: " + data.evidence_verified +
          "\n\nNEXT: Stop the dashboard and any workers. Restart with:" +
          "\npython suryadev_extras.py --data \"" + data.copied_to +
          "\" dashboard --port 8769" +
          "\nUse the same --data path when starting the mission or worker." +
          "\nThe original folder was NOT deleted.";
      }
    } catch(err) { result("storage-result", fail(err), "error"); }
  }));
  const cleanupValues = () => ({
    enabled:node("cleanup-enabled").checked,
    retention_hours:Number(node("cleanup-hours").value)
  });
  node("save-cleanup").addEventListener("click", () => busy(node("save-cleanup"), async () => {
    try {
      const data = await post("/api/operator/cleanup/save", cleanupValues());
      result("cleanup-result", data.message + " · Enabled: " + data.cleanup.enabled +
         " · Retention: " + data.cleanup.retention_hours + " hours.", "success");
    } catch(err) { result("cleanup-result", fail(err), "error"); }
  }));
  const formatCleanup = (r, preview) =>
    (preview ? "Preview: " + r.eligible_jobs + " eligible staged jobs (" :
      "Cleanup: " + r.deleted_jobs + " staged jobs removed (") +
    gb(preview ? r.eligible_bytes : r.deleted_bytes) + " processed). " +
    "Other skipped: " + r.skipped + ". Errors: " + r.errors +
    ". Database, original media and evidence retained.";
  node("preview-cleanup").addEventListener("click", () => busy(node("preview-cleanup"), async () => {
    try {
      const data = await post("/api/operator/cleanup/run", {dry_run:true});
      result("cleanup-result", data.enabled ? formatCleanup(data,true) :
        "Automatic cleanup is disabled. Enable and save the policy to preview eligible files.",
        data.errors ? "error" : "success");
    } catch(err) { result("cleanup-result", fail(err), "error"); }
  }));
  node("run-cleanup").addEventListener("click", () => busy(node("run-cleanup"), async () => {
    if (!window.confirm("Delete ONLY verified SURYADEV-owned extracted-text staging copies "+
      "from completed jobs? Permanent evidence, original files and database are retained.")) return;
    try {
      const data = await post("/api/operator/cleanup/run", {dry_run:false});
      result("cleanup-result", data.enabled ? formatCleanup(data,false) :
        "Cleanup is disabled. Change policy and save it first.",
        data.errors ? "error" : "success");
    } catch(err) { result("cleanup-result", fail(err), "error"); }
  }));
})();
