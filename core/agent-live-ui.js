/* KRISHNA live status UI adapter: no paid services, no fabricated activity.
 * Requires an authenticated same-origin endpoint returning validated agent-live.v1
 * rows. Rendering is text-only to avoid HTML injection from remote metadata.
 */
(function (root) {
  "use strict";
  function validate(row) {
    if (!row || row.schema !== "krishna.agent-live.v1" ||
        typeof row.agent_id !== "string" ||
        !["IDLE", "WORKING", "HEALING", "BLOCKED", "OFFLINE", "UNKNOWN", "STALE"].includes(row.display_status) ||
        !Number.isSafeInteger(row.sequence) || row.sequence < 0 ||
        typeof row.stale !== "boolean") {
      throw new Error("Invalid agent live status payload");
    }
    return row;
  }
  function render(container, rows) {
    if (!container || typeof container.replaceChildren !== "function") {
      throw new Error("Missing agent status container");
    }
    if (!Array.isArray(rows) || rows.length > 256) {
      throw new Error("Invalid agent status list");
    }
    const doc = container.ownerDocument;
    const fragment = doc.createDocumentFragment();
    rows.forEach(function (item) {
      const row = validate(item);
      const line = doc.createElement("div");
      line.className = "krishna-agent-live";
      line.dataset.state = row.display_status.toLowerCase();
      line.textContent = row.agent_id + " — " + row.display_status +
        (row.task_id ? " — " + String(row.task_id).slice(0, 128) : "");
      fragment.appendChild(line);
    });
    container.replaceChildren(fragment);
  }
  async function refresh(container, endpoint) {
    const target = new URL(endpoint, root.location.href);
    if (target.origin !== root.location.origin || target.protocol !== root.location.protocol) {
      throw new Error("Cross-origin live status endpoints are forbidden");
    }
    const response = await root.fetch(target.href, { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error("Live status request failed");
    const data = await response.json();
    render(container, data.agents);
    return data.agents.length;
  }
  root.KrishnaLiveAgents = Object.freeze({ validate: validate, render: render, refresh: refresh });
})(window);
