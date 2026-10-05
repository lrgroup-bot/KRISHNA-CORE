/* KRISHNA operational dashboard overlay.
 * Read-only UI normalization. It does not grant authority, execute actions or bypass Sudarshan.
 */
(() => {
'use strict';

const SYSTEMS = {
  krishna:{name:'KRISHNA',mark:'KR',role:'Main intelligence. Understands your command, coordinates the other systems and returns the final answer.',view:'home',api:'/api/dashboard'},
  brahma:{name:'BRAHMA',mark:'BR',role:'Quality control. Watches errors, verification and recovery so failed work is not treated as complete.',view:'workingGods',api:'/api/brahma/status'},
  sudarshan:{name:'Sudarshan',mark:'SU',role:'Authority and execution gate. Checks permission, approval and policy before anything changes the system or outside world.',view:'sudarshan',api:'/api/sudarshan/runtime'},
  hawkeye:{name:'HAWKEYE',mark:'HW',role:'Mobile and field eyes. Handles camera, sensor, diagnostic and field evidence without pretending an observation is proven fact.',view:'system',api:'/api/hawkeye/status'},
  kabach:{name:'KABACH',mark:'KB',role:'Security and privacy boundary. Protects projects, secrets and allowed access around KRISHNA.',view:'kabach',api:'/api/kabach/projects'},
  garuda:{name:'Garuda',mark:'GA',role:'Research scout. Collects public evidence and sources; KRISHNA still decides what the evidence means.',view:'garuda',api:'/api/garuda/status'},
  garudanetra:{name:'Garudanetra',mark:'GN',role:'Private browser eye. Opens and inspects real webpages and records browser evidence under KRISHNA controls.',view:'garudanetra',api:'/api/garudanetra/sessions'},
  narad:{name:'NARAD',mark:'NA',role:'Workflow and connected-provider coordinator. External actions remain permission and approval gated.',view:'narad',api:'/api/narad/status'},
  brahmagyan:{name:'BRAHMAGYAN',mark:'BG',role:'Deep-learning and Rishi research coordinator. Moves findings through evidence, cross-checking and maturity before trusted storage.',view:'brahmagyan',api:'/api/brahmagyan/status'},
  gyan:{name:'Gyan-Bhandar',mark:'GB',role:'Evidence-backed knowledge store. Keeps working, episodic, semantic, graph, skill and evidence memory separated.',view:'gyan',api:'/api/gyan-bhandar/inventory?project=KRISHNA'},
  rishi:{name:'Rishi Council',mark:'RI',role:'Domain specialists used for deep questions and independent review. Specialists advise; they do not become action authority.',view:'brahmagyan',api:'/api/brahmagyan/council'},
  amcc:{name:'aMCC',mark:'AM',role:'Adaptive effort controller. Chooses how much reasoning, checking and persistence a task needs; it can never grant permission.',view:'system',api:null},
  suryadev:{name:'Suryadev',mark:'SY',role:'Screen and audio learning worker. Captures structured learning from approved video, audio, OCR and ASR tasks.',view:'workingGods',api:'/api/suryadev/status'},
  chandradev:{name:'Chandradev',mark:'CH',role:'Independent visual QC. Watches screen/camera evidence, cross-checks results and can require a QC debate before release.',view:'workingGods',api:'/api/chandradev/status'},
  mrityunjaya:{name:'Mrityunjaya',mark:'MR',role:'Self-heal and recovery worker. Diagnoses, prepares a candidate repair, tests it and rolls back when proof fails.',view:'workingGods',api:null},
  ui_guardian:{name:'UI Guardian',mark:'UI',role:'Frontend verifier. Checks interaction, responsive layout, accessibility and visual regression before UI promotion.',view:'uiGuardian',api:'/api/ui-guardian/registry'},
  developer:{name:'Developer',mark:'DV',role:'Bounded engineering worker. Creates candidate code and tests; successful editing alone never means completion.',view:'development',api:'/api/software-factory/workers/status'},
  specialists:{name:'Specialists',mark:'SP',role:'Narrow expert workers selected for a task. Their output is reviewed before KRISHNA can use it.',view:'specialists',api:null},
  perfection:{name:'Project Perfection',mark:'PP',role:'Release proof pipeline. Requires evidence, tests, browser verification and safe promotion instead of assuming a change works.',view:'work',api:'/api/project-perfection/status'},
  vishvakarma:{name:'Vishvakarma',mark:'VI',role:'Repair and engineering specialist for evidence-led diagnosis, repair guidance and verified engineering learning.',view:'specialists',api:'/api/design/status'}
};

let selectedId = null;
let snapshot = null;
let detailData = null;
let miniObserver = null;

const byId = id => document.getElementById(id);
const text = v => String(v ?? '').trim();
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

function normalizedState(raw){
  const s=text(raw).toLowerCase();
  if(['working','running','active','handling','in_progress','in-progress'].includes(s)) return 'working';
  if(['done','completed','fixed','success','passed','verified','promoted'].includes(s)) return 'done';
  if(['waiting','queued','pending','waiting_approval','retest_required'].includes(s)) return 'waiting';
  if(['error','failed','failure','blocked','degraded','attention','debate_required'].includes(s)) return 'attention';
  if(['idle','ready','landed','stopped',''].includes(s)) return 'ready';
  return 'unknown';
}
function stateLabel(s){return ({working:'WORKING',done:'DONE',waiting:'WAITING',attention:'ATTENTION',ready:'READY',unknown:'UNKNOWN'})[s]||'UNKNOWN'}
function lightClass(s){return ({working:'op-working',done:'op-working',waiting:'op-waiting',attention:'op-attention',ready:'op-ready',unknown:'op-unknown'})[s]||'op-unknown'}
function prettyTime(epoch){
  const n=Number(epoch||0); if(!n) return 'Not reported';
  try{return new Date(n>1e12?n:n*1000).toLocaleString()}catch(_){return 'Not reported'}
}
async function getJSON(path){
  const response=await fetch(path,{credentials:'same-origin',headers:{'Accept':'application/json'},cache:'no-store'});
  let body={}; try{body=await response.json()}catch(_){body={}}
  if(!response.ok) throw new Error(body.error||('HTTP '+response.status));
  return body;
}
function systemRow(id){return (snapshot?.gods||[]).find(x=>x.id===id)||{id,name:SYSTEMS[id]?.name||id,state:'idle',detail:'No live task reported.',updated_at:0}}
function latestNotes(id,states){
  const wanted=new Set(states.map(x=>x.toLowerCase()));
  return (snapshot?.notifications||[]).filter(n=>n.component===id&&wanted.has(text(n.state).toLowerCase())).slice(-4).reverse();
}
function safeJson(value){try{return JSON.stringify(value,null,2)}catch(_){return '{"status":"unavailable"}'}}
function currentWork(g,s){
  const d=text(g.detail);
  if(s==='working') return d&&d.toLowerCase()!=='idle'?d:'A task is active. KRISHNA is waiting for the next verified update.';
  if(s==='attention') return d&&d.toLowerCase()!=='idle'?d:'An issue is recorded and needs verified handling.';
  if(s==='waiting') return d&&d.toLowerCase()!=='idle'?d:'Waiting for queued work, evidence or approval.';
  if(s==='done') return 'The last reported task finished. No new active task is reported.';
  return 'No active task is reported. This system is ready when KRISHNA needs it.';
}
function nextWork(s){
  if(s==='working') return 'Finish the current task, verify the result, then report the outcome to KRISHNA.';
  if(s==='attention') return 'Investigate the recorded issue and prove the recovery before the result can be trusted.';
  if(s==='waiting') return 'Wait for the required evidence, queue turn or owner approval. Do not bypass Sudarshan.';
  return 'Ready for KRISHNA to assign the next relevant task.';
}
function explicitApproval(value){
  if(!value||typeof value!=='object') return false;
  if(value.requires_approval===true||value.waiting_approval===true||value.approval_required===true) return true;
  if(Array.isArray(value)) return value.some(explicitApproval);
  return Object.entries(value).some(([k,v])=>{
    if(['payload','secret','token','password','key','raw'].includes(String(k).toLowerCase())) return false;
    if(typeof v==='string'&&/waiting[_ -]?approval|approval required|requires approval/i.test(v)) return true;
    return v&&typeof v==='object'&&explicitApproval(v);
  });
}
function realProgress(data){
  if(!data||typeof data!=='object') return null;
  for(const key of ['progress_percent','percent_complete','completion_percent']){
    const v=Number(data[key]); if(Number.isFinite(v)&&v>=0&&v<=100) return Math.round(v);
  }
  if(Object.prototype.hasOwnProperty.call(data,'progress')){
    const v=Number(data.progress); if(Number.isFinite(v)&&v>=0&&v<=1) return Math.round(v*100);
  }
  return null;
}
function healthSummary(id,g,s,data,error){
  if(error) return 'Live detail unavailable · snapshot retained';
  if(s==='attention') return 'Needs attention';
  if(id==='chandradev'&&Number(data?.open_debates||0)>0) return Number(data.open_debates)+' open QC debate(s)';
  if(data&&data.ready===false) return 'Not ready';
  if(s==='working') return 'Active';
  return 'Ready';
}
function usefulFacts(id,data){
  if(!data||typeof data!=='object') return [];
  const out=[];
  const add=(label,value)=>{if(value!==undefined&&value!==null&&value!=='')out.push([label,String(value)])};
  if(id==='hawkeye'){
    add('LIVE SESSIONS',data.live_sessions);add('SURVEYS',data.survey_count);add('SAVED EVIDENCE',data.mobile_evidence?.items);
  } else if(id==='chandradev'){
    add('QC RECORDS',data.qc_records);add('CAMERA CHECKS',data.camera_observations);add('OPEN DEBATES',data.open_debates);
  } else if(id==='suryadev'){
    add('STATUS',data.status||data.state||data.phase);add('NODES',Array.isArray(data.nodes?.nodes)?data.nodes.nodes.length:data.nodes?.count);
  } else if(id==='brahma'){
    add('STATUS',data.status||data.state||data.process_qc?.latest_state);add('OPEN ERRORS',Object.keys(data.process_qc?.open_errors||{}).length);
  } else if(id==='gyan'){
    add('MEMORY TYPES',Object.keys(data.kinds||{}).length);
  } else if(id==='garudanetra'){
    add('BROWSER SESSIONS',Array.isArray(data.sessions)?data.sessions.length:data.count);
  } else if(id==='ui_guardian'){
    add('REGISTERED UI',Array.isArray(data.entries)?data.entries.length:Array.isArray(data)?data.length:data.count);
  } else if(id==='perfection'){
    add('STATUS',data.status||data.state);add('RUNS',data.run_count||data.runs);
  } else if(id==='kabach'){
    add('PROTECTED PROJECTS',Array.isArray(data.projects)?data.projects.length:data.count);
  } else if(id==='brahmagyan'){
    add('MISSIONS',data.mission_count||data.missions);add('CURIOSITY QUEUED',data.curiosity_queued);
  } else if(id==='narad'){
    add('STATUS',data.status||data.state);add('DEAD LETTERS',data.dead_letters);
  }
  return out.slice(0,3);
}
function doneHtml(id){
  const notes=latestNotes(id,['done','fixed','completed']);
  if(!notes.length) return '<div class="opValue">No completed task is recorded in the recent live QC feed.</div>';
  return '<div class="opDoneList">'+notes.map(n=>'<div class="opDoneItem">'+escapeHtml(n.title||n.detail||'Completed')+'</div>').join('')+'</div>';
}
function installDialog(){
  const dialog=byId('godDetailDialog'); if(!dialog||dialog.dataset.operational==='1') return;
  dialog.dataset.operational='1';
  dialog.innerHTML=`<div class="godDetailInner">
    <div class="opHead"><span id="godDetailLogo">SYS</span><div class="opIdentity"><h2 id="godDetailName">System</h2><p id="godDetailRole"></p></div><button class="opClose" type="button" aria-label="Close">×</button></div>
    <div class="opStatusRow"><span id="opStateBadge" class="opBadge unknown"><i></i><span>UNKNOWN</span></span><span id="opHealthBadge" class="opBadge ready"><i></i><span>Checking health</span></span></div>
    <div class="opGrid">
      <section class="opCard"><h3>WORKING NOW</h3><div id="opWorking" class="opValue">Checking…</div><div id="opProgressWrap" hidden><div class="opProgress"><i id="opProgressBar"></i></div><small id="opProgressText"></small></div></section>
      <section class="opCard"><h3>DONE</h3><div id="opDone" class="opValue">Checking…</div></section>
      <section class="opCard"><h3>NEXT</h3><div id="opNext" class="opValue">Checking…</div></section>
      <section class="opCard"><h3>OWNER APPROVAL</h3><div id="opApproval" class="opValue">Checking…</div><small>No system may bypass Sudarshan for a mutating or external action.</small></section>
    </div>
    <div id="opMeta" class="opMeta"></div>
    <details class="opTechnical"><summary>Technical details (only when needed)</summary><pre id="opTechnicalJson">No detailed telemetry.</pre></details>
    <div class="opActions"><button id="opRefresh" type="button">Refresh</button><button id="godDetailOpen" class="primary" type="button">Open workspace</button></div>
  </div>`;
  dialog.querySelector('.opClose').onclick=()=>dialog.close();
  byId('opRefresh').onclick=()=>selectedId&&loadOperationalDetail(selectedId,true);
  byId('godDetailOpen').onclick=()=>openWorkspace(selectedId);
}
function renderMeta(g,id,data){
  const facts=usefulFacts(id,data);
  const meta=[['LAST ACTIVITY',prettyTime(g.updated_at)],['SOURCE','Live KRISHNA telemetry'],...facts];
  byId('opMeta').innerHTML=meta.slice(0,4).map(([k,v])=>'<div><span>'+escapeHtml(k)+'</span><b>'+escapeHtml(v)+'</b></div>').join('');
}
function renderOperational(id,error=''){
  installDialog();
  const c=SYSTEMS[id]||{name:id,mark:'SY',role:'KRISHNA internal system.',view:'workingGods'};
  const g=systemRow(id); const s=normalizedState(g.state);
  byId('godDetailLogo').textContent=c.mark; byId('godDetailName').textContent=c.name; byId('godDetailRole').textContent=c.role;
  const stateBadge=byId('opStateBadge'); stateBadge.className='opBadge '+s; stateBadge.querySelector('span').textContent=stateLabel(s);
  const health=healthSummary(id,g,s,detailData,error); const healthBadge=byId('opHealthBadge');
  const healthState=(s==='attention'||error)?'attention':'ready'; healthBadge.className='opBadge '+healthState;healthBadge.querySelector('span').textContent=health;
  byId('opWorking').textContent=currentWork(g,s); byId('opDone').innerHTML=doneHtml(id); byId('opNext').textContent=nextWork(s);
  byId('opApproval').textContent=explicitApproval(detailData)||/approval/i.test(text(g.detail))?'Approval request detected · review exact action in Sudarshan.':'No owner approval request is currently reported.';
  const pct=realProgress(detailData); const wrap=byId('opProgressWrap');wrap.hidden=pct===null;
  if(pct!==null){byId('opProgressBar').style.width=pct+'%';byId('opProgressText').textContent=pct+'% reported by this system';}
  renderMeta(g,id,detailData);
  byId('opTechnicalJson').textContent=detailData?safeJson(detailData):(error?'Detailed telemetry unavailable: '+error:'No separate detailed telemetry endpoint for this system yet. The live process-QC snapshot above remains authoritative for activity.');
  byId('godDetailOpen').textContent=c.view==='home'?'Talk to KRISHNA':'Open '+c.name+' workspace';
}
async function refreshSnapshot(){
  try{snapshot=await getJSON('/api/working-gods');return snapshot}catch(_){return snapshot}
}
async function loadOperationalDetail(id,keepOpen=false){
  selectedId=id; detailData=null;
  await refreshSnapshot(); renderOperational(id);
  const dialog=byId('godDetailDialog'); if(dialog&&!dialog.open&&!keepOpen) dialog.showModal();
  const c=SYSTEMS[id]; if(!c?.api) return;
  try{detailData=await getJSON(c.api);renderOperational(id)}catch(e){renderOperational(id,e.message)}
}
function openWorkspace(id){
  const c=SYSTEMS[id]; if(!c)return; const dialog=byId('godDetailDialog');if(dialog?.open)dialog.close();
  if(typeof window.showView==='function') window.showView(c.view||'workingGods');
  if(c.view==='home'&&typeof window.toggleKrishnaPopup==='function') window.toggleKrishnaPopup(true);
}
function decorateMiniButtons(){
  const host=byId('workingGodsMini');if(!host)return;
  host.querySelectorAll('.miniGodRow').forEach(btn=>{
    const id=btn.dataset.godId;const c=SYSTEMS[id];if(!c)return;
    const stateEl=btn.querySelector('.miniGodState');const s=normalizedState(stateEl?.textContent);
    const logo=btn.querySelector('.miniGodLogo');const name=btn.querySelector('.miniGodName');const light=btn.querySelector('.godLight');
    if(logo&&logo.textContent!==c.mark)logo.textContent=c.mark;if(name&&name.textContent!==c.name)name.textContent=c.name;
    if(light){light.className='godLight '+lightClass(s)}
    btn.title=c.name+' · '+stateLabel(s)+' · Click for a simple operational dashboard';btn.setAttribute('aria-label','Open '+c.name+' operational dashboard');
  });
}
function simplifyComposer(){
  const tools=document.querySelector('.composerWrap .composeFoot .tools'); if(!tools)return;
  tools.querySelectorAll('button.tool').forEach(button=>{
    const label=text(button.textContent).toLowerCase();
    if(label.includes('file')||label.includes('plugin')||label.includes('project')||label.includes('investigate')||label.includes('research')) button.dataset.opHidden='true';
  });
  const input=byId('input');if(input)input.placeholder='Tell KRISHNA what you want done…';
  const send=document.querySelector('.composerWrap .send');if(send){send.textContent='RUN';send.title='Send command to KRISHNA through Sudarshan';send.setAttribute('aria-label','Run command through Sudarshan')}
}
function fixLegend(){
  const head=document.querySelector('.systemOrbitHead');if(!head)return;
  const title=head.querySelector('span');if(title)title.textContent='KRISHNA SYSTEMS';
  const small=head.querySelector('small');if(small)small.innerHTML='<i class="orbitDot active"></i>working <i class="orbitDot idle"></i>ready <i class="godLight op-attention"></i>attention';
}
function install(){
  installDialog();simplifyComposer();fixLegend();decorateMiniButtons();
  window.openGodDetail=id=>loadOperationalDetail(id,false);
  window.updateGodDetail=()=>{if(selectedId)renderOperational(selectedId)};
  const host=byId('workingGodsMini');
  if(host&&window.MutationObserver){miniObserver=new MutationObserver(()=>decorateMiniButtons());miniObserver.observe(host,{childList:true,subtree:true,characterData:true})}
  refreshSnapshot().then(()=>decorateMiniButtons());
  window.KRISHNA_OPERATIONAL_UI={version:'2026.10-owner-readable-v1',systems:Object.keys(SYSTEMS),open:window.openGodDetail,refresh:refreshSnapshot};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
