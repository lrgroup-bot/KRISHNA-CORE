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
              lastList: "", lastDetail: "", taskQuery: "", status: "", kind: "", selectedDay: "",
              diaryCache: [], refreshInProgress: false,
              lastPulseFingerprint: null };

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
  // Book progress has one canonical detailed home in the Garudanetra
  // learning workspace; do not duplicate it in source and hardware cards.
  const gauges = $("gauges"); gauges.replaceChildren();
  const r = data.resources || {};
  if (r.available) {
    gauges.append(resourceGauge("CPU", r.cpu_percent),
        resourceGauge("Memory", r.ram_percent),
        resourceGauge("Storage", r.disk_percent),
        resourceGauge("GPU", r.gpu?.available ? r.gpu.usage_percent : null));
    const interfaceState = r.network_interface_up === true ? "Interface UP" :
      r.network_interface_up === false ? "Interface DOWN" : "Interface unverified";
    const link = Number(r.network_interface_speed_mbps);
    const linkState = Number.isFinite(link) && link > 0 ? " · Link "+format(link)+" Mbps" : "";
    const sourceReachability = r.internet_reachable === true
      ? " · Recent approved HTTPS source reached (not a bandwidth test)"
      : " · Internet reachability unverified";
    $("network").textContent = interfaceState + linkState + sourceReachability +
       " · Received: " + (Number(r.network_bytes_received_total || 0) / 1e9).toFixed(2) +
       " GB · Sent: " + (Number(r.network_bytes_sent_total || 0) / 1e9).toFixed(2) +
       " GB (cumulative; not internet speed)";
  } else {
    gauges.append(textNode("div", "Telemetry unavailable: " + (r.reason || "psutil missing"), "empty-state"));
    $("network").textContent = "Hardware telemetry requires the optional psutil package.";
  }
  app.diaryCache = data.diary || [];
  renderDiaryTiles();
  // Status counters are shown beside the task list and selected-day evidence.
  // Refresh those views as soon as SQLite's committed totals change, rather
  // than displaying a new Done count next to a stale Running task for 30s.
  const fingerprint = JSON.stringify({
    counts: data.status, findings: data.findings,
    days: (data.diary || []).map(x => [x.date,x.assignments,x.completed,x.failed,x.findings])
  });
  if (fingerprint !== app.lastPulseFingerprint) {
    app.lastPulseFingerprint = fingerprint;
    loadTasks();
    if (app.selectedDay) loadDiaryDay(app.selectedDay);
  }
}
async function pollLive() {
  try {
    const response = await window.suryadevRead("/api/live", {cache:"no-store"});
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
      q: app.taskQuery, kind: app.kind, status: app.status, date: app.selectedDay});
  try {
    const response = await window.suryadevRead("/api/tasks?" + p.toString(), {cache:"no-store"});
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
  let banner = "This task is queued. Processing has not started." +
      (task.queue_diagnosis?.message ? " " + task.queue_diagnosis.message : "");
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
  if (task.publisher_recovery) {
    const recovered = task.publisher_recovery;
    content.append(textNode("h3", "Approved publisher caption recovery", "detail-subtitle"));
    content.append(safeSourceLink(recovered.transcript_url));
    content.append(textNode("div", "Earlier YouTube extraction error: " +
      (recovered.previous_error || "Not recorded"), "result-pane"));
    content.append(textNode("div",
      "Recovered from publisher-hosted timed captions only. The original YouTube " +
      "request was blocked; video visuals, uncaptioned speech and complete " +
      "audiovisual coverage remain UNVERIFIED.", "detail-banner info"));
  }
  const coverage = task.coverage || {};
  content.append(textNode("h3", "Source coverage & learning provenance", "detail-subtitle"));
  if (Object.keys(coverage).length) {
    const coverFields = [
      ["Extraction status", coverage.coverage_status],
      ["Browser engine", coverage.browser_engine],
      ["Garudanetra Chromium tab opened", coverage.browser_tab_opened === true ? "Yes · closed after extraction" : ""],
      ["Rendered visible text characters", coverage.rendered_visible_characters],
      ["Browser final HTTPS URL", coverage.browser_final_url],
      ["PDF pages read as text", coverage.pages_total ? String(coverage.pages_extracted ?? 0) + "/" + String(coverage.pages_total) : ""],
      ["Timed caption cues", coverage.cue_count],
      ["Publisher caption source", coverage.publisher_transcript_url],
      ["Publisher transcript only", coverage.publisher_transcript_only === true ? "Yes · video playback not verified" : ""],
      ["Video duration (seconds)", coverage.duration_seconds],
      ["Transcript last cue (seconds)", coverage.last_cue_seconds],
      ["Caption gaps over 60 seconds", Array.isArray(coverage.long_uncaptioned_gaps) ? coverage.long_uncaptioned_gaps.length : ""],
      ["Text chunks presented to LLM", coverage.chunks_total ? String(coverage.chunks_summarized) + "/" + String(coverage.chunks_total) : ""],
      ["Summary coverage", coverage.summary_coverage],
      ["Evidence extracted (characters)", coverage.source_characters],
    ];
    const coverageGrid = textNode("div", "", "detail-grid");
    for (const [label, value] of coverFields) {
      if (value !== undefined && value !== null && value !== "")
        coverageGrid.append(detailField(label, String(value)));
    }
    content.append(coverageGrid);
    content.append(textNode("div", coverage.note || "These receipts describe text extraction, not full audiovisual comprehension.", "detail-banner info"));
  } else {
    const receiptMessage = task.status === "queued"
      ? "Not processed yet. Evidence and source coverage will be recorded after successful extraction."
      : task.status === "failed"
      ? "Processing failed before a source coverage receipt was saved. Check the recorded error."
      : "No source-by-source coverage receipt is available. Entire-source learning remains unverified.";
    content.append(textNode("div", receiptMessage, "detail-banner"));
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
    const response = await window.suryadevRead("/api/tasks/" + encodeURIComponent(id), {cache:"no-store"});
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

/* Day summaries and dated job inspections. All dates use laptop-local YYYY-MM-DD. */
const localToday = () => {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2,"0") +
         "-" + String(d.getDate()).padStart(2,"0");
};
function renderDiaryTiles() {
  const diary = $("diary-list");
  diary.replaceChildren();
  for (const day of app.diaryCache) {
    const item = textNode("button", "", "diary-row" + (day.date === app.selectedDay ? " selected" : ""));
    item.type = "button";
    item.setAttribute("aria-label", "View learning on " + day.date);
    const head = textNode("div", "", "day-head");
    const parts = day.date.split("-").map(Number);
    const label = new Date(parts[0], parts[1]-1, parts[2]).toLocaleDateString(undefined,
       {day:"numeric", month:"short", year:"numeric"});
    head.append(textNode("span", label), textNode("span", "↗", "day-icon"));
    const lines = textNode("div", "", "day-lines");
    lines.append(textNode("small", "Assigned: " + format(day.assignments) +
       "  •  Findings: " + format(day.findings)),
       textNode("b", "Finished: " + format(day.completed) + "  •  Failed: " + format(day.failed)));
    item.append(head, lines);
    item.addEventListener("click", () => selectDay(day.date, {scrollToReport:true}));
    diary.append(item);
  }
  if (!diary.childElementCount)
    diary.append(textNode("div", "No dated activity recorded yet. Choose a date above to check.", "empty-state"));
}
async function selectDay(day, {scrollToReport=false}={}) {
  if (day && !/^\d{4}-\d{2}-\d{2}$/.test(day)) return;
  app.selectedDay = day;
  $("date-main").value = day;
  $("date-selected-label").textContent = day ? "Selected learning date: " + day : "Showing all recorded dates";
  $("date-selected-count").textContent = day
      ? "Loading assignments and findings for this date…"
      : "All dates selected · the complete assignment history is visible.";
  app.offset = 0; app.lastList = "";
  renderDiaryTiles();
  loadTasks();
  const report = $("diary-report"); report.replaceChildren();
  if (!day) {
    report.append(textNode("div",
      "Select a date to see assigned work, findings, current terminal outcomes, and a clickable list of that day's tasks.",
      "diary-report-intro"));
  } else {
    report.append(textNode("div", "Loading learning activity for " + day + "…", "empty-state"));
    await loadDiaryDay(day);
  }
  if (scrollToReport) $("diary-report").scrollIntoView({behavior:"smooth",block:"nearest"});
}
async function loadDiaryDay(day) {
  const report = $("diary-report");
  try {
    const [statsResponse, tasksResponse] = await Promise.all([
      window.suryadevRead("/api/diary?date=" + encodeURIComponent(day), {cache:"no-store"}),
      window.suryadevRead("/api/tasks?date=" + encodeURIComponent(day) + "&limit=10", {cache:"no-store"})
    ]);
    if (!statsResponse.ok || !tasksResponse.ok) throw new Error("Daily activity is temporarily unavailable");
    const stats = await statsResponse.json();
    const activity = await tasksResponse.json();
    if (app.selectedDay !== day) return;
    $("date-selected-count").textContent =
        format(stats.assignments) + " assigned · " + format(stats.findings) + " findings · " +
        format(stats.completed) + " worker completed · " + format(stats.failed) + " failed · " +
        format(activity.total) + " related tasks.";
    report.replaceChildren();
    const title = textNode("div", "", "diary-report-head");
    const titleLeft = textNode("div", "");
    titleLeft.append(textNode("h3", "Learning activity · " + day),
                     textNode("p", "Assignments are grouped when created, completed, failed or saved as findings on this date."));
    title.append(titleLeft, textNode("span", format(activity.total) + " related tasks", "eyebrow-chip"));
    report.append(title);
    const counters = textNode("div", "", "diary-stats");
    for (const [value,label] of [[stats.assignments,"Assigned"],[stats.findings,"Findings saved"],
                                 [stats.completed,"Worker completed"],[stats.failed,"Worker failed"]]) {
      const item = textNode("div", "", "diary-stat");
      item.append(textNode("strong", format(value)), textNode("small", label));
      counters.append(item);
    }
    report.append(counters, textNode("div", "Tasks active or updated on this date", "diary-task-title"));
    if (!activity.tasks.length)
      report.append(textNode("div", "No matching activity was recorded for this date.", "empty-state"));
    for (const task of activity.tasks) {
      const btn = textNode("button", "", "diary-task");
      btn.type = "button";
      const name = textNode("span", "", "diary-task-name");
      name.append(textNode("strong", "#" + task.id + " · " + (task.title || task.url)));
      name.append(textNode("small",
          "Assigned " + dateTime(task.created) + " · Updated " + dateTime(task.updated)));
      btn.append(name, textNode("span", task.status + "  ↗", "diary-task-state"));
      btn.addEventListener("click", () => openDetail(task.id));
      report.append(btn);
    }
    if (activity.total > activity.tasks.length) {
      const more = textNode("button", "View all " + format(activity.total) + " tasks for this date ↗", "diary-view-all");
      more.type = "button";
      more.addEventListener("click", () => $("assignments").scrollIntoView({behavior:"smooth"}));
      report.append(more);
    }
  } catch (error) {
    if (app.selectedDay === day) {
      report.replaceChildren(textNode("div", "Date lookup failed: " + error.message, "empty-state"));
      $("date-selected-count").textContent = "Could not load this date: " + error.message;
    }
  }
}
/* The worker writes its own heartbeat. No invented task start times or progress percentages. */
function renderOperations(data) {
  const worker = data.worker || {};
  const state = worker.state || "offline";
  $("worker-state-label").textContent = state === "offline" ? "Worker paused" : "Worker: " + state.toUpperCase();
  const running = data.current || [];
  $("queue-count").textContent = format(data.queued_total || 0);
  if (running.length) {
    const first = running[0];
    $("active-work").textContent = "#" + first.id + " · " + first.kind.toUpperCase();
    $("active-details").textContent = first.url + " · Started " + dateTime(first.started_at) +
      " · Percentage not instrumented";
  } else {
    $("active-work").textContent = state === "paused" ? "Paused by resource guard" :
      state === "offline" ? "Ready to start learning" : "Idle / looking for tasks";
    $("active-details").textContent = state === "offline" ? "Use Start learning above to begin approved research." : (worker.reason || "No assignment currently marked running.");
  }
  $("next-check").textContent = worker.next_check_at ? new Date(worker.next_check_at * 1000).toLocaleTimeString() : "When started";
  $("worker-details").textContent = state === "offline" ?
    "Research polling is paused. Start learning above to activate it." :
    "Check interval: " + (worker.interval_seconds || "—") + " seconds · " + (worker.reason || state);
  const types = data.by_source || {};
  $("source-queue-counts").textContent =
    "▶ Video " + format(types.youtube?.queued || 0) +
    " · ▤ PDF " + format(types.pdf?.queued || 0) +
    " · ◎ Web " + format(types.website?.queued || 0) +
    " · Other " + format(types.other?.queued || 0);
  const upcoming = $("upcoming-jobs"); upcoming.replaceChildren();
  for (const task of (data.upcoming || [])) {
    const item = textNode("div", "", "operation-queue-item");
    item.append(textNode("span", "#" + task.id + " · " + task.kind.toUpperCase() +
       " · " + task.url));
    const btn = textNode("button", "Inspect ↗");
    btn.type = "button";
    btn.addEventListener("click", () => openDetail(task.id));
    item.append(btn);upcoming.append(item);
  }
  if (!(data.upcoming || []).length)
    upcoming.append(textNode("div", "No queued tasks in the current ledger.", "empty-state"));
  const feeder = data.feeder || {};
  $("feeder-status").textContent = feeder.last_run
    ? "Six-hour research feeder · Last discovery: " + dateTime(feeder.last_run) +
      " · New sources: " + format(feeder.added_total) +
      " · Next refresh: " + (feeder.next_run ? dateTime(feeder.next_run) : "not scheduled")
    : "Automatic approved-source discovery starts with the learning worker when a source plan is configured.";
  $("operations-note").textContent = worker.note || "No forecast available.";
  const connections = data.connections || {};
  for (const key of ["krishna","brahmagyan","rishi"]) {
    const detail = connections[key] || {};
    const connected = detail.connected === true;
    const readerActive = detail.reader_active === true && !connected;
    const led = $(key + "-led");
    led.className = "led" + (connected ? " green" : readerActive ? " amber" : "");
    led.title = detail.detail || "Not connected";
    $(key + "-led-label").textContent = connected ? "Connected" :
      readerActive ? "Reader active (unpaired)" : "Not connected";
  }
}
async function pollOperations() {
  try {
    const response = await window.suryadevRead("/api/operations", {cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const operations = await response.json();
    renderOperations(operations);
    // One request supplies both the mission pulse and Garudanetra workspace.
    document.dispatchEvent(new CustomEvent("suryadev:operations", {detail: operations}));
  } catch (e) {
    document.dispatchEvent(new CustomEvent("suryadev:operations-error"));
    $("worker-state-label").textContent = "Worker telemetry unavailable";
    for (const key of ["krishna","brahmagyan","rishi"]) {
      $(key+"-led").className = "led";
      $(key+"-led-label").textContent = "Unknown";
    }
  }
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
$("date-main").addEventListener("change", () => selectDay($("date-main").value));
$("date-today-main").addEventListener("click", () => selectDay(localToday()));
$("date-clear-main").addEventListener("click", () => selectDay(""));
function shiftDate(delta) {
  const parts = (app.selectedDay || localToday()).split("-").map(Number);
  const d = new Date(parts[0], parts[1]-1, parts[2]+delta, 12);
  const value = d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" +
                String(d.getDate()).padStart(2,"0");
  selectDay(value);
}
$("date-previous-main").addEventListener("click", () => shiftDate(-1));
$("date-next-main").addEventListener("click", () => shiftDate(1));


clockTick();setInterval(clockTick, 1000);
window.suryadevRead("/api/ui-version").then(r => r.ok ? r.json() : null)
  .then(data => {
    const version = document.getElementById("ui-version");
    if (version && data && data.version) version.textContent = "SURYADEV · " + data.version;
  }).catch(() => {});
pollLive();pollOperations();loadTasks();
setInterval(pollLive, 5000);
setInterval(pollOperations, 5000);
setInterval(() => {if (app.selectedDay) loadDiaryDay(app.selectedDay);}, 30000);
setInterval(loadTasks, 5000);
setInterval(() => {if (app.taskId && $("task-dialog").open) fetchDetail(app.taskId);}, 15000);
