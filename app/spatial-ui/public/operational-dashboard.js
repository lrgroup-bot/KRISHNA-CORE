/* KRISHNA Spatial Command OS — owner-facing operational overlay.
 * Read-only presentation layer. It never grants authority, executes actions,
 * promotes code, or bypasses Sudarshan. Live actions remain in existing KRISHNA paths.
 */
(() => {
'use strict';

const SYSTEMS = {
  krishna:{name:'KRISHNA',mark:'KR',role:'Main intelligence. Understands your command, coordinates the other systems and returns the final answer.',view:'home',api:'/api/dashboard'},
  brahma:{name:'BRAHMA',mark:'BR',role:'Quality control. Checks whether work, evidence and learning are trustworthy before KRISHNA treats them as complete.',view:'workingGods',api:'/api/brahma/status'},
  sudarshan:{name:'Sudarshan',mark:'SU',role:'Authority and execution gate. Checks permission, approval and policy before anything changes the system or outside world.',view:'sudarshan',api:'/api/sudarshan/runtime'},
  hawkeye:{name:'HAWKEYE',mark:'HW',role:'Mobile and field eyes. Handles camera, sensor, diagnostic and field evidence without treating observation as proven fact.',view:'system',api:'/api/hawkeye/status'},
  kabach:{name:'KABACH',mark:'KB',role:'Security and privacy boundary. Protects projects, secrets and allowed access around KRISHNA.',view:'kabach',api:'/api/kabach/projects'},
  garuda:{name:'Garuda',mark:'GA',role:'Research scout. Collects public evidence and sources; KRISHNA still decides what the evidence means.',view:'garuda',api:'/api/garuda/status'},
  garudanetra:{name:'Garudanetra',mark:'GN',role:'Private browser eye. Opens and inspects real webpages and records browser evidence under KRISHNA controls.',view:'garudanetra',api:'/api/garudanetra/sessions'},
  narad:{name:'NARAD',mark:'NA',role:'Workflow and connected-provider coordinator. External actions remain permission and approval gated.',view:'narad',api:'/api/narad/status'},
  brahmagyan:{name:'BRAHMAGYAN',mark:'BG',role:'Deep-learning and Rishi research coordinator. Moves findings through evidence, cross-checking and maturity before trusted storage.',view:'brahmagyan',api:'/api/brahmagyan/status'},
  gyan:{name:'Gyan-Bhandar',mark:'GB',role:'Evidence-backed knowledge store. Keeps working, episodic, semantic, graph, skill and evidence memory separated.',view:'gyan',api:'/api/gyan-bhandar/inventory?project=KRISHNA'},
  rishi:{name:'Rishi Council',mark:'RI',role:'Domain specialists used for deep questions and independent review. Specialists advise; they do not become action authority.',view:'brahmagyan',api:'/api/brahmagyan/council'},
  amcc:{name:'aMCC',mark:'AM',role:'Adaptive effort controller. Chooses how much reasoning, checking and persistence a task needs; it never grants permission.',view:'system',api:'/api/amcc/status?limit=50'},
  suryadev:{name:'Suryadev',mark:'SY',role:'Screen and audio learning worker. Captures structured learning from approved video, audio, OCR and ASR tasks.',view:'workingGods',api:'/api/suryadev/status'},
  chandradev:{name:'Chandradev',mark:'CH',role:'Independent visual QC. Watches screen/camera evidence, cross-checks results and can require a QC debate before release.',view:'workingGods',api:'/api/chandradev/status'},
  mrityunjaya:{name:'Mrityunjaya',mark:'MR',role:'Self-heal and recovery worker. Diagnoses, prepares a candidate repair, tests it and rolls back when proof fails.',view:'workingGods',api:'/api/mrityunjay/status'},
  ui_guardian:{name:'UI Guardian',mark:'UI',role:'Frontend verifier. Checks interaction, responsive layout, accessibility and visual regression before UI promotion.',view:'uiGuardian',api:'/api/ui-guardian/registry'},
  developer:{name:'Developer',mark:'DV',role:'Bounded engineering worker. Creates candidate code and tests; successful editing alone never means completion.',view:'development',api:'/api/software-factory/workers/status'},
  specialists:{name:'Specialists',mark:'SP',role:'Narrow expert workers selected for a task. Their output is reviewed before KRISHNA can use it.',view:'specialists',api:'/api/specialists'},
  perfection:{name:'Project Perfection',mark:'PP',role:'Release proof pipeline. Requires evidence, tests, browser verification and safe promotion instead of assuming a change works.',view:'work',api:'/api/project-perfection/status'},
  vishvakarma:{name:'Vishvakarma',mark:'VI',role:'Engineering and repair specialist for evidence-led diagnosis, repair guidance and verified engineering learning.',view:'specialists',api:'/api/design/status'}
};

let selectedId = null;
let snapshot = null;
let detailData = null;
let miniObserver = null;

const byId = id => document.getElementById(id);
const text = value => String(value ?? '').trim();
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

function normalizedState(raw){
  const s=text(raw).toLowerCase();
  if(['working','running','active','handling','in_progress','in-progress','busy'].includes(s)) return 'working';
  if(['healing','recovering','repairing','rollback','rolling_back'].includes(s)) return 'healing';
  if(['waiting','queued','pending','waiting_approval','retest_required','awaiting_owner'].includes(s)) return 'waiting';
  if(['error','failed','failure','blocked','degraded','attention','debate_required','quarantined'].includes(s)) return 'attention';
  if(['done','completed','fixed','success','passed','verified','promoted'].includes(s)) return 'done';
  if(['idle','ready','landed','stopped',''].includes(s)) return 'ready';
  return 'unknown';
}
function stateLabel(state){
  return ({working:'WORKING',healing:'HEALING',waiting:'WAITING',attention:'BLOCKED',done:'DONE',ready:'IDLE',unknown:'UNKNOWN'})[state]||'UNKNOWN';
}
function lightClass(state){
  return ({working:'op-working',healing:'op-healing',waiting:'op-waiting',attention:'op-attention',done:'op-done',ready:'op-ready',unknown:'op-unknown'})[state]||'op-unknown';
}
function prettyTime(epoch){
  const n=Number(epoch||0);if(!n)return 'No recent timestamp';
  try{return new Date(n>1e12?n:n*1000).toLocaleString()}catch(_){return 'No recent timestamp'}
}
async function getJSON(path){
  const response=await fetch(path,{credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store'});
  let body={};try{body=await response.json()}catch(_){body={}}
  if(!response.ok)throw new Error(body.error||('HTTP '+response.status));
  return body;
}
function systemRow(id){
  return (snapshot?.gods||[]).find(row=>row.id===id)||{id,name:SYSTEMS[id]?.name||id,state:'idle',detail:'No live task reported.',updated_at:0};
}
function latestNotes(id,states=null){
  let rows=(snapshot?.notifications||[]).filter(row=>row.component===id);
  if(states){const wanted=new Set(states.map(value=>String(value).toLowerCase()));rows=rows.filter(row=>wanted.has(text(row.state).toLowerCase()))}
  return rows.slice(-6).reverse();
}
function safeJson(value){try{return JSON.stringify(value,null,2)}catch(_){return '{"status":"unavailable"}'}}
function explicitApproval(value){
  if(!value||typeof value!=='object')return false;
  if(Array.isArray(value))return value.some(explicitApproval);
  if(value.requires_approval===true||value.waiting_approval===true||value.approval_required===true)return true;
  return Object.entries(value).some(([key,item])=>{
    if(['payload','secret','token','password','key','raw'].includes(String(key).toLowerCase()))return false;
    if(typeof item==='string'&&/waiting[_ -]?approval|approval required|requires approval|awaiting owner/i.test(item))return true;
    return item&&typeof item==='object'&&explicitApproval(item);
  });
}
function realProgress(data){
  if(!data||typeof data!=='object')return null;
  for(const key of ['progress_percent','percent_complete','completion_percent']){
    const value=Number(data[key]);if(Number.isFinite(value)&&value>=0&&value<=100)return Math.round(value);
  }
  if(Object.prototype.hasOwnProperty.call(data,'progress')){
    const value=Number(data.progress);if(Number.isFinite(value)&&value>=0&&value<=1)return Math.round(value*100);
  }
  return null;
}
function currentWork(g,state){
  const detail=text(g.detail);
  if(state==='working')return detail&&detail.toLowerCase()!=='idle'?detail:'A task is active. Waiting for the next verified update.';
  if(state==='healing')return detail&&detail.toLowerCase()!=='idle'?detail:'Recovery work is active. Live promotion remains gated.';
  if(state==='attention')return detail&&detail.toLowerCase()!=='idle'?detail:'A blocking issue is recorded and needs verified handling.';
  if(state==='waiting')return detail&&detail.toLowerCase()!=='idle'?detail:'Waiting for evidence, queue turn or owner approval.';
  if(state==='done')return 'The last reported task finished. No new active task is reported.';
  return 'No active task is reported. This system is ready when KRISHNA needs it.';
}
function nextWork(state){
  if(state==='working')return 'Finish the current task, verify the result, then report the outcome to KRISHNA.';
  if(state==='healing')return 'Complete repair verification. Promote nothing until the recovery proof passes.';
  if(state==='attention')return 'Investigate the blocker and prove recovery before the result can be trusted.';
  if(state==='waiting')return 'Wait for the required evidence, queue turn or Partha approval. Do not bypass Sudarshan.';
  return 'Ready for KRISHNA to assign the next relevant task.';
}
function problemsText(id,state,data,error){
  if(error)return 'Live detail endpoint is unavailable. The shared KRISHNA snapshot is still shown.';
  if(id==='chandradev'&&Number(data?.open_debates||0)>0)return `${Number(data.open_debates)} visual QC debate(s) need resolution.`;
  if(data?.last_error)return String(data.last_error);
  if(data?.error)return String(data.error);
  if(state==='attention')return text(systemRow(id).detail)||'This system reports a blocker.';
  return 'No problem is currently reported.';
}
function healthSummary(id,state,data,error){
  if(error)return 'DETAIL UNAVAILABLE';
  if(state==='attention')return 'NEEDS ATTENTION';
  if(state==='healing')return 'RECOVERING';
  if(id==='chandradev'&&Number(data?.open_debates||0)>0)return 'QC DEBATE OPEN';
  if(data&&data.ready===false)return 'NOT READY';
  if(state==='working')return 'ACTIVE';
  return 'HEALTHY';
}
function usefulFacts(id,data){
  if(!data||typeof data!=='object')return [];
  const out=[];const add=(label,value)=>{if(value!==undefined&&value!==null&&value!=='')out.push([label,String(value)])};
  if(id==='hawkeye'){add('LIVE SESSIONS',data.live_sessions);add('SURVEYS',data.survey_count);add('SAVED EVIDENCE',data.mobile_evidence?.items)}
  else if(id==='chandradev'){add('QC RECORDS',data.qc_records);add('CAMERA CHECKS',data.camera_observations);add('OPEN DEBATES',data.open_debates)}
  else if(id==='suryadev'){add('STATUS',data.status||data.state||data.phase);add('NODES',Array.isArray(data.nodes?.nodes)?data.nodes.nodes.length:data.nodes?.count)}
  else if(id==='brahma'){add('STATUS',data.status||data.state||data.process_qc?.latest_state);add('OPEN ERRORS',Object.keys(data.process_qc?.open_errors||{}).length)}
  else if(id==='gyan'){add('MEMORY TYPES',Object.keys(data.kinds||{}).length)}
  else if(id==='garudanetra'){add('BROWSER SESSIONS',Array.isArray(data.sessions)?data.sessions.length:data.count)}
  else if(id==='ui_guardian'){add('REGISTERED UI',Array.isArray(data.entries)?data.entries.length:Array.isArray(data)?data.length:data.count)}
  else if(id==='perfection'){add('STATUS',data.status||data.state);add('RUNS',data.run_count||data.runs)}
  else if(id==='kabach'){add('PROTECTED PROJECTS',Array.isArray(data.projects)?data.projects.length:data.count)}
  else if(id==='brahmagyan'){add('MISSIONS',data.mission_count||data.missions);add('CURIOSITY QUEUED',data.curiosity_queued)}
  else if(id==='narad'){add('STATUS',data.status||data.state);add('DEAD LETTERS',data.dead_letters)}
  else if(id==='sudarshan'){add('AUTHORITY',data.authority);add('STATUS',data.status||data.state)}
  return out.slice(0,4);
}
function historyHtml(id){
  const rows=latestNotes(id);
  if(!rows.length)return '<div class="opEmpty">No recent activity has been recorded for this system.</div>';
  return rows.map(row=>`<div class="opHistoryRow"><i class="${lightClass(normalizedState(row.state))}"></i><div><strong>${escapeHtml(row.title||row.detail||'Activity')}</strong><small>${escapeHtml(prettyTime(row.created_at||row.updated_at))}</small></div></div>`).join('');
}
function doneHtml(id){
  const rows=latestNotes(id,['done','fixed','completed','verified','success']);
  if(!rows.length)return '<div class="opEmpty">No completed task is recorded in the recent live feed.</div>';
  return rows.slice(0,4).map(row=>`<div class="opDoneItem">✓ ${escapeHtml(row.title||row.detail||'Completed')}</div>`).join('');
}
function installDialog(){
  const dialog=byId('godDetailDialog');if(!dialog||dialog.dataset.operational==='2')return;
  dialog.dataset.operational='2';
  dialog.innerHTML=`<div class="godDetailInner opDashboard">
    <div class="opHead">
      <span id="godDetailLogo" class="opSystemMark">SYS</span>
      <div class="opIdentity"><div class="opEyebrow">KRISHNA SYSTEM</div><h2 id="godDetailName">System</h2><p id="godDetailRole"></p></div>
      <button class="opClose" type="button" aria-label="Close dashboard">×</button>
    </div>
    <div class="opStatusRow"><span id="opStateBadge" class="opBadge unknown"><i></i><span>UNKNOWN</span></span><span id="opHealthBadge" class="opBadge ready"><i></i><span>Checking health</span></span><span class="opReadOnly">OWNER VIEW · READ ONLY</span></div>
    <div class="opHeroGrid">
      <section class="opCard opCardRole"><h3>WHAT THIS SYSTEM DOES</h3><div id="opPurpose" class="opValue">Checking…</div></section>
      <section class="opCard opCardWork"><h3>WORKING NOW</h3><div id="opWorking" class="opValue">Checking…</div></section>
      <section class="opCard opCardProgress"><h3>PROGRESS</h3><div id="opProgressLabel" class="opBigValue">—</div><div id="opProgressWrap"><div class="opProgress"><i id="opProgressBar"></i></div><small id="opProgressText">No percentage reported</small></div></section>
    </div>
    <div id="opMeta" class="opMeta"></div>
    <div class="opGrid">
      <section class="opCard"><h3>COMPLETED RECENTLY</h3><div id="opDone" class="opDoneList">Checking…</div></section>
      <section class="opCard"><h3>PROBLEMS</h3><div id="opProblems" class="opValue">Checking…</div></section>
      <section class="opCard"><h3>NEEDS PARTHA</h3><div id="opApproval" class="opValue">Checking…</div><small>Mutating and external actions remain behind Sudarshan.</small></section>
      <section class="opCard"><h3>NEXT</h3><div id="opNext" class="opValue">Checking…</div></section>
    </div>
    <section class="opHistory"><div class="opSectionHead"><div><span>RECENT HISTORY</span><strong>What this system has actually reported</strong></div></div><div id="opHistoryRows"></div></section>
    <details class="opTechnical"><summary>Advanced / evidence</summary><pre id="opTechnicalJson">No detailed telemetry.</pre></details>
    <div class="opActions"><button id="opRefresh" type="button">Refresh</button><button id="godDetailOpen" class="primary" type="button">Open workspace</button></div>
  </div>`;
  dialog.querySelector('.opClose').onclick=()=>{dialog.close();document.querySelectorAll('.miniGodRow.op-selected').forEach(row=>row.classList.remove('op-selected'))};
  byId('opRefresh').onclick=()=>selectedId&&loadOperationalDetail(selectedId,true);
  byId('godDetailOpen').onclick=()=>openWorkspace(selectedId);
}
function renderMeta(g,id,data,state,error){
  const facts=usefulFacts(id,data);
  const meta=[['STATUS',stateLabel(state)],['HEALTH',healthSummary(id,state,data,error)],['LAST ACTIVITY',prettyTime(g.updated_at)],...facts];
  byId('opMeta').innerHTML=meta.slice(0,6).map(([key,value])=>`<div><span>${escapeHtml(key)}</span><b>${escapeHtml(value)}</b></div>`).join('');
}
function renderOperational(id,error=''){
  installDialog();
  const config=SYSTEMS[id]||{name:id,mark:'SY',role:'KRISHNA internal system.',view:'workingGods'};
  const row=systemRow(id);const state=normalizedState(row.state);
  byId('godDetailLogo').textContent=config.mark;byId('godDetailName').textContent=config.name;byId('godDetailRole').textContent=config.role;byId('opPurpose').textContent=config.role;
  const stateBadge=byId('opStateBadge');stateBadge.className='opBadge '+state;stateBadge.querySelector('span').textContent=stateLabel(state);
  const healthBadge=byId('opHealthBadge');const healthState=(state==='attention'||error)?'attention':state==='healing'?'healing':'ready';healthBadge.className='opBadge '+healthState;healthBadge.querySelector('span').textContent=healthSummary(id,state,detailData,error);
  byId('opWorking').textContent=currentWork(row,state);byId('opDone').innerHTML=doneHtml(id);byId('opProblems').textContent=problemsText(id,state,detailData,error);byId('opNext').textContent=nextWork(state);
  const needsApproval=explicitApproval(detailData)||/approval|partha/i.test(text(row.detail));
  byId('opApproval').textContent=needsApproval?'YES · Review the exact requested action in Sudarshan before anything changes.':'Nothing needs Partha right now.';
  const pct=realProgress(detailData);const label=byId('opProgressLabel');const bar=byId('opProgressBar');const progressText=byId('opProgressText');
  if(pct===null){label.textContent=state==='working'?'ACTIVE':state==='healing'?'RECOVERING':state==='attention'?'BLOCKED':state==='waiting'?'WAITING':state==='done'?'COMPLETE':'IDLE';bar.style.width='0%';progressText.textContent='No percentage reported by this system';}
  else{label.textContent=pct+'%';bar.style.width=pct+'%';progressText.textContent=pct+'% reported by this system';}
  renderMeta(row,id,detailData,state,error);byId('opHistoryRows').innerHTML=historyHtml(id);
  byId('opTechnicalJson').textContent=detailData?safeJson(detailData):(error?'Detailed telemetry unavailable: '+error:'No separate detailed telemetry endpoint is registered for this system. Activity is taken from the shared KRISHNA process snapshot.');
  byId('godDetailOpen').textContent=config.view==='home'?'Talk to KRISHNA':'Open '+config.name+' workspace';
}
async function refreshSnapshot(){
  try{snapshot=await getJSON('/api/working-gods')}catch(_){try{snapshot=await getJSON('/api/brahma/process-qc')}catch(__){snapshot=snapshot||{gods:[],notifications:[]}}}
  updateHomeDeck();decorateMiniButtons();return snapshot;
}
async function loadOperationalDetail(id,keepOpen=false){
  selectedId=id;detailData=null;await refreshSnapshot();renderOperational(id);
  document.querySelectorAll('.miniGodRow').forEach(row=>row.classList.toggle('op-selected',row.dataset.godId===id));
  const dialog=byId('godDetailDialog');if(dialog&&!dialog.open&&!keepOpen)dialog.showModal();
  const config=SYSTEMS[id];if(!config?.api)return;
  try{detailData=await getJSON(config.api);renderOperational(id)}catch(error){renderOperational(id,error.message)}
}
function openWorkspace(id){
  const config=SYSTEMS[id];if(!config)return;const dialog=byId('godDetailDialog');if(dialog?.open)dialog.close();
  document.querySelectorAll('.miniGodRow.op-selected').forEach(row=>row.classList.remove('op-selected'));
  if(typeof window.showView==='function')window.showView(config.view||'workingGods');
  if(config.view==='home'&&typeof window.toggleKrishnaPopup==='function')window.toggleKrishnaPopup(true);
}
function decorateMiniButtons(){
  const host=byId('workingGodsMini');if(!host)return;
  host.querySelectorAll('.miniGodRow').forEach(button=>{
    const id=button.dataset.godId;const config=SYSTEMS[id];if(!config)return;
    const row=systemRow(id);const state=normalizedState(row.state);const logo=button.querySelector('.miniGodLogo');const name=button.querySelector('.miniGodName');const stateEl=button.querySelector('.miniGodState');const light=button.querySelector('.godLight');
    if(logo)logo.textContent=config.mark;if(name)name.textContent=config.name;if(stateEl)stateEl.textContent=stateLabel(state);if(light)light.className='godLight '+lightClass(state);
    button.dataset.opState=state;button.title=config.name+' · '+stateLabel(state)+' · Open operational dashboard';button.setAttribute('aria-label','Open '+config.name+' operational dashboard');
  });
}
function simplifyComposer(){
  const tools=document.querySelector('.composerWrap .composeFoot .tools');if(tools){tools.querySelectorAll('button.tool').forEach(button=>button.dataset.opHidden='true')}
  const input=byId('input');if(input)input.placeholder='Tell KRISHNA what you want done…';
  const send=document.querySelector('.composerWrap .send');if(send){send.textContent='RUN';send.title='Send command to KRISHNA through Sudarshan';send.setAttribute('aria-label','Run command through Sudarshan')}
}
function fixLegend(){
  const head=document.querySelector('.systemOrbitHead');if(!head)return;const title=head.querySelector('span');if(title)title.textContent='KRISHNA SYSTEMS';
  const small=head.querySelector('small');if(small)small.innerHTML='<i class="orbitDot active"></i>working <i class="orbitDot idle"></i>idle <i class="opLegendBlue"></i>healing <i class="opLegendRed"></i>blocked';
}
function installHomeDeck(){
  const host=document.querySelector('#home .panelInner.projectHome');if(!host||byId('opHomeDeck'))return;
  const deck=document.createElement('section');deck.id='opHomeDeck';deck.className='opHomeDeck';deck.innerHTML=`<div class="opHomeIntro"><div><span class="opEyebrow">KRISHNA SPATIAL COMMAND OS</span><h2>One command. Verified execution.</h2><p>Tell KRISHNA what you want. Internal systems research, build, inspect, verify and recover behind Sudarshan.</p></div><div class="opCorePill"><i></i><span>CORE ONLINE</span></div></div><div class="opHomeStats"><div><span>WORKING</span><strong id="opCountWorking">0</strong></div><div><span>IDLE</span><strong id="opCountIdle">0</strong></div><div><span>HEALING</span><strong id="opCountHealing">0</strong></div><div><span>NEEDS ATTENTION</span><strong id="opCountAttention">0</strong></div></div><div class="opHomeHint">Select any system above to see what it does, what it is doing now, what finished, what is blocked and whether Partha is needed.</div>`;
  host.appendChild(deck);updateHomeDeck();
}
function updateHomeDeck(){
  if(!byId('opHomeDeck'))return;const counts={working:0,ready:0,done:0,healing:0,waiting:0,attention:0,unknown:0};
  Object.keys(SYSTEMS).forEach(id=>{const state=normalizedState(systemRow(id).state);counts[state]=(counts[state]||0)+1});
  byId('opCountWorking').textContent=String(counts.working);byId('opCountIdle').textContent=String(counts.ready+counts.done+counts.waiting);byId('opCountHealing').textContent=String(counts.healing);byId('opCountAttention').textContent=String(counts.attention);
}
function simplifyShell(){
  document.body.classList.add('krishnaSpatialCommandOS');
  const pageTitle=byId('pageTitle');if(pageTitle&&document.body.dataset.view==='home')pageTitle.textContent='Command Deck';
  const workingTitle=document.querySelector('#workingGods .panelTitle');if(workingTitle)workingTitle.textContent='KRISHNA Systems';
  const workingSub=document.querySelector('#workingGods .panelSub');if(workingSub)workingSub.textContent='Select a system to see its current task, progress, completed work, problems and whether Partha is needed.';
}
function install(){
  installDialog();simplifyComposer();fixLegend();simplifyShell();installHomeDeck();decorateMiniButtons();
  window.openGodDetail=id=>loadOperationalDetail(id,false);window.updateGodDetail=()=>{if(selectedId)renderOperational(selectedId)};
  const host=byId('workingGodsMini');if(host&&window.MutationObserver){miniObserver=new MutationObserver(()=>decorateMiniButtons());miniObserver.observe(host,{childList:true,subtree:true,characterData:true})}
  refreshSnapshot();
  window.KRISHNA_OPERATIONAL_UI={version:'2026.10-spatial-command-os-v1',systems:Object.keys(SYSTEMS),open:window.openGodDetail,refresh:refreshSnapshot};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
