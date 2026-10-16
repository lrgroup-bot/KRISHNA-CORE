(() => {
  if (window.__KRISHNA_BRAHMAND_MAIN__) return;
  window.__KRISHNA_BRAHMAND_MAIN__ = true;
  const DATA = window.KRISHNA_BRAHMAND_DATA;
  if (!DATA) return;

  const $ = (id) => document.getElementById(id);
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const text = (v, fallback = '—') => v === undefined || v === null || v === '' ? fallback : String(v);
  const toJson = (v) => { try { return JSON.stringify(v, null, 2); } catch { return String(v); } };
  const ACTIVE = new Set(['running','working','executing','verifying','in_progress','healing']);
  const WAITING = new Set(['blocked','waiting_approval','awaiting_approval','waiting_dependency','paused']);
  const FAILED = new Set(['failed','error','rejected']);
  const BLOCKED = new Set([...WAITING,...FAILED]);
  const DONE = new Set(['verified','done','completed','complete','passed']);
  const NORMAL = window.KRISHNA_BRAHMAND_NORMALIZE;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = { tasks:[], status:{}, mobile:{}, qc:{}, health:new Map(), latency:new Map(), snapshot:new Map(), received:new Map(), errors:new Map(), group:'root', selected:'krishna', history:[], refreshed:0, lastDeepRefresh:0, busy:false };

  function statusOf(task){ return NORMAL.status(task); }
  function ownerOf(task){ return NORMAL.owners(task).join(' '); }
  function field(obj,names){ for(const name of names){ const v=obj?.[name] ?? obj?.detail?.[name]; if(v!==undefined&&v!==null&&v!=='') return v; } return null; }
  function node(id){ return DATA.nodes[id]; }
  function children(def){ return Array.isArray(def?.children) ? def.children : []; }
  function tasksFor(def){ return NORMAL.tasksFor(def?.id, state.tasks); }
  function seconds(value){ const n=Number(value); return Number.isFinite(n) && n>0 ? (n>1e12?n:n*1000) : Date.parse(value); }
  function updated(task){ return seconds(field(task,['updated_at','updated','timestamp','last_update','created_at'])) || 0; }
  function fresh(id){ return state.received.has(id) && Date.now()-state.received.get(id)<20000; }
  function telemetry(def){ const aliases=[def?.id,...(def?.telemetryAliases||[])]; return (state.qc.gods||[]).find(item=>aliases.includes(item.id)); }
  function reasons(def){
    const id=def?.id, snap=state.snapshot.get(id), god=telemetry(def), issues=[];
    if(state.health.get(id)===false) issues.push(state.errors.get(id)||'Telemetry request failed');
    if(snap?.load_error) issues.push(snap.load_error);
    if(snap?.error) issues.push(typeof snap.error==='string'?snap.error:toJson(snap.error));
    if((id==='brahma'||id==='rishi-council')&&snap?.process_qc?.load_error) issues.push('Process QC: '+snap.process_qc.load_error);
    const aliases=[id,...(def?.telemetryAliases||[])];
    (state.qc.open_errors||[]).filter(item=>aliases.includes(item.component)).forEach(item=>issues.push(item.error||item.topic||'Unresolved process error'));
    if(god&&['error','failed','blocked','degraded'].includes(String(god.state).toLowerCase())) issues.push(god.detail||god.state);
    return [...new Set(issues)];
  }
  function nodeState(def, seen=new Set()){
    if(!def||seen.has(def.id)) return 'unverified';
    seen.add(def.id);
    const id=def.id, tasks=tasksFor(def), snap=state.snapshot.get(id), god=telemetry(def);
    if(def.endpoint&&state.health.get(id)===false) return 'disconnected';
    if(def.endpoint&&state.health.has(id)&&!fresh(id)) return 'stale';
    if(reasons(def).length) return 'degraded';
    if(snap?.enabled===false) return 'disabled';
    if(snap?.mode==='unconfigured'||snap?.configured===false||snap?.ready===false) return 'unconfigured';
    if(id==='krishna'&&state.status.core&&state.status.core!=='ONLINE') return 'disconnected';
    if(tasks.length&&(!state.refreshed||Date.now()-state.refreshed>20000)) return 'stale';
    const newest=tasks.slice().sort((a,b)=>updated(b)-updated(a))[0];
    if(newest&&FAILED.has(statusOf(newest))&&(!updated(newest)||Date.now()-updated(newest)<900000)) return 'degraded';
    if(tasks.some(task=>WAITING.has(statusOf(task)))) return 'waiting';
    if(tasks.some(task=>ACTIVE.has(statusOf(task)))) return 'working';
    const signal=String(id==='krishna'?state.status.system_light?.state:god?.state||snap?.light?.state||snap?.state||'').toLowerCase();
    if(['blocked','degraded','error','failed'].includes(signal)) return signal==='blocked'?'waiting':'degraded';
    if(['working','running','executing','healing','verifying'].includes(signal)||god?.active===true||snap?.busy===true){
      const stamp=seconds(god?.updated_at);
      return god&&Number.isFinite(stamp)&&Date.now()-stamp>60000?'stale':'working';
    }
    const subStates=children(def).map(key=>nodeState(node(key),new Set(seen)));
    if(subStates.some(value=>['degraded','disconnected','waiting'].includes(value))) return 'degraded';
    if(subStates.includes('working')) return 'working';
    if(subStates.some(value=>['disabled','unconfigured','stale'].includes(value))) return 'limited';
    if(!def.endpoint&&god&&!fresh('rishi-council')) return 'stale';
    if(['idle','completed','complete','done','verified'].includes(signal)||god?.active===false||snap?.busy===false) return 'idle';
    if(state.health.get(id)===true) return 'connected';
    if(tasks.some(task=>statusOf(task)==='queued')) return 'queued';
    return 'unverified';
  }
  function tone(value){ return value==='working'?'active':['connected','idle','verified'].includes(value)?'green':['degraded','waiting','disconnected'].includes(value)?'red':'yellow'; }
  function deepNumber(value,names){ const queue=[value]; while(queue.length){ const item=queue.shift(); if(!item||typeof item!=='object') continue; for(const [k,v] of Object.entries(item)){ const key=k.toLowerCase().replaceAll('_','').replaceAll('-',''); if(names.some((n)=>key.includes(n))){ const num=typeof v==='number'?v:typeof v==='string'?Number(v.replace('%','')):NaN; if(Number.isFinite(num)&&num>=0&&num<=100) return num; } if(v&&typeof v==='object') queue.push(v); } } return null; }
  function lrRefresh(){ return window.__KRISHNA_LR_REFRESH__||window.KRISHNA_OWNER_UI?.refreshLR; }


  function addMenu(){ const menu=qs('.mainMenuNav'); if(!menu||$('kbNavBrahmand')) return; const lr=document.createElement('button'); lr.id='kbNavLR'; lr.innerHTML='<span class="ico">◎</span><span class="txt">LR Universe Dashboard</span>'; lr.onclick=()=>showCustom('lrUniverse'); const pipe=document.createElement('button'); pipe.id='kbNavBrahmand'; pipe.innerHTML='<span class="ico">✦</span><span class="txt">Krishna Brahmand</span>'; pipe.onclick=()=>showCustom('brahmand'); menu.append(lr,pipe); }

  function addSidebarTelemetry(){ const foot=qs('.sideFoot'),vitals=qs('.opsVitals',foot); if(!foot||!vitals||$('kbSuryaCard')) return; const surya=document.createElement('section'); surya.id='kbSuryaCard'; surya.className='kb-side-card'; surya.innerHTML='<div class="kb-side-card-head"><span>☀</span><strong>SURYA DEV</strong><i id="kbSuryaDot" class="kb-live-dot yellow"></i></div><div id="kbSuryaState" class="kb-side-card-value yellow">UNVERIFIED</div><small id="kbSuryaCount">Systems working now: 0</small>'; const mobile=document.createElement('section'); mobile.id='kbMobileCard'; mobile.className='kb-side-card'; mobile.innerHTML='<div class="kb-side-card-head"><span>▯</span><strong>MOBILE</strong><i id="kbMobileDot" class="kb-live-dot red"></i></div><div id="kbMobileState" class="kb-side-card-value red">UNVERIFIED</div><small id="kbMobileDetail">No confirmed live link</small>'; vitals.after(surya,mobile); }

  function addCosmicOm(){ const home=qs('#home .assistantHome'),om=$('assistantOm'); if(!home||!om||qs('.kb-core-shell',home)) return; const shell=document.createElement('div'); shell.className='kb-core-shell'; const canvas=document.createElement('canvas'); canvas.className='kb-cosmos'; const r1=document.createElement('i');r1.className='kb-orbit o1'; const r2=document.createElement('i');r2.className='kb-orbit o2'; const r3=document.createElement('i');r3.className='kb-orbit o3'; const status=document.createElement('div');status.id='kbCoreStatus';status.className='kb-core-status';status.innerHTML='<i></i><span>KRISHNA · IDLE</span>'; home.insertBefore(shell,om); shell.append(canvas,r1,r2,r3,om,status); om.innerHTML='<span class="kb-om-depth">ॐ</span>'; startCosmos(canvas,shell); }

  function startCosmos(canvas,shell){
    const ctx=canvas.getContext('2d'); if(!ctx) return;
    const dots=Array.from({length:64},(_,i)=>({a:Math.random()*Math.PI*2,r:Math.sqrt(Math.random())*.46,s:i%11===0?2:1,p:Math.random()*Math.PI*2}));
    const pointer={x:.5,y:.5},motion=matchMedia('(prefers-reduced-motion: reduce)');
    let tick=0,raf=0,last=0;
    shell.addEventListener('pointermove',event=>{const rect=shell.getBoundingClientRect();pointer.x=(event.clientX-rect.left)/rect.width;pointer.y=(event.clientY-rect.top)/rect.height});
    shell.addEventListener('pointerleave',()=>{pointer.x=.5;pointer.y=.5});
    const draw=time=>{
      raf=0;
      if(document.hidden||!$('home')?.classList.contains('active')) return;
      if(time-last<33){ if(!motion.matches)raf=requestAnimationFrame(draw);return; }
      last=time;
      const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.round(rect.width*dpr)),h=Math.max(1,Math.round(rect.height*dpr));
      if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}
      ctx.clearRect(0,0,w,h);
      const scale=Math.min(w,h),speed=nodeState(node('krishna'))==='working'?.026:.010;
      const pts=dots.map((dot,i)=>{const wave=motion.matches?0:Math.sin(tick*speed+dot.p+i*.17)*.015,r=(dot.r+wave)*scale;return{x:w/2+Math.cos(dot.a+tick*speed*.16)*r+(pointer.x-.5)*scale*.035,y:h/2+Math.sin(dot.a+tick*speed*.14)*r+(pointer.y-.5)*scale*.035,s:dot.s*dpr}});
      const palette=getComputedStyle(shell),accent=palette.getPropertyValue('--kb-cyan').trim()||'#6d74e8',secondary=palette.getPropertyValue('--kb-gold').trim()||'#a777d8';
      ctx.strokeStyle=accent;ctx.lineWidth=.7*dpr;
      for(let i=0;i<pts.length;i++){
        for(let j=i+1;j<pts.length;j++){const a=pts[i],b=pts[j],distance=Math.hypot(a.x-b.x,a.y-b.y),maximum=scale*.115;if(distance>maximum)continue;ctx.globalAlpha=.18*(1-distance/maximum);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}
        const point=pts[i];ctx.globalAlpha=.8;ctx.fillStyle=i%11===0?secondary:accent;ctx.beginPath();ctx.arc(point.x,point.y,point.s,0,Math.PI*2);ctx.fill();
      }
      ctx.globalAlpha=1; tick++;
      if(!motion.matches)raf=requestAnimationFrame(draw);
    };
    const resume=()=>{if(!raf&&!document.hidden&&$('home')?.classList.contains('active')){last=0;raf=requestAnimationFrame(draw)}};
    new MutationObserver(resume).observe($('home'),{attributes:true,attributeFilter:['class']});
    document.addEventListener('visibilitychange',resume);motion.addEventListener('change',resume);window.addEventListener('resize',resume);
    window.addEventListener('beforeunload',()=>cancelAnimationFrame(raf),{once:true});resume();
  }


  function addViews(){ const main=qs('main.main'); if(!main) return; if(!$('brahmand')){const view=document.createElement('section');view.id='brahmand';view.className='kb-view';view.innerHTML='<div class="kb-dashboard"><header class="kb-dash-head"><div><small>LIVE INTERNAL INTELLIGENCE MAP</small><h1>KRISHNA BRAHMAND</h1><p>Open a branch to inspect live work, connections and verification evidence.</p></div><div class="kb-dash-actions"><button id="kbRefreshGraph">↻ Refresh</button></div></header><div class="kb-brahmand-grid"><div class="kb-graph-shell"><div id="kbCrumb" class="kb-crumb"></div><svg id="kbGraphSvg"></svg><div id="kbGraphNodes"></div></div><aside id="kbInspector" class="kb-inspector"></aside></div></div>';main.appendChild(view);$('kbRefreshGraph').onclick=()=>refresh(true)} if(!$('lrUniverse')){const view=document.createElement('section');view.id='lrUniverse';view.className='kb-view';view.innerHTML='<div class="kb-dashboard"><header class="kb-dash-head"><div><small>KRISHNA SUPERVISED BUSINESS UNIVERSE</small><h1>LR UNIVERSE DASHBOARD</h1><p>Observed LR work only. No backend record means no invented company status.</p></div><div class="kb-dash-actions"><button id="kbRefreshLR">↻ Refresh</button></div></header><div id="kbLRBody" class="kb-lr-body"></div></div>';main.appendChild(view);$('kbRefreshLR').onclick=()=>lrRefresh()?lrRefresh()():refresh(true)} }

  const originalShow = typeof window.showView==='function' ? window.showView.bind(window) : null;
  function clearCustomNav(){ $('kbNavLR')?.removeAttribute('data-brahmand-active'); $('kbNavBrahmand')?.removeAttribute('data-brahmand-active'); }
  function showCustom(id){ qsa('.view,.kb-view').forEach((v)=>v.classList.remove('active')); $(id)?.classList.add('active'); document.body.dataset.view=id; qsa('.mainMenuNav button').forEach((b)=>b.classList.remove('active')); clearCustomNav(); if(id==='brahmand'){ $('kbNavBrahmand')?.setAttribute('data-brahmand-active','1'); renderGraph(); } else { $('kbNavLR')?.setAttribute('data-brahmand-active','1'); if(lrRefresh())lrRefresh()();else renderLR(); } }
  window.showView=(id)=>{ if(id==='brahmand'||id==='lrUniverse') return showCustom(id); qsa('.kb-view').forEach((v)=>v.classList.remove('active')); clearCustomNav(); return originalShow?originalShow(id):undefined; };

  function visibleIds(){ return state.group==='root'?['krishna',...DATA.root]:[state.group,...children(node(state.group))]; }
  function navigate(id){
    const def=node(id);if(!def)return;
    if(children(def).length&&id!==state.group){state.history.push({group:state.group,selected:state.selected});state.group=id;}
    state.selected=id;renderGraph();refresh().catch(()=>{});
  }
  window.__KRISHNA_BRAHMAND_NAV_BACK__=()=>{const previous=state.history.pop();state.group=previous?.group||'root';state.selected=previous?.selected||'krishna';renderGraph();};
  function layout(ids){
    const shell=qs('.kb-graph-shell'),box=$('kbGraphNodes'),svg=$('kbGraphSvg'),buttons=qsa('.kb-node',box);
    const nodeWidth=Math.max(165,...buttons.map(button=>button.offsetWidth)),nodeHeight=Math.max(80,...buttons.map(button=>button.offsetHeight));
    const width=Math.max(shell.clientWidth,nodeWidth+48),columns=Math.max(1,Math.min(3,Math.floor((width-40)/(nodeWidth+28)))),rows=Math.ceil((ids.length-1)/columns),spacing=nodeHeight+48;
    const height=Math.max(shell.clientHeight,190+rows*spacing);
    shell.style.overflow='auto';box.style.width=width+'px';box.style.height=height+'px';svg.style.width=width+'px';svg.style.height=height+'px';svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    const positions=[{id:ids[0],x:width/2,y:100}];
    ids.slice(1).forEach((id,i)=>positions.push({id,x:(width/columns)*(i%columns+.5),y:210+Math.floor(i/columns)*spacing}));
    return positions;
  }
  function pairs(ids){ return ids.slice(1).map(id=>[ids[0],id]); }
  function renderGraph(){
    const box=$('kbGraphNodes'),crumb=$('kbCrumb');if(!box||!crumb)return;
    const ids=visibleIds(),same=box.dataset.group===state.group&&box.children.length===ids.length;
    if(!same){box.innerHTML='';box.dataset.group=state.group;qs('.kb-graph-shell').scrollTop=0;}
    crumb.innerHTML='';const root=document.createElement('button');root.textContent='KRISHNA BRAHMAND';root.onclick=()=>{state.group='root';state.selected='krishna';state.history=[];renderGraph()};crumb.append(root);
    if(state.group!=='root'){const label=document.createElement('span');label.textContent='› '+node(state.group).label;crumb.append(label);}
    ids.forEach(id=>{
      const def=node(id);if(!def)return;
      const ns=nodeState(def),tasks=tasksFor(def),active=tasks.filter(task=>ACTIVE.has(statusOf(task))).length;
      let button=qsa('.kb-node',box).find(item=>item.dataset.node===id);
      if(!button){button=document.createElement('button');button.type='button';button.dataset.node=id;button.onclick=()=>navigate(id);box.append(button);}
      button.className='kb-node'+(id===ids[0]?' root':'')+(state.selected===id?' selected':'');button.dataset.state=ns;button.setAttribute('aria-pressed',String(state.selected===id));
      button.title=children(def).length&&id!==state.group?'Open '+def.label+' pipeline':'Inspect '+def.label;
      const content=`<span class="kb-node-icon">${esc(def.icon||'◈')}</span><span><strong>${esc(def.label)}</strong><small>${esc(def.role)}</small><span class="kb-node-state"><i class="${tone(ns)}"></i>${esc(ns.replaceAll('_',' '))}${active?' · '+active+' active':tasks.length?' · '+tasks.length+' recorded':''}</span></span>`;
      if(button.innerHTML!==content)button.innerHTML=content;
    });
    layout(ids).forEach(({id,x,y})=>{const button=qsa('.kb-node',box).find(item=>item.dataset.node===id);if(button){button.style.left=x+'px';button.style.top=y+'px';}});
    requestAnimationFrame(()=>{renderEdges();renderInspector()});
  }
  function renderEdges(){
    const svg=$('kbGraphSvg'),box=$('kbGraphNodes');if(!svg||!box)return;svg.innerHTML='';
    pairs(visibleIds()).forEach(([from,to])=>{
      const a=qsa('.kb-node',box).find(item=>item.dataset.node===from),b=qsa('.kb-node',box).find(item=>item.dataset.node===to);if(!a||!b)return;
      const x1=parseFloat(a.style.left),y1=parseFloat(a.style.top)+a.offsetHeight/2,x2=parseFloat(b.style.left),y2=parseFloat(b.style.top)-b.offsetHeight/2,mid=(y1+y2)/2,target=nodeState(node(to));
      const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',`M ${x1} ${y1} C ${x1} ${mid}, ${x2} ${mid}, ${x2} ${y2}`);path.setAttribute('class','kb-edge '+tone(target));path.dataset.from=from;path.dataset.to=to;path.dataset.state=target;svg.append(path);
    });
  }
  function renderInspector(){
    const box=$('kbInspector');if(!box)return;
    const def=node(state.selected)||node('krishna'),id=def.id,tasks=tasksFor(def).slice().sort((a,b)=>updated(b)-updated(a)),ns=nodeState(def),health=state.health.get(id),snap=state.snapshot.get(id),god=telemetry(def),first=tasks.find(task=>ACTIVE.has(statusOf(task))||WAITING.has(statusOf(task)))||tasks[0]||{};
    const deps=field(first,['dependencies','depends_on','dependency_ids','dependsOn']),evidence=tasks.filter(NORMAL.verification),errors=reasons(def),latency=state.latency.get(id),failed=tasks.filter(task=>FAILED.has(statusOf(task))),waiting=tasks.filter(task=>WAITING.has(statusOf(task))),completed=tasks.filter(task=>DONE.has(statusOf(task)));
    const inputs=DATA.input[id]||[state.group==='root'?'KRISHNA':node(state.group)?.label||'KRISHNA'],outputs=DATA.output[id]||['KRISHNA'];
    const checks=[['Telemetry reached',def.endpoint?(health===true?'ok':'bad'):god?'ok':'warn'],['Telemetry fresh',fresh(def.endpoint?id:'rishi-council')?'ok':'warn'],['Current work attributed',tasks.some(task=>ACTIVE.has(statusOf(task)))?'ok':'warn'],['No unresolved operational errors',errors.length?'bad':'ok'],['Recorded verification evidence',evidence.length?'ok':'warn']];
    const stamp=field(first,['updated_at','updated','timestamp','last_update'])||god?.updated_at,formatted=Number.isFinite(seconds(stamp))?new Date(seconds(stamp)).toLocaleString():text(stamp);
    const connection=def.endpoint?(health===true?'REACHABLE':health===false?'FAILED':'CHECKING'):god?'PROCESS QC':'NO DEDICATED SIGNAL';
    const content=`<div class="kb-inspector-head"><div class="kb-inspector-logo">${esc(def.icon||'◈')}</div><div><small>SELECTED INTELLIGENCE</small><h2>${esc(def.label)}</h2></div></div><p class="kb-inspector-role">${esc(def.role)}</p>
      <div class="kb-metric-row"><span>Operational state</span><b>${esc(ns.toUpperCase())}</b></div><div class="kb-metric-row"><span>Telemetry connection</span><b>${connection}</b></div><div class="kb-metric-row"><span>Endpoint latency</span><b>${latency==null?'—':Math.round(latency)+' ms'}</b></div>
      <div class="kb-metric-row"><span>Active / waiting</span><b>${tasks.filter(task=>ACTIVE.has(statusOf(task))).length} / ${waiting.length}</b></div><div class="kb-metric-row"><span>Completed / historical failures</span><b>${completed.length} / ${failed.length}</b></div><div class="kb-metric-row"><span>Verified task receipts</span><b>${evidence.length}</b></div>
      <div class="kb-metric-row"><span>Project</span><b>${esc(text(field(first,['project','project_name'])))}</b></div><div class="kb-metric-row"><span>Model</span><b>${esc(text(field(first,['model','model_id','selected_model','provider'])))}</b></div><div class="kb-metric-row"><span>System / device</span><b>${esc(text(field(first,['system','system_id','device','device_id','host','machine'])))}</b></div><div class="kb-metric-row"><span>Latest source update</span><b>${esc(formatted)}</b></div>
      <section class="kb-inspector-section"><h3>PIPELINE RELATIONSHIPS</h3><div class="kb-pill-wrap"><span class="kb-pill">INPUT · ${esc(inputs.join(', '))}</span><span class="kb-pill">OUTPUT · ${esc(outputs.join(', '))}</span></div></section>
      ${children(def).length?`<section class="kb-inspector-section"><h3>OPEN A BRANCH</h3><div class="kb-pill-wrap">${children(def).map(key=>`<button type="button" class="kb-pill" data-open-node="${esc(key)}">${esc(node(key).label)} · ${esc(nodeState(node(key)))}</button>`).join('')}</div></section>`:''}
      <section class="kb-inspector-section"><h3>LIVE CHECKS</h3>${checks.map(([label,status])=>`<div class="kb-check ${status}"><i></i><span>${esc(label)}</span></div>`).join('')}</section>
      <section class="kb-inspector-section"><h3>OPERATIONAL ERRORS</h3>${errors.length?errors.map(error=>`<div class="kb-check bad"><i></i><span>${esc(error)}</span></div>`).join(''):`<div class="kb-check ${ns==='unverified'?'warn':'ok'}"><i></i><span>${ns==='unverified'?'No operational signal available.':'No unresolved error exposed by current telemetry.'}</span></div>`}${ns==='disabled'||ns==='unconfigured'?`<div class="kb-check warn"><i></i><span>${ns==='disabled'?'This component is disabled in backend configuration.':'This component requires configuration before use.'}</span></div>`:''}</section>
      <section class="kb-inspector-section"><h3>TASK LEDGER</h3>${tasks.length?tasks.slice(0,8).map(task=>`<div class="kb-task"><b>${esc(text(field(task,['title','name','summary','goal','description','id','task_id']),'Task'))}</b><span>${esc(text(task.status,'unknown'))}${NORMAL.verification(task)?' · verified receipt':''}</span>${field(task,['error','blocker','blocked_reason'])?`<span>${esc(field(task,['error','blocker','blocked_reason']))}</span>`:''}</div>`).join(''):'<div class="kb-check warn"><i></i><span>No task has been attributed to this pipeline.</span></div>'}</section>
      <section class="kb-inspector-section"><h3>DEPENDENCIES</h3><div class="kb-check ${Array.isArray(deps)&&deps.length?'ok':'warn'}"><i></i><span>${Array.isArray(deps)?deps.length+' declared dependencies':'No dependency list exposed in latest task.'}</span></div></section><details><summary>Exact backend telemetry</summary><pre>${esc(toJson({endpoint:snap||null,process:god||null,task:first}))}</pre></details>`;
    if(box.dataset.node!==id){box.scrollTop=0;box.dataset.node=id;}
    if(box.innerHTML!==content){const detailsOpen=!!qs('details',box)?.open,scroll=box.scrollTop;box.innerHTML=content;if(detailsOpen)qs('details',box).open=true;box.scrollTop=scroll;}
    qsa('[data-open-node]',box).forEach(button=>button.onclick=()=>navigate(button.dataset.openNode));
  }
  async function json(url){
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
    try{const response=await fetch(url,{cache:'no-store',signal:controller.signal});if(!response.ok)throw new Error('HTTP '+response.status);return await response.json();}finally{clearTimeout(timer);}
  }
  async function probeEndpoint(url,ids){
    const start=performance.now();try{const data=await json(url);ids.forEach(id=>{state.health.set(id,true);state.errors.delete(id);state.snapshot.set(id,data);state.received.set(id,Date.now());state.latency.set(id,performance.now()-start)});if(url==='/api/brahma/status')state.qc=data.process_qc||{};}catch(error){ids.forEach(id=>{state.health.set(id,false);state.errors.set(id,error.message||String(error));state.latency.set(id,performance.now()-start)});}
  }


  function updateSidebar(){const source=state.status.resources||state.status.pc_observer||state.status,cpu=deepNumber(source,['cpu','processor']),gpu=deepNumber(source,['gpu','graphics']),load=$('opsLoadText');if(load)load.textContent=`CPU ${cpu==null?'—':Math.round(cpu)+'%'} · GPU ${gpu==null?'—':Math.round(gpu)+'%'} · NET ${navigator.onLine?'ONLINE':'OFFLINE'}`;const surya=state.tasks.filter((t)=>ownerOf(t).includes('surya')),active=surya.filter((t)=>ACTIVE.has(statusOf(t))),blocked=surya.some((t)=>BLOCKED.has(statusOf(t))),systems=new Set(active.map((t)=>field(t,['system','system_id','device','device_id','host','target','machine'])).filter(Boolean).map(String)),core=state.health.get('krishna')===true&&fresh('krishna')&&(state.status.core==='ONLINE'||state.status.ok===true),sTone=!core||blocked?'red':active.length?'green':'yellow',sLabel=sTone==='green'?'RUNNING':sTone==='yellow'?'IDLE':'BLOCKED / UNVERIFIED';const ss=$('kbSuryaState'),sd=$('kbSuryaDot'),sc=$('kbSuryaCount');if(ss){ss.className='kb-side-card-value '+sTone;ss.textContent=sLabel}if(sd)sd.className='kb-live-dot '+sTone;if(sc)sc.textContent=`Systems working now: ${systems.size||(active.length?1:0)}`;const mobileText=toJson(state.mobile).toLowerCase(),mTone=(state.mobile.connected===true||state.mobile.online===true||state.mobile.live===true||state.mobile.paired===true&&state.mobile.reachable===true)?'green':(/"paired"\s*:\s*true|"idle"/.test(mobileText)?'yellow':'red'),mLabel=mTone==='green'?'CONNECTED':mTone==='yellow'?'IDLE':'DISCONNECTED / UNVERIFIED';const ms=$('kbMobileState'),md=$('kbMobileDot'),mt=$('kbMobileDetail');if(ms){ms.className='kb-side-card-value '+mTone;ms.textContent=mLabel}if(md)md.className='kb-live-dot '+mTone;if(mt)mt.textContent=mTone==='green'?'Live companion link':mTone==='yellow'?'Known device · idle':'No confirmed live link';const dot=$('dot'),side=$('sideStatus');if(dot)dot.classList.toggle('on',core);if(side)side.textContent=core?'Core Online':'Core Unverified'; }

  function updateCore(){const core=$('kbCoreStatus');if(!core)return;const s=nodeState(node('krishna'));core.className='kb-core-status'+(s==='working'?' working':['waiting','degraded','disconnected'].includes(s)?' blocked':'');const label=qs('span',core);if(label)label.textContent=`KRISHNA · ${s.toUpperCase()}`;}

  function renderLR(){const box=$('kbLRBody');if(!box)return;const lrTasks=state.tasks.filter((task)=>{const j=toJson(task).toLowerCase();return j.includes('lr ')||j.includes('lr_')||j.includes('lr-')||j.includes('universe')}),working=lrTasks.filter((t)=>ACTIVE.has(statusOf(t))).length,attention=lrTasks.filter((t)=>BLOCKED.has(statusOf(t))).length;box.innerHTML=`<div class="kb-lr-summary"><div class="kb-lr-metric"><span>OBSERVED LR TASKS</span><strong>${lrTasks.length}</strong></div><div class="kb-lr-metric"><span>WORKING</span><strong>${working}</strong></div><div class="kb-lr-metric"><span>NEEDS ATTENTION</span><strong>${attention}</strong></div><div class="kb-lr-metric"><span>KRISHNA AUTHORITY</span><strong>${state.status.core==='ONLINE'?'ONLINE':'UNVERIFIED'}</strong></div></div><div class="kb-company-grid">${DATA.companies.map(([name,terms],i)=>{const matches=lrTasks.filter((task)=>terms.some((term)=>toJson(task).toLowerCase().includes(term))),active=matches.filter((t)=>ACTIVE.has(statusOf(t))).length,blocked=matches.filter((t)=>BLOCKED.has(statusOf(t))).length;return `<article class="kb-company" style="animation-delay:-${i*.8}s"><h3>${name}</h3><p>${matches.length?'Observed backend work is mapped here.':'No matching backend work observed; no status is invented.'}</p><footer><span>Tasks <strong>${matches.length}</strong></span><span>Working <strong>${active}</strong></span><span>Blocked <strong>${blocked}</strong></span></footer></article>`}).join('')}</div>`;}

  async function refresh(force=false){
    if(state.busy)return;state.busy=true;
    const button=$('kbRefreshGraph');if(button)button.disabled=true;
    try{
      const [statusResult,tasksResult,mobileResult]=await Promise.allSettled([json('/api/status'),json('/api/tasks?limit=500'),json('/api/mobile/connection')]);
      if(statusResult.status==='fulfilled'){state.status=statusResult.value||{};state.health.set('krishna',true);state.errors.delete('krishna');state.snapshot.set('krishna',state.status);state.received.set('krishna',Date.now());}else{state.health.set('krishna',false);state.errors.set('krishna',statusResult.reason.message);}
      if(tasksResult.status==='fulfilled'){const value=tasksResult.value;state.tasks=Array.isArray(value)?value:Array.isArray(value?.tasks)?value.tasks:[];state.refreshed=Date.now();}else{state.refreshed=0;}
      if(mobileResult.status==='fulfilled')state.mobile=mobileResult.value||{};else state.mobile={connected:false,error:mobileResult.reason.message};
      const deep=force||Date.now()-state.lastDeepRefresh>=15000;
      const ids=new Set(deep?Object.keys(DATA.nodes):[...DATA.root,...visibleIds(),state.selected]);ids.delete('krishna');
      if(deep)state.lastDeepRefresh=Date.now();
      const endpoints=new Map();ids.forEach(id=>{const endpoint=node(id)?.endpoint;if(endpoint){if(!endpoints.has(endpoint))endpoints.set(endpoint,[]);endpoints.get(endpoint).push(id);}});
      if(!endpoints.has('/api/brahma/status'))endpoints.set('/api/brahma/status',['rishi-council','brahma']);
      await Promise.all([...endpoints].map(([url,mapped])=>probeEndpoint(url,mapped)));
      updateSidebar();updateCore();if($('brahmand')?.classList.contains('active'))renderGraph();
      window.dispatchEvent(new CustomEvent('krishna:brahmand-telemetry',{detail:{checked_at:new Date().toISOString(),tasks_fresh:!!state.refreshed,nodes:Object.keys(DATA.nodes).map(id=>({id,label:node(id).label,state:nodeState(node(id)),errors:reasons(node(id))}))}}));
      if(($('lrUniverse')?.classList.contains('active')||force)&&!lrRefresh())renderLR();
    }finally{state.busy=false;if(button)button.disabled=false;}
  }
  function boot(){
    addMenu();addSidebarTelemetry();addCosmicOm();addViews();refresh(true).catch(()=>{});
    setInterval(()=>{if(!document.hidden)refresh().catch(()=>{})},5000);
    window.addEventListener('resize',()=>{if($('brahmand')?.classList.contains('active'))requestAnimationFrame(renderGraph)});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh().catch(()=>{})});
  }


  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
