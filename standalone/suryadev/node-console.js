/* SURYADEV Node Control — source data is never inserted as HTML.
 * Local-only, one read-only retry helper; mutations are same-origin + CSRF.
 */
"use strict";
(() => {
  const el = id => document.getElementById(id);
  const text = (id, value) => { if (el(id)) el(id).textContent = String(value ?? "—"); };
  const num = value => Number(value || 0).toLocaleString();
  const date = seconds => seconds && Number.isFinite(Number(seconds))
    ? new Date(Number(seconds) * 1000).toLocaleString() : "Not recorded";
  const short = value => {
    const input = String(value || "");
    try { const url = new URL(input); return url.hostname + url.pathname + url.search; }
    catch { return input || "Unknown source"; }
  };
  const section = (head, body) => {
    const block = document.createElement("div"); block.className = "detail-section";
    const h = document.createElement("h3"); h.textContent = head;
    const p = document.createElement("p"); p.textContent = String(body ?? "Not recorded");
    block.append(h,p); return block;
  };
  const state = { control:null, operations:null, live:null, csrf:null,
                  busy:false, offset:0, limit:15, query:"", status:"",
                  tasks:[], total:0, loading:false, lastError:"" };

  async function get(path) {
    const response = await window.suryadevRead(path);
    if (!response.ok) throw new Error("HTTP " + response.status);
    return response.json();
  }
  function statusMessage(message) { text("action-status",message); }
  function roleDescription() {
    const collector = el("learning-model").value === "collector";
    text("mode-explanation", collector
      ? "Collect approved sources without running Ollama. Extraction is evidence, not AI analysis or verified comprehension."
      : "Optional local Ollama inference consumes device RAM. Model analysis does not prove independent comprehension.");
  }
  function buttons() {
    const c=state.control || {};
    const managed=!!c.managed_running, external=!!c.external_worker_active;
    el("start-worker").disabled=state.busy || !c.can_start;
    el("stop-worker").disabled=state.busy || !managed;
    el("learning-model").disabled=state.busy || managed || external;
  }
  function renderControl(c) {
    state.control=c;
    const managed=!!c.managed_running, external=!!c.external_worker_active;
    const online=managed || external;
    const dot=el("worker-dot");
    dot.className="status-dot " + (managed ? "" : external ? "warn" : "idle");
    text("worker-state", managed ? "Worker active · dashboard-managed" :
          external ? "Worker active · separate process" : "Worker stopped");
    text("worker-message", managed
      ? "Worker PID " + String(c.managed_pid || "unknown") +
        (c.managed_model ? " · " + (c.managed_model==="collector"?"Collector only":"Local "+c.managed_model) : "")
      : external
        ? "A different worker owns this data folder. Follow its actual activity below; dashboard Stop cannot terminate it."
        : "Safe to start one worker for this workspace, if approved sources and capacity are available.");
    const tag=el("workspace-tag");
    tag.textContent = c.workspace_mode==="fresh" ? "FRESH WORKSPACE · MAX 3" : "EXISTING WORKSPACE";
    text("role-pill", managed && c.managed_model ? c.managed_model : (external ? "External worker" : "Ready"));
    text("core-status", c.core_dispatch?.ready===true
      ? "TLS configuration validated · live dispatch unverified" : "Not paired");
    const plan=c.plan_exists;
    const research=state.operations?.research_plan;
    text("plan-status", research?.present
      ? (research.valid ? "Approved plan loaded" : "Needs review") : plan ? "Plan file present" : "No plan");
    if (!online && c.preferred_model &&
        Array.from(el("learning-model").options).some(option=>option.value===c.preferred_model)
        && el("learning-model").dataset.userChosen!=="true") {
      el("learning-model").value=c.preferred_model;
    }
    roleDescription();
    buttons();
  }
  function renderOperations(o) {
    state.operations=o;
    const cap=o.capacity || {}, hw=o.hardware || {}, worker=o.worker || {};
    const active=Number(o.running_total||0)+Number(o.concurrent_books?.active||0)
      +Number(o.concurrent_videos?.active||0);
    text("stat-active",num(active));
    text("stat-admitted",o.worker_running
      ? num(cap.max_total)+" safe admission slots · 3 total max" : "Worker offline · no admitted jobs");
    text("stat-queued",num(o.queued_total));
    text("last-updated",new Date().toLocaleTimeString());
    const queue=Number(o.queued_total||0), running=active>0;
    const workerLive=!!o.worker_running;
    const next=worker.next_check_at;
    text("next-check",workerLive ? date(next) : "Worker offline");
    const why = cap.reason || hw.potential_reason || "No scheduler reason recorded";
    if (running) {
      text("activity-state","Processing "+num(active)+" assignment"+(active===1?"":"s"));
      text("activity-message","Evidence capture is in progress. Source coverage remains independently unverified.");
    } else if (queue && !workerLive) {
      text("activity-state","Work queued · worker offline");
      text("activity-message",num(queue)+" source(s) are waiting. Start an available worker to resume.");
    } else if (queue && cap.safe===false) {
      text("activity-state","Queued work · capacity paused");
      text("activity-message",why+". The 85% admission guard takes priority.");
    } else if (queue) {
      text("activity-state","Queued work · awaiting admission");
      text("activity-message",why+". Next worker poll: "+date(next));
    } else {
      text("activity-state",workerLive?"Worker idle · no queued source":"No active learning worker");
      text("activity-message",workerLive
        ? "No tasks are scheduled. Confirm that an approved source plan exists; source discovery may not yield new tasks."
        : "The dashboard can show saved evidence without starting a worker.");
    }
    renderMini("current-jobs",o.current||[],"No source assignments currently processing.");
    renderMini("upcoming-jobs",o.upcoming||[],"No queued source assignments.");
    const names=[["website","lane-web","lane-web-detail"],["youtube","lane-youtube","lane-youtube-detail"],["pdf","lane-pdf","lane-pdf-detail"]];
    for(const [kind,countId,detailId] of names) {
      const summary=o.by_source?.[kind] || {};
      const total=Number(summary.queued||0)+Number(summary.running||0)+Number(summary.done||0)+Number(summary.failed||0);
      text(countId,num(total));text(detailId,num(summary.running)+" active · "+num(summary.done)+" done · "+num(summary.failed)+" failed");
    }
    const books=o.book_learning || {};
    text("lane-books",num(books.indexed||0));
    text("lane-books-detail",num(books.lines_processed||0)+" / "+num(books.lines_total||0)+" lines indexed/read");
    const yt=cap.youtube_access || {};
    const banner=el("audit-banner");
    if (yt.state==="rate_limited") {
      banner.className="notice warning";
      banner.textContent="YouTube captions rate-limited (HTTP 429). New requests paused until "+
        date(yt.cooldown_until)+". Failed assignments are not automatically retried.";
    } else {
      banner.className="notice";
      banner.textContent="Source extraction is evidence, not understanding. Closed-book verification and RISHI exams are not established by worker completion.";
    }
    const metrics=[["CPU", hw.cpu_percent],["Memory",hw.ram_percent],["Storage",hw.disk_percent],
                   ["GPU",hw.gpu?.available===true?hw.gpu.usage_percent:null]];
    const grid=el("health-grid");grid.replaceChildren();
    for (const [name, value] of metrics) {
      const v=value===null||value===undefined||!Number.isFinite(Number(value))
        ? null : Math.max(0,Math.min(100,Number(value)));
      const card=document.createElement("div");card.className="health";
      const head=document.createElement("div");head.className="health-head";
      const label=document.createElement("span");label.textContent=name;
      const bold=document.createElement("strong");bold.textContent=v===null?"Unavailable":v.toFixed(1)+"%";
      head.append(label,bold);
      const meter=document.createElement("div");meter.className="meter";
      const fill=document.createElement("div");fill.className="meter-fill"+(v!==null&&v>=85?" warning":"");
      fill.style.width=(v===null?0:v)+"%";
      meter.append(fill);card.append(head,meter);grid.append(card);
    }
    text("capacity-reason",workerLive
      ? "Scheduler admission: "+why+". This device may run fewer than three jobs; other nodes are scheduled independently."
      : "Worker is not reporting active scheduling. Device measurements alone do not mean any jobs are running.");
    if(state.control)renderControl(state.control);
  }
  function renderMini(id, jobs, message) {
    const root=el(id);root.replaceChildren();
    if(!jobs.length){const p=document.createElement("p");p.className="empty";p.textContent=message;root.append(p);return;}
    for(const item of jobs.slice(0,5)){
      const line=document.createElement("div");line.className="job-mini";
      const icon=document.createElement("span");icon.textContent=({youtube:"▶",website:"◎",pdf:"▤"})[item.kind]||"◇";
      const info=document.createElement("div");
      const h=document.createElement("strong");h.textContent="#"+item.id+" · "+String(item.kind||"source").toUpperCase();
      const details=document.createElement("small");details.textContent=short(item.url);
      info.append(h,details);line.append(icon,info);root.append(line);
    }
  }
  function renderLive(d) {
    state.live=d;
    text("stat-done",num(d.status?.done));
    text("stat-failed",num(d.status?.failed));
    if(!state.operations){text("stat-queued",num(d.status?.queued));text("stat-active",num(d.status?.running));}
  }
  async function refresh() {
    if (state.loading) return;
    state.loading=true;
    try {
      const [control,ops,live]=await Promise.all([
        get("/api/learning/control"),get("/api/operations"),get("/api/live")]);
      renderLive(live);
      renderOperations(ops);
      renderControl(control);
      text("connection","Local service online");
      el("connection-dot").classList.remove("off");
      if(state.lastError){state.lastError="";statusMessage("Connection restored.");}
    } catch(err) {
      el("connection-dot").classList.add("off");
      text("connection","Local service unavailable");
      text("worker-state","Connection interrupted");
      el("worker-dot").className="status-dot off";
      text("worker-message","Last recorded activity may be stale. "+String(err.message||err));
      state.lastError=String(err.message||err);
      // A disconnected or outdated control endpoint must not allow mutation.
      state.control=null;buttons();
    } finally {state.loading=false;}
  }
  async function mutate(path, payload) {
    state.busy=true;buttons();
    try {
      if(!state.csrf){
        const settings=await get("/api/operator/settings");
        state.csrf=settings.csrf_token;
        if(!state.csrf)throw Error("Missing local authorization token");
      }
      const response=await fetch(path,{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json","X-SURYADEV-CSRF":state.csrf},
        body:JSON.stringify(payload)});
      const answer=await response.json();
      if(!response.ok)throw Error(answer.error||"HTTP "+response.status);
      statusMessage(answer.note || answer.status || "Operation accepted; checking actual worker state.");
    } catch (err) {
      statusMessage("Action failed: "+String(err.message||err));
    } finally {
      state.busy=false;
      await refresh();
      buttons();
    }
  }
  function taskRecord(job) {
    const button=document.createElement("button");button.type="button";
    button.className="record";button.setAttribute("aria-label","Inspect source #"+job.id+", "+job.status);
    const icon=document.createElement("span");icon.className="record-icon";
    icon.textContent=({youtube:"▶",website:"◎",pdf:"▤"})[job.kind]||"◇";
    const info=document.createElement("div");
    const title=document.createElement("strong");title.className="record-name";
    title.textContent=job.title || short(job.url);
    const sub=document.createElement("small");sub.className="record-sub";
    sub.textContent="#"+job.id+" · "+String(job.kind||"other").toUpperCase()+" · "+date(job.created);
    info.append(title,sub);
    const stage=document.createElement("span");stage.className="stage "+String(job.status||"");
    stage.textContent=job.status==="done"?"Worker done":job.status||"unknown";
    button.append(icon,info,stage);
    button.addEventListener("click",()=>showDetail(job.id));
    return button;
  }
  async function loadTasks() {
    const query=new URLSearchParams({offset:String(state.offset),limit:String(state.limit),
                                    status:state.status,q:state.query});
    try {
      const d=await get("/api/tasks?"+query);
      state.tasks=d.tasks||[];state.total=Number(d.total||0);
      text("jobs-count",num(state.total)+" assignments");
      const list=el("job-list");list.replaceChildren();
      if(!state.tasks.length){const empty=document.createElement("p");empty.className="empty";
        empty.textContent=state.query||state.status
          ? "No matching assignments. Clear filters to see all evidence."
          : "No assignments in this workspace. No work has been fabricated.";
        list.append(empty);
      } else for (const item of state.tasks)list.append(taskRecord(item));
      const count=Math.min(state.total,state.offset+state.tasks.length);
      text("page-label",state.total?num(state.offset+1)+"–"+num(count)+" of "+num(state.total):"0 of 0");
      el("prev-jobs").disabled=state.offset===0;
      el("next-jobs").disabled=state.offset+state.limit>=state.total;
    } catch (err) {
      text("jobs-count","Unable to load");
      const list=el("job-list");list.replaceChildren();
      const p=document.createElement("p");p.className="empty";p.textContent="Cannot load assignments: "+String(err.message||err);list.append(p);
    }
  }
  async function showDetail(id) {
    const dialog=el("job-dialog"),dest=el("job-detail");
    dest.replaceChildren();
    const loading=document.createElement("p");loading.textContent="Reading original task and evidence receipts…";dest.append(loading);
    dialog.showModal();
    try {
      const d=await get("/api/tasks/"+encodeURIComponent(String(id)));
      text("detail-title","Assignment #"+d.id);
      dest.replaceChildren(
        section("Source",d.url),
        section("Status",String(d.kind||"source").toUpperCase()+" · "+String(d.status||"unknown")),
        section("Acquisition/evidence",d.evidence_state||"Not verified"),
        section("Finding",d.summary||"No saved finding yet."),
        section("Error",d.error||"No error recorded."),
        section("Coverage receipt",d.coverage && Object.keys(d.coverage).length ? JSON.stringify(d.coverage,null,2) : "No verified coverage receipt"),
        section("Independent comprehension","Not verified by this console. Worker completion alone cannot pass a RISHI exam.")
      );
      if(d.steps && Array.isArray(d.steps)){
        for(const step of d.steps)dest.append(section(step.name||"Processing step",
          String(step.state||"unverified")+" · "+String(step.detail||"")));
      }
    }catch(err){dest.replaceChildren(section("Detail unavailable",String(err.message||err)));}
  }
  function init() {
    text("clock",new Date().toLocaleTimeString());
    el("learning-model").addEventListener("change",()=>{el("learning-model").dataset.userChosen="true";roleDescription();});
    el("start-worker").addEventListener("click",()=>mutate("/api/operator/learning/start",
                                                          {model:el("learning-model").value}));
    el("stop-worker").addEventListener("click",()=>mutate("/api/operator/learning/stop",{}));
    el("refresh-jobs").addEventListener("click",loadTasks);
    el("prev-jobs").addEventListener("click",()=>{state.offset=Math.max(0,state.offset-state.limit);loadTasks();});
    el("next-jobs").addEventListener("click",()=>{if(state.offset+state.limit<state.total){state.offset+=state.limit;loadTasks();}});
    el("job-filter").addEventListener("change",event=>{state.status=event.target.value;state.offset=0;loadTasks();});
    let searchDelay;
    el("job-search").addEventListener("input",event=>{
      clearTimeout(searchDelay);
      const q=event.target.value.trim();
      searchDelay=setTimeout(()=>{state.query=q;state.offset=0;loadTasks();},350);
    });
    el("close-detail").addEventListener("click",()=>el("job-dialog").close());
    const links=Array.from(document.querySelectorAll('.sidebar nav a[href^="#"]'));
    function nav() {for(const link of links)link.classList.toggle("active",link.hash===(location.hash||"#overview"));}
    window.addEventListener("hashchange",nav);nav();
    roleDescription();
    refresh();
    loadTasks();
    setInterval(()=>text("clock",new Date().toLocaleTimeString()),1000);
    setInterval(refresh,5000);
    setInterval(loadTasks,5000);
  }
  document.addEventListener("DOMContentLoaded",init);
})();