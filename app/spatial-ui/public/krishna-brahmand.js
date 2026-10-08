(() => {
  if (window.__KRISHNA_BRAHMAND_PREVIEW__) return;
  window.__KRISHNA_BRAHMAND_PREVIEW__ = true;

  const $ = (id) => document.getElementById(id);
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const safeText = (value, fallback = '—') => value === undefined || value === null || value === '' ? fallback : String(value);
  const nowText = () => new Date().toLocaleTimeString();
  const jsonText = (value) => { try { return JSON.stringify(value, null, 2); } catch { return String(value); } };

  const ACTIVE_STATES = new Set(['queued','running','working','executing','verifying']);
  const BLOCKED_STATES = new Set(['blocked','failed','error']);
  const DONE_STATES = new Set(['verified','done','completed','complete','passed']);

  const NODE_DEFS = {
    krishna: { id:'krishna', label:'KRISHNA', icon:'ॐ', role:'Authority · conversation · orchestration', endpoint:'/api/status', aliases:['krishna'] },
    'rishi-council': { id:'rishi-council', label:'RISHI COUNCIL', icon:'△', role:'Specialist reasoning council', endpoint:'/api/brahma/status', aliases:['rishi','council','brahma'], children:['vashistha','vishwamitra','vyasa','sushruta','kashyapa','atri','gautama','jamadagni','bharadvaja','kanada','kapila','patanjali','yajnavalkya','agastya'] },
    sudarshan: { id:'sudarshan', label:'SUDARSHAN', icon:'☸', role:'Execution · testing · verification', endpoint:'/api/tasks?project=KRISHNA&limit=300', aliases:['sudarshan'], children:['vishwakarma','ui-guardian','narad','project-perfection','developer','specialists'] },
    research: { id:'research', label:'KNOWLEDGE & RESEARCH', icon:'✦', role:'Deep research · verified knowledge · browser evidence', endpoint:'/api/brahma/intelligence/status', aliases:['brahmagyan','research','gyan'], children:['brahma','brahmagyan','gyan-bhandar','garuda','garudanetra'] },
    vision: { id:'vision', label:'VISION & LEARNING', icon:'◉', role:'Vision · camera · screen/audio learning', aliases:['hawkeye','surya','chandra','vision'], children:['hawkeye','suryadev','chandradev'] },
    protection: { id:'protection', label:'PROTECTION & RECOVERY', icon:'⬡', role:'Security · privacy · recovery', endpoint:'/api/kabach/privacy/status', aliases:['kabach','mrityunjaya','security'], children:['kabach','mrityunjaya'] },

    brahma: { id:'brahma', label:'BRAHMA', icon:'◈', role:'Knowledge process · council coordination', endpoint:'/api/brahma/status', aliases:['brahma'] },
    brahmagyan: { id:'brahmagyan', label:'BRAHMAGYAN', icon:'✦', role:'Deep research · synthesis', aliases:['brahmagyan'] },
    'gyan-bhandar': { id:'gyan-bhandar', label:'GYAN-BHANDAR', icon:'▤', role:'Verified knowledge archive', endpoint:'/api/gyan-bhandar/archive/status', aliases:['gyan-bhandar','gyan bhandar'] },
    garuda: { id:'garuda', label:'GARUDA', icon:'◆', role:'Research scout · evidence', aliases:['garuda'] },
    garudanetra: { id:'garudanetra', label:'GARUDANETRA', icon:'◉', role:'Browser · web research · evidence', endpoint:'/api/garudanetra/fabric', aliases:['garudanetra'] },
    hawkeye: { id:'hawkeye', label:'HAWKEYE', icon:'◉', role:'Vision · mobile · field sensing', endpoint:'/api/hawkeye/ruview/status', aliases:['hawkeye'] },
    suryadev: { id:'suryadev', label:'SURYA DEV', icon:'☀', role:'Screen/audio learning', aliases:['suryadev','surya dev','surya'] },
    chandradev: { id:'chandradev', label:'CHANDRA DEV', icon:'◐', role:'Camera observation', aliases:['chandradev','chandra dev','chandra'] },
    kabach: { id:'kabach', label:'KABACH', icon:'⬡', role:'Security · privacy · project boundary', endpoint:'/api/kabach/privacy/status', aliases:['kabach'] },
    mrityunjaya: { id:'mrityunjaya', label:'MRITYUNJAYA', icon:'♜', role:'Diagnosis · recovery · self-heal', endpoint:'/api/mrityunjay/status', aliases:['mrityunjaya','mrityunjay'] },
    vishwakarma: { id:'vishwakarma', label:'VISHWAKARMA', icon:'⚒', role:'Engineering · repair · design verification', endpoint:'/api/design/status', aliases:['vishwakarma'] },
    'ui-guardian': { id:'ui-guardian', label:'UI GUARDIAN', icon:'◇', role:'Rendered UI verification', endpoint:'/api/ui-guardian/registry?project=KRISHNA', aliases:['ui guardian','ui-guardian'] },
    narad: { id:'narad', label:'NARAD', icon:'♫', role:'Messaging · workflows · automation', aliases:['narad'] },
    'project-perfection': { id:'project-perfection', label:'PROJECT PERFECTION', icon:'◎', role:'Quality gates · project perfection', endpoint:'/api/project-perfection/status', aliases:['project perfection','project-perfection'] },
    developer: { id:'developer', label:'DEVELOPER', icon:'⌘', role:'Code implementation worker', aliases:['developer'] },
    specialists: { id:'specialists', label:'SPECIALISTS', icon:'⌘', role:'Specialist execution pool', aliases:['specialist','specialists'] },

    vashistha:{id:'vashistha',label:'VASHISTHA',icon:'✧',role:'Council reasoning',aliases:['vashistha']},
    vishwamitra:{id:'vishwamitra',label:'VISHWAMITRA',icon:'✧',role:'Council reasoning',aliases:['vishwamitra']},
    vyasa:{id:'vyasa',label:'VYASA',icon:'✧',role:'Synthesis · knowledge',aliases:['vyasa']},
    sushruta:{id:'sushruta',label:'SUSHRUTA',icon:'✧',role:'Health/medical specialist knowledge',aliases:['sushruta']},
    kashyapa:{id:'kashyapa',label:'KASHYAPA',icon:'✧',role:'Council specialist',aliases:['kashyapa']},
    atri:{id:'atri',label:'ATRI',icon:'✧',role:'Council specialist',aliases:['atri']},
    gautama:{id:'gautama',label:'GAUTAMA',icon:'✧',role:'Logic · reasoning',aliases:['gautama']},
    jamadagni:{id:'jamadagni',label:'JAMADAGNI',icon:'✧',role:'Council specialist',aliases:['jamadagni']},
    bharadvaja:{id:'bharadvaja',label:'BHARADVAJA',icon:'✧',role:'Engineering/science knowledge',aliases:['bharadvaja']},
    canada_placeholder:null,
    kanada:{id:'kanada',label:'KANADA',icon:'✧',role:'Physics · analytical reasoning',aliases:['kanada']},
    kapila:{id:'kapila',label:'KAPILA',icon:'✧',role:'Systems reasoning',aliases:['kapila']},
    patanjali:{id:'patanjali',label:'PATANJALI',icon:'✧',role:'Mind · discipline · wellness knowledge',aliases:['patanjali']},
    yajnavalkya:{id:'yajnavalkya',label:'YAJNAVALKYA',icon:'✧',role:'Philosophy · reasoning',aliases:['yajnavalkya']},
    agastya:{id:'agastya',label:'AGASTYA',icon:'✧',role:'Applied knowledge · engineering',aliases:['agastya']},
  };
  delete NODE_DEFS.canada_placeholder;

  const ROOT_IDS = ['rishi-council','sudarshan','research','vision','protection'];
  const GROUP_INPUT = {
    'rishi-council':['KRISHNA'], sudarshan:['KRISHNA'], research:['KRISHNA'], vision:['KRISHNA'], protection:['KRISHNA'],
    brahma:['RISHI COUNCIL','KRISHNA'], brahmagyan:['BRAHMA','KRISHNA'], 'gyan-bhandar':['BRAHMA','BRAHMAGYAN'], garuda:['KRISHNA'], garudanetra:['GARUDA','KRISHNA'],
    hawkeye:['KRISHNA'], suryadev:['KRISHNA'], chandradev:['KRISHNA'], kabach:['KRISHNA'], mrityunjaya:['KABACH','KRISHNA'],
    vishwakarma:['SUDARSHAN'], 'ui-guardian':['SUDARSHAN'], narad:['SUDARSHAN'], 'project-perfection':['SUDARSHAN'], developer:['SUDARSHAN'], specialists:['SUDARSHAN'],
  };
  const GROUP_OUTPUT = {
    'rishi-council':['KRISHNA'], sudarshan:['KRISHNA','QA/QC'], research:['KRISHNA'], vision:['KRISHNA'], protection:['KRISHNA','SUDARSHAN'],
    brahma:['KRISHNA','BRAHMAGYAN'], brahmagyan:['KRISHNA','GYAN-BHANDAR'], 'gyan-bhandar':['KRISHNA'], garuda:['GARUDANETRA','KRISHNA'], garudanetra:['KRISHNA'],
    hawkeye:['KRISHNA'], suryadev:['KRISHNA'], chandradev:['KRISHNA'], kabach:['MRITYUNJAYA','KRISHNA'], mrityunjaya:['SUDARSHAN','KRISHNA'],
    vishwakarma:['SUDARSHAN'], 'ui-guardian':['KRISHNA'], narad:['KRISHNA'], 'project-perfection':['KRISHNA'], developer:['SUDARSHAN'], specialists:['SUDARSHAN'],
  };

  const state = {
    tasks: [], status: {}, mobile: {}, endpointHealth: new Map(), endpointData: new Map(), endpointLatency: new Map(),
    selected:'krishna', group:'root', lastRefresh:0,
  };

  function deepNumber(value, names) {
    const queue = [value];
    while (queue.length) {
      const item = queue.shift();
      if (!item || typeof item !== 'object') continue;
      for (const [key, raw] of Object.entries(item)) {
        const normalized = key.toLowerCase().replaceAll('_','').replaceAll('-','');
        if (names.some((name) => normalized.includes(name))) {
          const n = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw.replace('%','')) : NaN;
          if (Number.isFinite(n) && n >= 0 && n <= 100) return n;
        }
        if (raw && typeof raw === 'object') queue.push(raw);
      }
    }
    return null;
  }

  function ownerText(task) {
    return [task.assigned_specialist,task.assignedSpecialist,task.specialist,task.agent,task.owner,task.worker,task.assignee]
      .filter((x)=>typeof x==='string').join(' ').toLowerCase().replaceAll('_',' ').replaceAll('-',' ');
  }
  function taskStatus(task) { return String(task.status || '').toLowerCase(); }
  function taskMatches(def, task) {
    const text = ownerText(task);
    if (!text) return false;
    return (def.aliases || [def.id]).some((alias)=>text.includes(String(alias).toLowerCase().replaceAll('_',' ').replaceAll('-',' ')));
  }
  function childIds(def) { return Array.isArray(def.children) ? def.children : []; }
  function tasksForNode(def) {
    const direct = state.tasks.filter((task)=>taskMatches(def,task));
    if (!childIds(def).length) return direct;
    const ids = childIds(def).map((id)=>NODE_DEFS[id]).filter(Boolean);
    const nested = state.tasks.filter((task)=>ids.some((child)=>taskMatches(child,task)));
    return [...new Map([...direct,...nested].map((task,index)=>[String(task.id||task.task_id||index),task])).values()];
  }
  function nodeState(def) {
    const tasks = tasksForNode(def);
    if (tasks.some((task)=>BLOCKED_STATES.has(taskStatus(task)))) return 'blocked';
    if (tasks.some((task)=>ACTIVE_STATES.has(taskStatus(task)))) return 'working';
    if (tasks.some((task)=>DONE_STATES.has(taskStatus(task)))) return 'verified';
    const health = state.endpointHealth.get(def.id);
    if (health === true) return 'connected';
    if (health === false) return 'disconnected';
    return 'unverified';
  }
  function colorClass(nodeStateValue) {
    if (nodeStateValue === 'working') return 'active';
    if (nodeStateValue === 'verified' || nodeStateValue === 'connected') return 'green';
    if (nodeStateValue === 'blocked' || nodeStateValue === 'disconnected') return 'red';
    return 'yellow';
  }

  function ensureMenu() {
    const menu = qs('.mainMenuNav');
    if (!menu || $('kbNavBrahmand')) return;
    const lr = document.createElement('button');
    lr.id='kbNavLR'; lr.type='button'; lr.innerHTML='<span class="ico">◎</span><span class="txt">LR Universe Dashboard</span>';
    lr.addEventListener('click',()=>showCustomView('lrUniverse'));
    const pipe = document.createElement('button');
    pipe.id='kbNavBrahmand'; pipe.type='button'; pipe.innerHTML='<span class="ico">✦</span><span class="txt">Krishna Brahmand</span>';
    pipe.addEventListener('click',()=>showCustomView('brahmand'));
    menu.appendChild(lr); menu.appendChild(pipe);
  }

  function ensureSidebarTelemetry() {
    const foot = qs('.sideFoot');
    const vitals = qs('.opsVitals',foot);
    if (!foot || !vitals || $('kbSuryaCard')) return;
    const surya = document.createElement('section');
    surya.id='kbSuryaCard'; surya.className='kb-side-card';
    surya.innerHTML='<div class="kb-side-card-head"><span>☀</span><strong>SURYA DEV</strong><i id="kbSuryaDot" class="kb-live-dot yellow"></i></div><div id="kbSuryaState" class="kb-side-card-value yellow">UNVERIFIED</div><small id="kbSuryaCount">Systems working now: 0</small>';
    const mobile = document.createElement('section');
    mobile.id='kbMobileCard'; mobile.className='kb-side-card';
    mobile.innerHTML='<div class="kb-side-card-head"><span>▯</span><strong>MOBILE</strong><i id="kbMobileDot" class="kb-live-dot red"></i></div><div id="kbMobileState" class="kb-side-card-value red">UNVERIFIED</div><small id="kbMobileDetail">No confirmed live link</small>';
    vitals.after(surya,mobile);
  }

  function ensureHomeCore() {
    const home = qs('#home .assistantHome');
    const om = $('assistantOm');
    if (!home || !om || qs('.kb-core-shell',home)) return;
    const shell = document.createElement('div');
    shell.className='kb-core-shell';
    const canvas = document.createElement('canvas'); canvas.className='kb-cosmos'; canvas.id='kbCosmos';
    const o1=document.createElement('i');o1.className='kb-orbit o1';
    const o2=document.createElement('i');o2.className='kb-orbit o2';
    const o3=document.createElement('i');o3.className='kb-orbit o3';
    const status=document.createElement('div');status.id='kbCoreStatus';status.className='kb-core-status';status.innerHTML='<i></i><span>KRISHNA · IDLE</span>';
    home.insertBefore(shell,om); shell.append(canvas,o1,o2,o3,om,status);
    om.innerHTML='<span class="kb-om-depth">ॐ</span>';
    startCosmos(canvas,shell);
  }

  function startCosmos(canvas, shell) {
    const ctx = canvas.getContext('2d'); if (!ctx) return;
    const dots = Array.from({length:84},(_,i)=>({a:Math.random()*Math.PI*2,r:Math.sqrt(Math.random())*.46,s:i%11===0?2.1:1.15,p:Math.random()*Math.PI*2}));
    const pointer={x:.5,y:.5}; let raf=0; let tick=0;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const move=(e)=>{const rect=shell.getBoundingClientRect();pointer.x=(e.clientX-rect.left)/rect.width;pointer.y=(e.clientY-rect.top)/rect.height};
    shell.addEventListener('pointermove',move);shell.addEventListener('pointerleave',()=>{pointer.x=.5;pointer.y=.5});
    const draw=()=>{
      const rect=canvas.getBoundingClientRect();const dpr=Math.min(devicePixelRatio||1,2);const w=Math.max(1,Math.round(rect.width*dpr));const h=Math.max(1,Math.round(rect.height*dpr));
      if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}
      ctx.clearRect(0,0,w,h);const scale=Math.min(w,h);const working=nodeState(NODE_DEFS.krishna)==='working';const speed=working?.026:.010;
      const points=dots.map((d,i)=>{const wave=reduced?0:Math.sin(tick*speed+d.p+i*.17)*.015;const rr=(d.r+wave)*scale;const x=w/2+Math.cos(d.a+tick*speed*.16)*rr;const y=h/2+Math.sin(d.a+tick*speed*.14)*rr;const dx=(pointer.x-.5)*scale*.035,dy=(pointer.y-.5)*scale*.035;return{x:x+dx,y:y+dy,s:d.s*dpr}});
      const max=scale*.115;for(let i=0;i<points.length;i++){for(let j=i+1;j<points.length;j++){const a=points[i],b=points[j],dist=Math.hypot(a.x-b.x,a.y-b.y);if(dist>max)continue;ctx.strokeStyle=`rgba(105,215,238,${.18*(1-dist/max)})`;ctx.lineWidth=.7*dpr;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}const p=points[i];ctx.fillStyle=i%11===0?'rgba(232,201,119,.95)':'rgba(116,224,244,.88)';ctx.beginPath();ctx.arc(p.x,p.y,p.s,0,Math.PI*2);ctx.fill()}
      tick++;if(!reduced)raf=requestAnimationFrame(draw)
    };draw();
    window.addEventListener('beforeunload',()=>cancelAnimationFrame(raf),{once:true});
  }

  function ensureViews() {
    const main = qs('main.main'); if (!main) return;
    if (!$('brahmand')) {
      const view=document.createElement('section');view.id='brahmand';view.className='kb-view';
      view.innerHTML='<div class="kb-dashboard"><header class="kb-dash-head"><div><small>LIVE INTERNAL INTELLIGENCE MAP</small><h1>KRISHNA BRAHMAND</h1><p>Hierarchical pipeline: only active work flows animate. Select a system to inspect its exact dashboard.</p></div><div class="kb-dash-actions"><button id="kbRefreshGraph" type="button">↻ Refresh</button></div></header><div class="kb-brahmand-grid"><div class="kb-graph-shell"><div id="kbCrumb" class="kb-crumb"></div><svg id="kbGraphSvg" aria-hidden="true"></svg><div id="kbGraphNodes"></div></div><aside id="kbInspector" class="kb-inspector"></aside></div></div>';
      main.appendChild(view);$('kbRefreshGraph').addEventListener('click',()=>refreshAll(true));
    }
    if (!$('lrUniverse')) {
      const view=document.createElement('section');view.id='lrUniverse';view.className='kb-view';
      view.innerHTML='<div class="kb-dashboard"><header class="kb-dash-head"><div><small>KRISHNA SUPERVISED BUSINESS UNIVERSE</small><h1>LR UNIVERSE DASHBOARD</h1><p>Frontend view of LR work observed by KRISHNA. No company status is invented when backend records are absent.</p></div><div class="kb-dash-actions"><button id="kbRefreshLR" type="button">↻ Refresh</button></div></header><div id="kbLRBody" class="kb-lr-body"></div></div>';
      main.appendChild(view);$('kbRefreshLR').addEventListener('click',renderLRUniverse);
    }
  }

  const originalShowView = typeof window.showView === 'function' ? window.showView.bind(window) : null;
  function clearCustomNav() { ['kbNavLR','kbNavBrahmand'].forEach((id)=>$(id)?.removeAttribute('data-brahmand-active')); }
  function showCustomView(id) {
    qsa('.view,.kb-view').forEach((node)=>node.classList.remove('active'));
    $(id)?.classList.add('active'); document.body.dataset.view=id; clearCustomNav();
    if(id==='brahmand'){ $('kbNavBrahmand')?.setAttribute('data-brahmand-active','1'); renderGraph(); }
    if(id==='lrUniverse'){ $('kbNavLR')?.setAttribute('data-brahmand-active','1'); renderLRUniverse(); }
    qsa('.mainMenuNav button').forEach((b)=>b.classList.remove('active'));
  }
  window.showView = function(id) {
    if(id==='brahmand'||id==='lrUniverse') return showCustomView(id);
    qsa('.kb-view').forEach((node)=>node.classList.remove('active')); clearCustomNav();
    return originalShowView ? originalShowView(id) : undefined;
  };

  function groupIds() {
    if (state.group === 'root') return ['krishna',...ROOT_IDS];
    const def=NODE_DEFS[state.group]; return def ? [state.group,...childIds(def)] : ['krishna',...ROOT_IDS];
  }
  function layoutFor(ids) {
    if(state.group==='root') {
      const pos={krishna:[50,50],'rishi-council':[24,22],sudarshan:[77,27],research:[21,72],vision:[78,70],protection:[50,84]};
      return ids.map((id)=>({id,x:pos[id]?.[0]??50,y:pos[id]?.[1]??50}));
    }
    const children=ids.slice(1);const rows=Math.ceil(children.length/3);
    const positions=[{id:ids[0],x:17,y:50}];
    children.forEach((id,index)=>{const col=index%3,row=Math.floor(index/3);const x=46+col*22;const y=rows<=1?50:18+row*(64/Math.max(1,rows-1));positions.push({id,x,y})});
    return positions;
  }
  function edgePairs(ids) {
    if(state.group==='root') return ROOT_IDS.map((id)=>['krishna',id]);
    return ids.slice(1).map((id)=>[state.group,id]);
  }

  function renderGraph() {
    const nodesBox=$('kbGraphNodes'),svg=$('kbGraphSvg'),crumb=$('kbCrumb');if(!nodesBox||!svg||!crumb)return;
    const ids=groupIds(),layout=layoutFor(ids);nodesBox.innerHTML='';
    crumb.innerHTML='';const rootButton=document.createElement('button');rootButton.textContent='KRISHNA BRAHMAND';rootButton.onclick=()=>{state.group='root';state.selected='krishna';renderGraph()};crumb.appendChild(rootButton);
    if(state.group!=='root'){const sep=document.createElement('span');sep.textContent='›';crumb.appendChild(sep);const label=document.createElement('span');label.textContent=NODE_DEFS[state.group]?.label||state.group;crumb.appendChild(label)}
    layout.forEach(({id,x,y})=>{const def=NODE_DEFS[id];if(!def)return;const ns=nodeState(def),cc=colorClass(ns),tasks=tasksForNode(def);const button=document.createElement('button');button.type='button';button.className='kb-node'+(id==='krishna'||id===state.group?' root':'')+(state.selected===id?' selected':'');button.style.left=x+'%';button.style.top=y+'%';button.dataset.node=id;button.innerHTML=`<span class="kb-node-icon">${def.icon||'◈'}</span><span><strong>${def.label}</strong><small>${def.role}</small><span class="kb-node-state"><i class="${cc}"></i>${ns}${tasks.length?` · ${tasks.length} task${tasks.length===1?'':'s'}`:''}</span></span>`;button.onclick=()=>{state.selected=id;renderInspector();renderGraphEdges();qsa('.kb-node').forEach((n)=>n.classList.toggle('selected',n.dataset.node===id));if(childIds(def).length&&id!==state.group){state.group=id;state.selected=id;setTimeout(renderGraph,80)}};nodesBox.appendChild(button)});
    requestAnimationFrame(()=>{renderGraphEdges();renderInspector()});
  }

  function renderGraphEdges() {
    const svg=$('kbGraphSvg'),shell=qs('.kb-graph-shell');if(!svg||!shell)return;svg.innerHTML='';const shellRect=shell.getBoundingClientRect();
    edgePairs(groupIds()).forEach(([source,target],index)=>{const a=qs(`.kb-node[data-node="${source}"]`),b=qs(`.kb-node[data-node="${target}"]`);if(!a||!b)return;const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();const x1=ra.left+ra.width/2-shellRect.left,y1=ra.top+ra.height/2-shellRect.top,x2=rb.left+rb.width/2-shellRect.left,y2=rb.top+rb.height/2-shellRect.top;const bend=Math.max(55,Math.abs(x2-x1)*.42);const path=document.createElementNS('http://www.w3.org/2000/svg','path');const targetState=nodeState(NODE_DEFS[target]),sourceState=nodeState(NODE_DEFS[source]);const active=targetState==='working'||sourceState==='working';let cc=active?'active':(targetState==='blocked'||targetState==='disconnected'?'red':targetState==='unverified'?'yellow':'green');path.setAttribute('d',`M ${x1} ${y1} C ${x1+(x2>x1?bend:-bend)} ${y1}, ${x2-(x2>x1?bend:-bend)} ${y2}, ${x2} ${y2}`);path.setAttribute('class','kb-edge '+cc);path.setAttribute('data-edge',String(index));svg.appendChild(path)})
  }

  function field(task,names) {
    for(const name of names){if(task?.[name]!==undefined&&task?.[name]!==null&&task?.[name]!=='')return task[name]}
    return null;
  }
  function renderInspector() {
    const box=$('kbInspector');if(!box)return;const def=NODE_DEFS[state.selected]||NODE_DEFS.krishna;const tasks=tasksForNode(def);const ns=nodeState(def),cc=colorClass(ns);const health=state.endpointHealth.get(def.id);const latency=state.endpointLatency.get(def.id);const snap=state.endpointData.get(def.id);const first=tasks[0]||{};const deps=field(first,['dependencies','depends_on','dependency_ids','dependsOn']);const evidence=field(first,['verification','verification_evidence','evidence','test_results','tests','receipts']);const blocker=field(first,['error','blocker','blocked_reason','reason','failure']);const model=field(first,['model','model_id','selected_model','provider']);const project=field(first,['project','project_name']);const system=field(first,['system','system_id','device','device_id','host','machine']);const updated=field(first,['updated_at','updated','timestamp','last_update']);const children=childIds(def).map((id)=>NODE_DEFS[id]).filter(Boolean);
    const checks=[
      ['Task ownership mapped',tasks.length>0?'ok':'warn'],
      ['Dedicated telemetry endpoint',def.endpoint?(health===false?'bad':'ok'):'warn'],
      ['No blocking error',blocker?'bad':'ok'],
      ['Verification evidence present',evidence?'ok':'warn'],
      ['Data freshness',state.lastRefresh&&Date.now()-state.lastRefresh<15000?'ok':'warn'],
    ];
    box.innerHTML=`<div class="kb-inspector-head"><div class="kb-inspector-logo">${def.icon||'◈'}</div><div><small>SELECTED INTELLIGENCE</small><h2>${def.label}</h2></div></div><p class="kb-inspector-role">${def.role}</p>
      <div class="kb-metric-row"><span>Live state</span><b>${ns.toUpperCase()}</b></div>
      <div class="kb-metric-row"><span>Connection</span><b>${def.endpoint?(health===true?'CONNECTED':health===false?'FAILED':'CHECKING'):'TASK-DERIVED'}</b></div>
      <div class="kb-metric-row"><span>Endpoint latency</span><b>${latency==null?'—':Math.round(latency)+' ms'}</b></div>
      <div class="kb-metric-row"><span>Mapped tasks</span><b>${tasks.length}</b></div>
      <div class="kb-metric-row"><span>Project</span><b>${safeText(project)}</b></div>
      <div class="kb-metric-row"><span>Model</span><b>${safeText(model)}</b></div>
      <div class="kb-metric-row"><span>System / device</span><b>${safeText(system)}</b></div>
      <div class="kb-metric-row"><span>Latest update</span><b>${safeText(updated)}</b></div>
      <section class="kb-inspector-section"><h3>PIPELINE RELATIONSHIPS</h3><div class="kb-pill-wrap"><span class="kb-pill">INPUT FROM · ${(GROUP_INPUT[def.id]||[state.group==='root'?'KRISHNA':NODE_DEFS[state.group]?.label]).join(', ')}</span><span class="kb-pill">OUTPUT TO · ${(GROUP_OUTPUT[def.id]||['KRISHNA']).join(', ')}</span></div></section>
      ${children.length?`<section class="kb-inspector-section"><h3>INSIDE THIS PIPELINE</h3><div class="kb-pill-wrap">${children.map((c)=>`<span class="kb-pill">${c.label}</span>`).join('')}</div></section>`:''}
      <section class="kb-inspector-section"><h3>WHAT TO CHECK</h3>${checks.map(([label,status])=>`<div class="kb-check ${status}"><i></i><span>${label}</span></div>`).join('')}</section>
      <section class="kb-inspector-section"><h3>CURRENT WORK</h3>${tasks.length?tasks.slice(0,8).map((t)=>`<div class="kb-task"><b>${safeText(field(t,['title','name','summary','description','id','task_id']),'Task')}</b><span>${safeText(t.status,'unknown')}${field(t,['progress','progress_percent','percent'])!=null?' · '+field(t,['progress','progress_percent','percent'])+'%':''}</span></div>`).join(''):'<div class="kb-check warn"><i></i><span>No ledger task currently attributed.</span></div>'}</section>
      <section class="kb-inspector-section"><h3>BLOCKER / ERROR</h3><div class="kb-check ${blocker?'bad':'ok'}"><i></i><span>${blocker?safeText(blocker):'No blocker exposed in current task record.'}</span></div></section>
      <section class="kb-inspector-section"><h3>DEPENDENCIES & EVIDENCE</h3><div class="kb-check ${Array.isArray(deps)&&deps.length?'ok':'warn'}"><i></i><span>Dependencies: ${Array.isArray(deps)?deps.length:'not exposed'}</span></div><div class="kb-check ${evidence?'ok':'warn'}"><i></i><span>Verification evidence: ${evidence?'present':'not exposed'}</span></div></section>
      <details><summary>Exact backend telemetry</summary><pre>${jsonText(snap||first||{})}</pre></details>`;
  }

  async function probe(def) {
    if (!def.endpoint) return;
    const start=performance.now();
    try { const response=await fetch(def.endpoint,{cache:'no-store'});const text=await response.text();if(!response.ok)throw new Error(`HTTP ${response.status}`);let data={raw:text};try{data=JSON.parse(text)}catch{}state.endpointHealth.set(def.id,true);state.endpointData.set(def.id,data);state.endpointLatency.set(def.id,performance.now()-start); }
    catch(error){state.endpointHealth.set(def.id,false);state.endpointData.set(def.id,{error:error instanceof Error?error.message:String(error)});state.endpointLatency.set(def.id,performance.now()-start)}
  }

  async function refreshAll(force=false) {
    const requests=[
      fetch('/api/status',{cache:'no-store'}).then((r)=>r.ok?r.json():Promise.reject(new Error('status '+r.status))),
      fetch('/api/tasks?limit=500',{cache:'no-store'}).then((r)=>r.ok?r.json():Promise.reject(new Error('tasks '+r.status))),
      fetch('/api/mobile/connection',{cache:'no-store'}).then((r)=>r.ok?r.json():Promise.reject(new Error('mobile '+r.status))),
    ];
    const [statusR,tasksR,mobileR]=await Promise.allSettled(requests);
    if(statusR.status==='fulfilled')state.status=statusR.value||{};
    if(tasksR.status==='fulfilled')state.tasks=Array.isArray(tasksR.value?.tasks)?tasksR.value.tasks:[];
    if(mobileR.status==='fulfilled')state.mobile=mobileR.value||{};
    state.lastRefresh=Date.now();
    const visible = new Set(['krishna',...ROOT_IDS,...groupIds(),state.selected]);
    await Promise.all([...visible].map((id)=>NODE_DEFS[id]).filter(Boolean).filter((d)=>d.endpoint).map(probe));
    updateSidebarTelemetry();updateCoreStatus();
    if($('brahmand')?.classList.contains('active')) renderGraph();
    if($('lrUniverse')?.classList.contains('active')||force) renderLRUniverse();
  }

  function updateSidebarTelemetry() {
    const resources=state.status.resources||state.status.pc_observer||state.status;const cpu=deepNumber(resources,['cpu','processor']);const gpu=deepNumber(resources,['gpu','graphics']);
    const load=$('opsLoadText');if(load)load.textContent=`CPU ${cpu==null?'—':Math.round(cpu)+'%'} · GPU ${gpu==null?'—':Math.round(gpu)+'%'} · NET ${navigator.onLine?'ONLINE':'OFFLINE'}`;
    const surya=state.tasks.filter((t)=>ownerText(t).includes('surya'));const active=surya.filter((t)=>ACTIVE_STATES.has(taskStatus(t)));const blocked=surya.some((t)=>BLOCKED_STATES.has(taskStatus(t)));const systems=new Set(active.map((t)=>field(t,['system','system_id','device','device_id','host','target','machine'])).filter(Boolean).map(String));let sState=!state.status?.core?'red':blocked?'red':active.length?'green':'yellow';const sText=sState==='green'?'RUNNING':sState==='yellow'?'IDLE':'BLOCKED / UNVERIFIED';
    const sv=$('kbSuryaState'),sd=$('kbSuryaDot'),sc=$('kbSuryaCount');if(sv){sv.className='kb-side-card-value '+sState;sv.textContent=sText}if(sd)sd.className='kb-live-dot '+sState;if(sc)sc.textContent=`Systems working now: ${systems.size||(active.length?1:0)}`;
    const mText=jsonText(state.mobile).toLowerCase();let mState=/"connected"\s*:\s*true|"online"\s*:\s*true|"active"\s*:\s*true/.test(mText)?'green':(/"paired"\s*:\s*true|"idle"/.test(mText)?'yellow':'red');let mLabel=mState==='green'?'CONNECTED':mState==='yellow'?'IDLE':'DISCONNECTED / UNVERIFIED';const mv=$('kbMobileState'),md=$('kbMobileDot'),mt=$('kbMobileDetail');if(mv){mv.className='kb-side-card-value '+mState;mv.textContent=mLabel}if(md)md.className='kb-live-dot '+mState;if(mt)mt.textContent=mState==='green'?'Live companion link':mState==='yellow'?'Known device · idle':'No confirmed live link';
    const core=state.status?.core==='ONLINE'||state.status?.ok===true;const dot=$('dot'),text=$('sideStatus');if(dot)dot.classList.toggle('on',core);if(text)text.textContent=core?'Core Online':'Core Unverified';
  }

  function updateCoreStatus() {
    const core=$('kbCoreStatus');if(!core)return;const ns=nodeState(NODE_DEFS.krishna);core.className='kb-core-status'+(ns==='working'?' working':ns==='blocked'||ns==='disconnected'?' blocked':'');const label=qs('span',core);if(label)label.textContent=`KRISHNA · ${ns.toUpperCase()}`;
  }

  function renderLRUniverse() {
    const box=$('kbLRBody');if(!box)return;const companies=[
      ['LR Resources',['resources','waste','e-waste','ewaste']],['LR Technology',['technology','software','ai','it']],['LR Production',['production','film','animation','media']],['LR Construction',['construction','renovation']],['LR Homes',['homes','residential']],['LR Foods',['foods','beverage']],['LR Agro',['agro','agriculture','farm']],['LR Commerce',['commerce','retail','wholesale','e-commerce','ecommerce']]
    ];
    const lrTasks=state.tasks.filter((task)=>{const text=jsonText(task).toLowerCase();return text.includes('lr ')||text.includes('lr_')||text.includes('lr-')||text.includes('universe')});const working=lrTasks.filter((t)=>ACTIVE_STATES.has(taskStatus(t))).length;const attention=lrTasks.filter((t)=>BLOCKED_STATES.has(taskStatus(t))).length;
    box.innerHTML=`<div class="kb-lr-summary"><div class="kb-lr-metric"><span>OBSERVED LR TASKS</span><strong>${lrTasks.length}</strong></div><div class="kb-lr-metric"><span>WORKING</span><strong>${working}</strong></div><div class="kb-lr-metric"><span>NEEDS ATTENTION</span><strong>${attention}</strong></div><div class="kb-lr-metric"><span>KRISHNA AUTHORITY</span><strong>${state.status?.core==='ONLINE'?'ONLINE':'UNVERIFIED'}</strong></div></div><div class="kb-company-grid">${companies.map(([name,terms],i)=>{const matches=lrTasks.filter((task)=>terms.some((term)=>jsonText(task).toLowerCase().includes(term)));const active=matches.filter((t)=>ACTIVE_STATES.has(taskStatus(t))).length;const blocked=matches.filter((t)=>BLOCKED_STATES.has(taskStatus(t))).length;return `<article class="kb-company" style="animation-delay:-${i*.8}s"><h3>${name}</h3><p>${matches.length?'Observed backend work is mapped here.':'No matching backend work observed; no status is invented.'}</p><footer><span>Tasks <strong>${matches.length}</strong></span><span>Working <strong>${active}</strong></span><span>Blocked <strong>${blocked}</strong></span></footer></article>`}).join('')}</div>`;
  }

  function boot() {
    ensureMenu();ensureSidebarTelemetry();ensureHomeCore();ensureViews();
    refreshAll(true).catch(()=>{});
    setInterval(()=>refreshAll(false).catch(()=>{}),5000);
    window.addEventListener('resize',()=>{if($('brahmand')?.classList.contains('active'))requestAnimationFrame(renderGraphEdges)});
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
