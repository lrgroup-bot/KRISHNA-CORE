"use strict";
/* Vanilla JS: works offline, uses textContent for all research/source data. */
const $ = id => document.getElementById(id);
const format = n => Number(n || 0).toLocaleString();
const dateTime = value => value ? new Date(value * 1000).toLocaleString() : "Not recorded";
const textNode = (tag, value, className) => {
  const el = document.createElement(tag);
  el.textContent = String(value ?? "");
  if (className) el.className = className;
  return el;
};
const app = { offset: 0, limit: 25, total: 0, taskId: null,
              lastList: "", lastDetail: "", taskQuery: "", status: "", kind: "", refreshInProgress: false };

function clockTick() { $("clock").textContent = new Date().toLocaleTimeString(); }
function resourceGauge(name, value) {
  const row = textNode("div", "", "gauge");
  const head = textNode("div", "", "gauge-head");
  const percent = value !== undefined && value !== null && Number.isFinite(Number(value))
      ? Math.max(0, Math.min(100, Number(value))) : null;
  head.append(textNode("span", name), textNode("b", percent === null ? "Unavailable" : percent.toFixed(1) + "%"));
  const track = textNode("div", "", "track");
  const fill = textNode("div", "", "fill" + (percent !== null && percent >= 85 ? " high" : ""));
  fill.style.width = (percent ?? 0) + "%";
  track.append(fill); row.append(head, track);
  return row;
}
function renderLive(data) {
  $("total").textContent = format(data.total);
  $("done").textContent = format(data.status.done);
  $("queued").textContent = format(data.status.queued);
  $("findings").textContent = format(data.findings);
  $("updated").textContent = "Updated " + dateTime(data.time);

  const source = $("source-grid"); source.replaceChildren();
  for (const [kind, values] of Object.entries(data.sources || {})) {
    const card = textNode("div", "", "source-card " + kind);
    card.append(textNode("div", ({youtube:"▶ YouTube",pdf:"▤ PDF documents",website:"◎ Websites",other:"◇ Other sources"})[kind] || kind, "type"),
                textNode("strong", format(values.total)),
                textNode("div", "Queued " + format(values.queued) + "  ·  Running " +
                    format(values.running) + "  ·  Done " + format(values.done) +
                    "  ·  Failed " + format(values.failed), "detail"));
    source.append(card);
  }
  const gauges = $("gauges"); gauges.replaceChildren();
  const r = data.resources || {};
  if (r.available) {
    gauges.append(resourceGauge("CPU", r.cpu_percent),
        resourceGauge("Memory", r.ram_percent),
        resourceGauge("Storage", r.disk_percent),
        resourceGauge("GPU", r.gpu?.available ? r.gpu.usage_percent : null));
    $("network").textContent = "Network received: " + (Number(r.network_bytes_received_total || 0) / 1e9).toFixed(2) +
       " GB  ·  Sent: " + (Number(r.network_bytes_sent_total || 0) / 1e9).toFixed(2) +
       " GB (cumulative)";
  } else {
    gauges.append(textNode("div", "Telemetry unavailable: " + (r.reason || "psutil missing"), "empty-state"));
    $("network").textContent = "Hardware telemetry requires the optional psutil package.";
  }
  const diary = $("diary-list"); diary.replaceChildren();
  for (const day of (data.diary || []).slice(0, 28)) {
    const item = textNode("div", "", "diary-row");
    item.append(textNode("span", day.date), textNode("b", format(day.assignments) +
       " assigned · " + format(day.completed) + " worker-done"));
    diary.append(item);
  }
  if (!diary.childElementCount) diary.append(textNode("div", "No dated activity yet.", "empty-state"));
}
async function pollLive() {
  try {
    const response = await fetch("/api/live", {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    renderLive(await response.json());
    $("connection").textContent = "Online · local service";
    $("connection-dot").classList.remove("off");
    $("live-chip").classList.remove("off");
  } catch (error) {
    $("connection").textContent = "Disconnected · reconnecting";
    $("connection-dot").classList.add("off");
    $("live-chip").classList.add("off");
    $("updated").textContent = "Connection interrupted — last readings retained";
  }
}
function taskRow(task) {
  const row = textNode("button", "", "task-row");
  row.type = "button";
  row.setAttribute("aria-label", "Inspect assignment " + task.id + ", " + task.status);
  const left = textNode("span", "", "task-main");
  const icon = ({youtube:"▶",pdf:"▤",website:"◎",other:"◇"})[task.kind] || "◇";
  const source = textNode("span", icon, "source-icon " + task.kind);
  const label = textNode("span", "", "task-text");
  label.append(textNode("strong", "#" + task.id + " · " + (task.title || task.url)),
               textNode("small", task.kind.toUpperCase() + " · " + dateTime(task.created) + " · " + task.url));
  left.append(source, label);
  row.append(left, textNode("span", task.status, "state-pill " + task.status), textNode("span", "View ↗", "task-inspect"));
  row.addEventListener("click", () => openDetail(task.id));
  return row;
}
async function loadTasks() {
  if (app.refreshInProgress) return;
  app.refreshInProgress = true;
  const p = new URLSearchParams({offset: String(app.offset), limit: String(app.limit),
      q: app.taskQuery, kind: app.kind, status: app.status});
  try {
    const response = await fetch("/api/tasks?" + p.toString(), {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    const key = JSON.stringify(data);
    app.total = data.total;
    if (app.offset > 0 && app.offset >= app.total) {
      app.offset = Math.max(0, Math.floor(Math.max(0, app.total - 1) / app.limit) * app.limit);
      app.lastList = "";
      app.refreshInProgress = false;
      return loadTasks();
    }
    $("filtered-count").textContent = format(data.total);
    $("page-label").textContent = data.total
      ? (app.offset + 1) + "–" + (app.offset + data.tasks.length) + " of " + format(data.total)
      : "0 assignments";
    $("page-prev").disabled = app.offset === 0;
    $("page-next").disabled = !data.has_more;
    if (key !== app.lastList) {
      const list = $("task-list"); list.replaceChildren();
      if (!data.tasks.length) list.append(textNode("div", "No tasks match your search. Try another filter.", "empty-state"));
      for (const task of data.tasks) list.append(taskRow(task));
      app.lastList = key;
    }
  } catch (error) {
    $("task-list").replaceChildren(textNode("div", "Could not load assignments: " + error.message, "empty-state"));
    app.lastList = "";
  } finally {
    app.refreshInProgress = false;
  }
}
function filterChanged() {
  app.offset = 0; app.lastList = "";
  app.taskQuery = $("task-search").value.trim();
  app.status = $("status-filter").value;
  app.kind = $("kind-filter").value;
  loadTasks();
}
function detailField(name, value) {
  const box = textNode("div", "");
  box.append(textNode("b", name), textNode("span", value || "Not recorded"));
  return box;
}
function safeSourceLink(source) {
  const span = textNode("div", "", "detail-source");
  span.append(textNode("strong", "Source: "));
  try {
    const parsed = new URL(source);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") throw new Error("Non-web source");
    const link = document.createElement("a");
    link.href = parsed.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = source;
    span.append(link);
  } catch {
    span.append(textNode("span", source));
  }
  return span;
}
function renderDetail(task) {
  $("detail-title").textContent = "Assignment #" + task.id;
  const content = $("detail-content"); content.replaceChildren();
  const meta = textNode("div", "", "detail-meta");
  meta.append(textNode("span", task.kind.toUpperCase(), "state-pill running"),
              textNode("span", task.status, "state-pill " + task.status));
  content.append(meta, safeSourceLink(task.url));
  let banner = "This task is queued. Processing has not started.";
  let bannerClass = "detail-banner";
  if (task.status === "running") {banner = "The worker is processing this task. Its result is not recorded yet.";bannerClass += " info";}
  if (task.status === "done") {banner = "Worker completed this assignment. Full-source coverage and KRISHNA acceptance are NOT verified.";bannerClass += " good";}
  if (task.status === "failed") {banner = "Processing failed. See the error and unfinished checklist stages below.";bannerClass += " bad";}
  content.append(textNode("div", banner, bannerClass));
  if (task.stale_running) content.append(textNode("div", "This task has been running for over two hours without an update.", "detail-banner bad"));
  const grid = textNode("div", "", "detail-grid");
  grid.append(detailField("Assigned", dateTime(task.created)),
              detailField("Last updated", dateTime(task.updated)),
              detailField("Learning record", task.finding_id ? "#" + task.finding_id : "No record"),
              detailField("Summary method", task.method || "Not recorded"),
              detailField("Evidence integrity", String(task.evidence_state || "Unknown").replaceAll("_", " ")),
              detailField("Last finding", dateTime(task.learned_at)));
  content.append(grid);
  content.append(textNode("h3", "What is done / what remains", "detail-subtitle"));
  const steps = textNode("div", "", "steps");
  const symbols = {done:"✓",blocked:"!",pending:"·",unverified:"?"};
  for (const stage of task.steps || []) {
    const item = textNode("div", "", "step " + stage.state);
    const body = textNode("div", "");
    body.append(textNode("b", stage.name + " · " + stage.state.replace("_", " ")),
                textNode("p", stage.detail));
    item.append(textNode("span", symbols[stage.state] || "?", "step-icon"), body);
    steps.append(item);
  }
  content.append(steps);
  if (task.error) {
    content.append(textNode("h3", "Recorded error", "detail-subtitle"),
                   textNode("div", task.error, "result-pane error-pane"));
  }
  content.append(textNode("h3", "What SURYADEV recorded", "detail-subtitle"),
      textNode("div", task.summary || "No learning summary has been saved.", "result-pane"));
  if (task.excerpt) {
    content.append(textNode("h3", "Evidence excerpt", "detail-subtitle"),
                   textNode("div", task.excerpt, "result-pane"));
  }
  if (task.sha256) {
    content.append(textNode("h3", "Evidence SHA-256", "detail-subtitle"),
                   textNode("div", task.sha256, "evidence-hash"));
  }
  const actions = textNode("div", "", "detail-actions");
  const refresh = textNode("button", "↻ Refresh this task", "detail-action");
  refresh.type = "button";refresh.addEventListener("click", () => fetchDetail(task.id));
  actions.append(refresh);
  const close = textNode("button", "Close", "detail-action secondary");
  close.type = "button";close.addEventListener("click", () => $("task-dialog").close());
  actions.append(close);
  content.append(actions);
}
async function fetchDetail(id) {
  try {
    const response = await fetch("/api/tasks/" + encodeURIComponent(id), {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const task = await response.json();
    if (app.taskId === id && $("task-dialog").open) {
      const serialized = JSON.stringify(task);
      if (serialized !== app.lastDetail) {
        const scroller = $("detail-content");
        const scroll = scroller.scrollTop;
        renderDetail(task);
        scroller.scrollTop = scroll;
        app.lastDetail = serialized;
      }
    }
  } catch (error) {
    if (app.taskId === id && $("task-dialog").open)
      $("detail-content").replaceChildren(textNode("div", "Could not load task detail: " + error.message, "empty-state"));
  }
}
function openDetail(id) {
  app.taskId = id; app.lastDetail = "";
  $("detail-title").textContent = "Assignment #" + id;
  $("detail-content").replaceChildren(textNode("div", "Loading task evidence and completion checklist…", "empty-state"));
  if (!$("task-dialog").open) $("task-dialog").showModal();
  fetchDetail(id);
}
$("close-detail").addEventListener("click", () => $("task-dialog").close());
$("task-dialog").addEventListener("close", () => { app.taskId = null; app.lastDetail = ""; });
$("task-search").addEventListener("input", (() => {
  let timer;return () => {clearTimeout(timer);timer = setTimeout(filterChanged, 300);};
})());
$("status-filter").addEventListener("change", filterChanged);
$("kind-filter").addEventListener("change", filterChanged);
$("page-prev").addEventListener("click", () => {app.offset = Math.max(0, app.offset - app.limit);app.lastList = "";loadTasks();});
$("page-next").addEventListener("click", () => {app.offset += app.limit;app.lastList = "";loadTasks();});
clockTick();setInterval(clockTick, 1000);
pollLive();loadTasks();
setInterval(pollLive, 5000);
setInterval(loadTasks, 10000);
setInterval(() => {if (app.taskId && $("task-dialog").open) fetchDetail(app.taskId);}, 15000);
