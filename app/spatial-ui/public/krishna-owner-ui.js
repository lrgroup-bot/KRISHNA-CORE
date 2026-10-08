(() => {
  if (window.__KRISHNA_OWNER_UI__) return;
  window.__KRISHNA_OWNER_UI__ = true;

  const $ = (id) => document.getElementById(id);
  const qs = (s, root = document) => root.querySelector(s);
  const qsa = (s, root = document) => Array.from(root.querySelectorAll(s));
  const DATA = window.KRISHNA_BRAHMAND_DATA || {};
  const LR = window.LR_UNIVERSE_SOURCE_DATA || {};
  const state = { browserSession:'', browserOpen:false, lr:null, telemetry:null };

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  async function json(url, options){
    const response = await fetch(url, {cache:'no-store', ...(options||{})});
    let body = {};
    try { body = await response.json(); } catch { body = {error:`HTTP ${response.status}`}; }
    if (!response.ok) throw new Error(body.error || body.message || `HTTP ${response.status}`);
    return body;
  }
  function metric(value, names, max=100){
    const queue=[value];
    while(queue.length){
      const item=queue.shift(); if(!item || typeof item!=='object') continue;
      for(const [key,raw] of Object.entries(item)){
        const k=key.toLowerCase().replaceAll('_','').replaceAll('-','');
        if(names.some(n=>k.includes(n))){
          const number=typeof raw==='number'?raw:Number(String(raw).replace(/[^0-9.\-]/g,''));
          if(Number.isFinite(number) && number>=0 && number<=max) return number;
        }
        if(raw && typeof raw==='object') queue.push(raw);
      }
    }
    return null;
  }
  function loadTone(value){ return value == null ? 'unknown' : value >= 80 ? 'high' : 'good'; }
  function setMetric(id, value, suffix='%'){
    const el=$(id); if(!el) return;
    el.className=loadTone(value);
    el.textContent=value==null ? `—${suffix}` : `${Math.round(value)}${suffix}`;
  }

  function fixMenu(){
    const menu=qs('.mainMenuNav'); if(!menu) return;
    const lr=$('kbNavLR'), brahmand=$('kbNavBrahmand');
    if(lr){ const t=qs('.txt',lr); if(t)t.textContent='LR Universe'; }
    if(brahmand){
      const t=qs('.txt',brahmand); if(t)t.textContent='Brahmand';
      const icon=qs('.ico',brahmand); if(icon){ icon.innerHTML='<span class="kb-mini-universe"><i></i><i></i><i></i></span>'; }
    }
    const plugin=qs('.mainMenuPlugin');
    if(plugin && plugin.parentElement!==menu) menu.appendChild(plugin);
    const bottom=qs('.bottomNav'); if(bottom) bottom.hidden=true;
  }

  function compactStatus(){
    $('kbSuryaCard')?.remove();
    const foot=qs('.sideFoot'), vitals=qs('.opsVitals',foot); if(!foot||!vitals) return;
    if(!$('kbOwnerLoad')){
      const card=document.createElement('section');
      card.id='kbOwnerLoad'; card.className='kb-owner-compact kb-owner-load';
      card.innerHTML='<div class="kb-owner-title">SYSTEM LOAD</div><div class="kb-owner-row"><span>CPU</span><b id="kbCpu">—%</b><span>RAM</span><b id="kbRam">—%</b></div><div class="kb-owner-row"><span>GPU</span><b id="kbGpu">—%</b><span>NET</span><b id="kbNet">— Mbps</b></div>';
      vitals.after(card);
    }
    let mobile=$('kbMobileCard');
    if(!mobile){
      mobile=document.createElement('section'); mobile.id='kbMobileCard'; mobile.className='kb-owner-compact kb-owner-mobile';
      mobile.innerHTML='<div class="kb-mobile-row"><span>▯</span><strong>MOBILE</strong><i id="kbMobileDot" class="kb-live-dot red"></i><b id="kbMobileState">UNVERIFIED</b></div><small id="kbMobileDetail">No confirmed live link</small>';
      $('kbOwnerLoad')?.after(mobile);
    } else {
      mobile.className='kb-owner-compact kb-owner-mobile';
    }
  }

  async function refreshTelemetry(){
    try{
      const [status,mobile] = await Promise.allSettled([json('/api/status'),json('/api/mobile/status')]);
      const s=status.status==='fulfilled'?status.value:{};
      state.telemetry=s;
      setMetric('kbCpu',metric(s,['cpupercent','cpuusage','cpuload','cpu']));
      setMetric('kbRam',metric(s,['rampercent','memorypercent','memoryusage','ramusage']));
      setMetric('kbGpu',metric(s,['gpupercent','gpuusage','gpuload','gpu']));
      const net=metric(s,['downloadmbps','networkmbps','netspeedmbps','speedmbps'],100000);
      const netEl=$('kbNet'); if(netEl){netEl.className=net==null?'unknown':'good';netEl.textContent=net==null?'— Mbps':`${Math.round(net)} Mbps`;}
      if(mobile.status==='fulfilled'){
        const m=mobile.value||{}; const connected=Boolean(m.connected||m.online||m.paired&&m.reachable||m.live);
        const st=$('kbMobileState'), detail=$('kbMobileDetail'), dot=$('kbMobileDot');
        if(st){st.textContent=connected?'CONNECTED':'DISCONNECTED / UNVERIFIED';st.className=connected?'good':'bad';}
        if(detail) detail.textContent=connected?(m.device_name||m.device||'Live link confirmed'):'No confirmed live link';
        if(dot) dot.className='kb-live-dot '+(connected?'green':'red');
      }
    }catch{/* fail closed: leave unknown */}
  }

  function addCustomToolbar(){
    const brahmand=$('brahmand');
    if(brahmand && !$('kbGraphToolbar')){
      const bar=document.createElement('div'); bar.id='kbGraphToolbar'; bar.className='kb-view-toolbar';
      bar.innerHTML='<button id="kbGraphBack" type="button">← Back</button><span>Brahmand</span><button id="kbGraphHome" type="button">◎ Root</button><button id="kbGraphRefresh2" type="button">↻</button>';
      const dashboard=qs('.kb-dashboard',brahmand); dashboard?.prepend(bar);
      $('kbGraphBack').onclick=()=>{
        if(window.__KRISHNA_BRAHMAND_NAV_BACK__) window.__KRISHNA_BRAHMAND_NAV_BACK__();
        else $('kbCrumb')?.querySelector('button')?.click();
      };
      $('kbGraphHome').onclick=()=> $('kbCrumb')?.querySelector('button')?.click();
      $('kbGraphRefresh2').onclick=()=> $('kbRefreshGraph')?.click();
    }
    const lr=$('lrUniverse');
    if(lr && !$('kbLRToolbar')){
      const bar=document.createElement('div'); bar.id='kbLRToolbar'; bar.className='kb-view-toolbar';
      bar.innerHTML='<span>LR Universe</span><span id="kbLRLiveBadge" class="kb-live-badge">CHECKING</span><button id="kbLRRefresh2" type="button">↻</button>';
      qs('.kb-dashboard',lr)?.prepend(bar);
      $('kbLRRefresh2').onclick=refreshLR;
    }
  }

  function list(items, empty='None'){
    const rows=(items||[]).map(x=>typeof x==='string'?x:(x.name||x.id||JSON.stringify(x)));
    return rows.length?rows.map(x=>`<span>${esc(x)}</span>`).join(''):`<span class="muted">${esc(empty)}</span>`;
  }
  async function refreshLR(){
    const body=$('kbLRBody'); if(!body) return;
    const badge=$('kbLRLiveBadge'); if(badge){badge.textContent='CHECKING';badge.className='kb-live-badge';}
    const endpoints=[['health','/lr-universe-api/health'],['providers','/lr-universe-api/api/providers'],['platforms','/lr-universe-api/api/distribution/platforms'],['market','/lr-universe-api/api/market-intelligence/schema']];
    const live={}; let connected=0;
    await Promise.all(endpoints.map(async([key,url])=>{try{live[key]=await json(url);connected++;}catch(error){live[key]={error:error.message};}}));
    state.lr=live;
    if(badge){badge.textContent=connected?`LIVE ${connected}/${endpoints.length}`:'BACKEND OFFLINE';badge.className='kb-live-badge '+(connected?'good':'bad');}
    const companies=(DATA.companies||[]).map(row=>row[0]);
    const departments=LR.sharedDepartments||[];
    const desks=Object.entries(LR.ownerDesks||{}).map(([name,value])=>({name,mission:value.mission}));
    const providers=live.providers?.providers?.map(p=>p.name) || LR.providers || [];
    const platforms=live.platforms?.platforms?.map(p=>p.name) || LR.platforms || [];
    body.innerHTML=`
      <div class="kb-lr-grid">
       <section class="kb-lr-card wide"><div class="eyebrow">ORIGINAL LR UNIVERSE SOURCE</div><strong>${esc(LR.sourceRepo||'lrgroup-bot/LR_Group')}</strong><small>Read-only bridge. Operating-company system-of-record boundaries remain intact.</small></section>
       <section class="kb-lr-card"><div class="eyebrow">COMPANIES</div><div class="kb-chip-cloud">${list(companies)}</div></section>
       <section class="kb-lr-card"><div class="eyebrow">SHARED DEPARTMENTS</div><div class="kb-mini-list">${departments.map(d=>`<div><b>${esc(d.name)}</b><small>${esc(d.mission)}</small></div>`).join('')}</div></section>
       <section class="kb-lr-card"><div class="eyebrow">OWNER DESKS</div><div class="kb-mini-list">${desks.map(d=>`<div><b>${esc(d.name)}</b><small>${esc(d.mission)}</small></div>`).join('')}</div></section>
       <section class="kb-lr-card"><div class="eyebrow">PROVIDERS</div><div class="kb-chip-cloud">${list(providers)}</div></section>
       <section class="kb-lr-card"><div class="eyebrow">DISTRIBUTION</div><div class="kb-chip-cloud">${list(platforms)}</div></section>
       <section class="kb-lr-card"><div class="eyebrow">SOURCE MODULES</div><div class="kb-chip-cloud dense">${list(LR.modules||[])}</div></section>
       <section class="kb-lr-card"><div class="eyebrow">GOVERNANCE</div><div class="kb-mini-list"><div><b>Autonomous spend</b><small>₹${esc(LR.governance?.autonomousSpendInr ?? 0)}</small></div><div><b>Owner-only gates</b><small>${esc((LR.governance?.ownerOnlyActions||[]).join(' · '))}</small></div></div></section>
       <section class="kb-lr-card wide"><div class="eyebrow">LIVE READ STATUS</div><pre>${esc(JSON.stringify(live,null,2))}</pre></section>
      </div>`;
  }

  function browserMarkup(){
    return `<aside id="kbBrowserDrawer" class="kb-browser-drawer" aria-label="Garudanetra browser">
      <div class="kb-browser-head"><div><small>SUDARSHAN TOOL</small><strong>GARUDANETRA BROWSER</strong></div><button id="kbBrowserClose" type="button">×</button></div>
      <div class="kb-browser-address"><button data-bact="back" title="Back">←</button><button data-bact="forward" title="Forward">→</button><button data-bact="reload" title="Reload">↻</button><input id="kbBrowserUrl" value="https://www.google.com" spellcheck="false" aria-label="Browser URL"><select id="kbBrowserMode" aria-label="Browser mode"><option value="private">Private</option><option value="task_memory">Task memory</option></select><button id="kbBrowserGo" type="button">Go</button></div>
      <div class="kb-browser-sessionbar"><select id="kbBrowserSessions" aria-label="Browser sessions"><option value="">No session</option></select><span id="kbBrowserState">CHECKING</span><button data-bact="takeover" type="button">Take over</button><button data-bact="resume" type="button">Resume</button><button data-bact="stop" type="button">Stop</button></div>
      <div class="kb-browser-frame"><img id="kbBrowserFrame" alt="Live Garudanetra browser frame"><div id="kbBrowserEmpty">Start or select a Garudanetra session.</div></div>
      <div class="kb-browser-foot"><span id="kbBrowserMeta">Playwright canonical · backend-enforced authority</span><button id="kbBrowserRefresh" type="button">Refresh</button></div>
    </aside>`;
  }

  function addBrowserDrawer(){
    const sudarshan=$('sudarshan'), bar=qs('.sudarshanBar',sudarshan); if(!sudarshan||!bar) return;
    if(!$('kbBrowserToggle')){
      const toggle=document.createElement('button'); toggle.id='kbBrowserToggle'; toggle.className='ghost kb-browser-toggle'; toggle.type='button';
      toggle.innerHTML='<span>◉</span> Browser';
      const spacer=qs('.spacer',bar); bar.insertBefore(toggle,spacer||null);
      toggle.onclick=()=>setBrowserOpen(!state.browserOpen);
    }
    if(!$('kbBrowserDrawer')){
      sudarshan.insertAdjacentHTML('beforeend',browserMarkup());
      $('kbBrowserClose').onclick=()=>setBrowserOpen(false);
      $('kbBrowserRefresh').onclick=refreshBrowserSessions;
      $('kbBrowserGo').onclick=startOrNavigateBrowser;
      $('kbBrowserUrl').addEventListener('keydown',e=>{if(e.key==='Enter')startOrNavigateBrowser();});
      $('kbBrowserSessions').onchange=e=>{state.browserSession=e.target.value;refreshBrowserSession();};
      qsa('[data-bact]',$('kbBrowserDrawer')).forEach(button=>button.onclick=()=>browserAction(button.dataset.bact));
    }
  }
  function setBrowserOpen(open){
    state.browserOpen=Boolean(open);
    $('kbBrowserDrawer')?.classList.toggle('open',state.browserOpen);
    $('kbBrowserToggle')?.classList.toggle('active',state.browserOpen);
    if(state.browserOpen) refreshBrowserSessions();
  }
  async function refreshBrowserSessions(){
    const stateEl=$('kbBrowserState');
    try{
      const fabric=await json('/api/garudanetra/fabric');
      const sessions=await json('/api/garudanetra/sessions');
      const rows=sessions.sessions||[];
      const select=$('kbBrowserSessions');
      if(select){
        const previous=state.browserSession;
        select.innerHTML='<option value="">No session</option>'+rows.map(s=>`<option value="${esc(s.session_id)}">${esc((s.title||s.current_url||s.requested_url||'Session').slice(0,65))} · ${esc(s.state)}</option>`).join('');
        if(previous && rows.some(s=>s.session_id===previous)){select.value=previous;}
        else if(rows[0]){state.browserSession=rows[0].session_id;select.value=state.browserSession;}
      }
      if(stateEl) stateEl.textContent=`${esc(fabric.canonical_engine||'playwright').toUpperCase()} · ${rows.length} SESSION${rows.length===1?'':'S'}`;
      await refreshBrowserSession();
    }catch(error){if(stateEl)stateEl.textContent='BACKEND UNAVAILABLE';const empty=$('kbBrowserEmpty');if(empty)empty.textContent=error.message;}
  }
  async function startOrNavigateBrowser(){
    let url=String($('kbBrowserUrl')?.value||'').trim(); if(!/^https?:\/\//i.test(url))url='https://'+url;
    const mode=$('kbBrowserMode')?.value||'private';
    try{
      if(state.browserSession){
        await browserControl('navigate',{url});
      }else{
        const row=await json('/api/garudanetra/session/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:'KRISHNA',url,mode})});
        state.browserSession=row.session_id||'';
      }
      await refreshBrowserSessions();
    }catch(error){const empty=$('kbBrowserEmpty');if(empty)empty.textContent=error.message;}
  }
  async function browserControl(action,payload={}){
    if(!state.browserSession) throw new Error('No Garudanetra session selected.');
    return json('/api/garudanetra/session/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:state.browserSession,action,payload})});
  }
  async function browserAction(action){
    try{await browserControl(action);if(action==='stop')state.browserSession='';await refreshBrowserSessions();}
    catch(error){const empty=$('kbBrowserEmpty');if(empty)empty.textContent=error.message;}
  }
  async function refreshBrowserSession(){
    const image=$('kbBrowserFrame'), empty=$('kbBrowserEmpty'), meta=$('kbBrowserMeta');
    if(!state.browserSession){if(image){image.removeAttribute('src');image.hidden=true;}if(empty){empty.hidden=false;empty.textContent='Start or select a Garudanetra session.';}return;}
    try{
      const session=await json('/api/garudanetra/session?id='+encodeURIComponent(state.browserSession));
      if($('kbBrowserUrl') && session.current_url) $('kbBrowserUrl').value=session.current_url;
      if(meta) meta.textContent=`${session.state} · ${session.mode} · ${session.stream_mode||'frame'} · ${session.title||session.current_url||''}`;
      if(session.frame_available){
        if(image){image.hidden=false;image.src='/api/garudanetra/frame?id='+encodeURIComponent(state.browserSession)+'&t='+Date.now();}
        if(empty)empty.hidden=true;
      }else{if(image)image.hidden=true;if(empty){empty.hidden=false;empty.textContent=session.last_error||`${session.state} · waiting for rendered frame`;}}
    }catch(error){if(empty){empty.hidden=false;empty.textContent=error.message;}}
  }

  function fixCustomNavigation(){
    const original=window.showView;
    if(typeof original==='function' && !original.__ownerWrapped){
      const wrapped=function(id){
        const result=original(id);
        const composer=qs('.composerWrap'); if(composer) composer.style.display=id==='sudarshan'?'block':'none';
        if(id==='lrUniverse') setTimeout(refreshLR,0);
        if(id!=='sudarshan') setBrowserOpen(false);
        return result;
      };
      wrapped.__ownerWrapped=true; window.showView=wrapped;
    }
    [$('kbNavLR'),$('kbNavBrahmand')].forEach(button=>{
      if(!button||button.dataset.ownerHook==='1')return;
      button.dataset.ownerHook='1';
      button.addEventListener('click',()=>{const composer=qs('.composerWrap');if(composer)composer.style.display='none';if(button.id==='kbNavLR')setTimeout(refreshLR,30);});
    });
  }

  function install(){
    fixMenu(); compactStatus(); addCustomToolbar(); addBrowserDrawer(); fixCustomNavigation(); refreshTelemetry();
    setInterval(refreshTelemetry,5000);
    setInterval(()=>{if(state.browserOpen)refreshBrowserSession();},1300);
    window.KRISHNA_OWNER_UI={refreshLR,refreshBrowserSessions,setBrowserOpen};
  }

  let attempts=0;
  const timer=setInterval(()=>{
    attempts++;
    if($('kbNavBrahmand') && $('sudarshan') && $('brahmand')){clearInterval(timer);install();}
    else if(attempts>80)clearInterval(timer);
  },50);
})();
