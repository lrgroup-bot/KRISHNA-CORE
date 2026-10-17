/* KRISHNA Mobile resilient transport state machine.
   Native Android bridge performs network I/O off the WebView thread.
   A synchronous compatibility path remains for non-Android harnesses.

   Mobile shell policy:
   - KRISHNA remains the primary screen.
   - Main navigation is symbol-only.
   - Sudarshan owns persistent/dynamic conversation rooms and unread counters.
   - Hawkeye is a top symbol beside notifications, not a large standalone button.
   - Brahmand is one compact PC-pipeline/status surface instead of many buttons.
   - Realtime Core events are mirrored into Sudarshan as durable mobile notices.
*/
class KrishnaRealtime {
  constructor(api){
    this.api=api;this.seq=Number(localStorage.getItem('krishna_seq')||0);
    this.attempt=0;this.maxAttempts=12;this.timer=null;this.connected=false;this.inflight=false;
  }
  backoff(){const cap=Math.min(500*Math.pow(2,this.attempt++),30000);return Math.floor(cap*(.5+Math.random()*.5))}
  start(){
    this.stop();
    window.onKrishnaRealtimeResult=(raw)=>this.accept(raw);
    if(!this._visibilityBound){
      this._visibilityBound=true;
      document.addEventListener('visibilitychange',()=>{
        if(!document.hidden){this.attempt=0;this.sync()}
      });
    }
    this.sync();
  }
  stop(){if(this.timer)clearTimeout(this.timer);this.timer=null;this.inflight=false}
  schedule(ms){if(this.timer)clearTimeout(this.timer);this.timer=setTimeout(()=>this.sync(),ms)}
  accept(raw){
    this.inflight=false;
    try{
      const r=typeof raw==='string'?JSON.parse(raw):raw;
      if(!r||r.error)throw new Error(r&&r.error||'resume failed');
      this.connected=true;this.attempt=0;
      for(const e of (r.events||[])){
        this.seq=Math.max(this.seq,Number(e.seq||0));
        try{window.onSudarshanRealtimeEvent?.(e)}catch(_){}
        this.onEvent?.(e);
      }
      localStorage.setItem('krishna_seq',String(this.seq));
      this.schedule(document.hidden?60000:15000);
    }catch(e){
      this.connected=false;
      if(this.attempt>=this.maxAttempts){this.onState?.('disconnected');return}
      this.onState?.('reconnecting');this.schedule(this.backoff());
    }
  }
  sync(){
    if(this.inflight)return;
    this.inflight=true;
    try{
      if(this.api&&typeof this.api.resumeAsync==='function'){
        this.api.resumeAsync(this.seq);
        return;
      }
      const raw=this.api.resume(this.seq);
      this.accept(raw);
    }catch(e){
      this.inflight=false;this.connected=false;
      if(this.attempt>=this.maxAttempts){this.onState?.('disconnected');return}
      this.onState?.('reconnecting');this.schedule(this.backoff());
    }
  }
}

(()=>{
  const STORE='krishna_sudarshan_mobile_v1';
  const MAX_MESSAGES=160;
  const PERMANENT=[
    ['krishna','KRISHNA','conversation'],
    ['meetings','Meetings','meeting'],
    ['projects','Projects','project'],
    ['tasks','Tasks','task'],
    ['hawkeye','Hawkeye','hawkeye'],
    ['brahmand','Brahmand','pipeline'],
    ['notifications','Notifications','notification']
  ];

  const esc=(value)=>String(value??'').replace(/[&<>"']/g,c=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
  const now=()=>Date.now();
  const parse=(raw,fallback={})=>{try{return JSON.parse(String(raw||''))}catch(_){return fallback}};
  const textOf=(value)=>{
    if(value===null||value===undefined)return'';
    if(typeof value==='string')return value;
    try{return JSON.stringify(value)}catch(_){return String(value)}
  };
  const trim=(value,n=180)=>{const s=textOf(value).replace(/\s+/g,' ').trim();return s.length>n?s.slice(0,n-1)+'…':s};

  class SudarshanMobileShell{
    constructor(api){
      this.api=api;
      this.state=this.load();
      this.active=this.state.active||'krishna';
      this.threadView=false;
      this.sheet=null;
      this.brahmand=null;
      this.messageList=null;
      this.roomList=null;
      this.titleNode=null;
      this.composerHost=null;
      this.sudarshanBadge=null;
      this.notificationBadge=null;
      this.voiceNotice='';
      this.installed=false;
      this.ensurePermanent();
    }

    load(){
      const data=parse(localStorage.getItem(STORE),{});
      return data&&typeof data==='object'?data:{threads:{},order:[],active:'krishna'};
    }
    save(){
      this.state.active=this.active;
      try{localStorage.setItem(STORE,JSON.stringify(this.state))}catch(_){}
    }
    ensurePermanent(){
      if(!this.state.threads||typeof this.state.threads!=='object')this.state.threads={};
      if(!Array.isArray(this.state.order))this.state.order=[];
      for(const [id,title,kind] of PERMANENT){
        if(!this.state.threads[id])this.state.threads[id]={id,title,kind,pinned:true,unread:0,updated:now(),messages:[]};
        if(!this.state.order.includes(id))this.state.order.push(id);
      }
      this.save();
    }
    thread(id){return this.state.threads[id]||null}
    createThread(id,title,kind='activity',pinned=false){
      id=String(id||'').trim()||('chat-'+now());
      if(!this.state.threads[id]){
        this.state.threads[id]={id,title:trim(title||'New chat',64),kind,pinned:!!pinned,unread:0,updated:now(),messages:[]};
        this.state.order.unshift(id);
      }else if(title){
        this.state.threads[id].title=trim(title,64);
      }
      this.save();
      return this.state.threads[id];
    }
    addMessage(threadId,role,text,meta={}){
      const t=this.thread(threadId)||this.createThread(threadId,threadId,'activity');
      const clean=String(text||'').trim();if(!clean)return;
      const previous=t.messages[t.messages.length-1];
      if(previous&&previous.role===role&&previous.text===clean&&now()-Number(previous.at||0)<5000)return;
      t.messages.push({role,text:clean,at:now(),meta:meta||{}});
      if(t.messages.length>MAX_MESSAGES)t.messages.splice(0,t.messages.length-MAX_MESSAGES);
      t.updated=now();
      const visible=this.sheet?.classList.contains('open')&&this.threadView&&this.active===threadId;
      if(!visible&&role!=='user')t.unread=Math.min(999,Number(t.unread||0)+1);
      this.save();
      this.renderBadges();
      if(visible)this.renderMessages();
    }
    clearUnread(id){
      const t=this.thread(id);if(!t)return;t.unread=0;t.updated=now();this.save();this.renderBadges();this.renderRooms();
    }
    unreadNotifications(){return Number(this.thread('notifications')?.unread||0)}

    installStyle(){
      if(document.getElementById('krishnaSymbolShellStyle'))return;
      const style=document.createElement('style');style.id='krishnaSymbolShellStyle';
      style.textContent=`
        .quickDock{display:none!important}
        .krishnaTopSymbols{position:absolute;z-index:30;top:max(8px,env(safe-area-inset-top));left:8px;right:8px;height:44px;display:flex;align-items:center;gap:6px;padding:4px 6px;border:1px solid #70dded26;border-radius:24px;background:#020b12a8;backdrop-filter:blur(14px);box-shadow:0 8px 28px #0006}
        .krishnaTopSymbols .symbolSpacer{flex:1}
        .krishnaSymbol{position:relative;width:34px;height:34px;border:0!important;border-radius:50%;display:grid;place-items:center;padding:0;background:transparent!important;color:#dffaff;font-size:19px;line-height:1;box-shadow:none!important;outline:none}
        .krishnaSymbol:active{background:#123849aa!important;transform:scale(.94)}
        .krishnaSymbol.om{font-family:Georgia,serif;color:#f2c96f;font-size:24px;text-shadow:0 0 14px #f2c96f66}
        .krishnaSymbol.sudarshan{color:#7defff;font-size:21px}.krishnaSymbol.brahmand{color:#a8bfff}.krishnaSymbol.hawkeye{color:#f2c96f}.krishnaSymbol.voice{color:#65f0b0}
        .symbolBadge{position:absolute;right:-2px;top:-3px;display:none;min-width:16px;height:16px;padding:0 4px;border-radius:9px;background:#ff526f;color:#fff;font:800 9px/16px Arial;text-align:center;border:1px solid #020914}
        .symbolBadge.visible{display:block}
        .sudarshanSheet,.brahmandSheet{position:absolute;z-index:25;left:8px;right:8px;top:max(58px,calc(env(safe-area-inset-top) + 54px));bottom:max(8px,env(safe-area-inset-bottom));display:none;overflow:hidden;border:1px solid #54d8e955;border-radius:22px;background:#02101bea;backdrop-filter:blur(18px);box-shadow:0 24px 54px #000c}
        .sudarshanSheet.open,.brahmandSheet.open{display:flex;flex-direction:column}
        .sheetBar{height:48px;display:flex;align-items:center;gap:8px;padding:6px 9px;border-bottom:1px solid #6adceb24}
        .sheetBarTitle{min-width:0;flex:1;font-size:13px;font-weight:800;letter-spacing:.8px;color:#dffaff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .sheetIcon{width:34px;height:34px;border:0;border-radius:50%;background:#082536;color:#dffaff;font-size:18px}
        .roomList{flex:1;overflow:auto;padding:7px}
        .roomRow{width:100%;display:grid;grid-template-columns:36px minmax(0,1fr) auto;gap:9px;align-items:center;border:0;background:transparent;color:#e9fbff;text-align:left;padding:9px 7px;border-radius:14px}
        .roomRow:active{background:#0a2d3d}.roomGlyph{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#092637;border:1px solid #57cddd38;color:#9cefff;font-size:16px}
        .roomName{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.roomPreview{margin-top:3px;font-size:10px;color:#7ca4b3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.roomUnread{min-width:20px;height:20px;border-radius:10px;padding:0 6px;background:#ff526f;color:#fff;font:800 10px/20px Arial;text-align:center}.roomUnread.zero{visibility:hidden}
        .threadPane{display:none;flex:1;min-height:0;flex-direction:column}.sudarshanSheet.thread .roomList{display:none}.sudarshanSheet.thread .threadPane{display:flex}
        .threadMessages{flex:1;overflow:auto;padding:10px 10px 5px;display:flex;flex-direction:column;gap:7px}
        .threadMessage{max-width:88%;padding:8px 10px;border-radius:15px;font-size:12px;line-height:1.4;white-space:pre-wrap;overflow-wrap:anywhere}.threadMessage.user{align-self:flex-end;background:#0e566b;color:#fff;border-bottom-right-radius:4px}.threadMessage.assistant{align-self:flex-start;background:#071f2c;color:#dffaff;border-bottom-left-radius:4px}.threadMessage.event{align-self:stretch;max-width:100%;background:#161c2a;color:#bcd2df;border:1px solid #53697a3d;font-size:10px}.threadTime{display:block;margin-top:3px;font-size:8px;color:#75929e}
        .sudarshanComposer{padding:7px 8px 9px;border-top:1px solid #5bdff028;background:#020b12cc}.sudarshanComposer .composer{display:grid!important;position:static!important;margin:0!important}.sudarshanComposer .security{display:none!important}
        #chatSheet{display:none!important}
        .brahmandBody{flex:1;overflow:auto;padding:9px;display:grid;grid-template-columns:1fr;gap:8px}.brahmandCard{border:1px solid #476b8a45;border-radius:15px;background:#061824cc;padding:9px}.brahmandCardTitle{font-size:9px;letter-spacing:1.2px;color:#f2c96f;margin-bottom:6px}.brahmandCardBody{font-size:10px;line-height:1.45;color:#cde8f0;white-space:pre-wrap;overflow-wrap:anywhere}.pipelineCloud{display:flex;flex-wrap:wrap;gap:6px}.pipelineChip{padding:6px 8px;border-radius:12px;border:1px solid #506b7c55;background:#071d28;color:#bcebf4;font-size:9px}.voiceQuietState{color:#7ea0ad;font-size:9px;padding:5px 10px;text-align:center}
        .gitaControls button{font-size:0!important;width:34px!important;min-width:34px!important;padding:0!important;border-radius:50%!important}.gitaControls button:nth-child(1)::after{content:'▶';font-size:13px}.gitaControls button:nth-child(2)::after{content:'↻';font-size:15px}.gitaControls button:nth-child(3)::after{content:'✧';font-size:15px}
        @media (min-width:720px){.sudarshanSheet,.brahmandSheet{left:50%;right:auto;width:min(620px,94vw);transform:translateX(-50%)}.brahmandBody{grid-template-columns:1fr 1fr}}
      `;
      document.head.appendChild(style);
    }

    symbol(id,glyph,label,cls='',handler=null,badge=false){
      const b=document.createElement('button');b.type='button';b.id=id;b.className=('krishnaSymbol '+cls).trim();b.textContent=glyph;b.setAttribute('aria-label',label);b.title=label;
      if(handler)b.addEventListener('click',handler);
      if(badge){const s=document.createElement('span');s.className='symbolBadge';s.setAttribute('aria-hidden','true');b.appendChild(s)}
      return b;
    }

    install(){
      if(this.installed)return;this.installed=true;this.installStyle();
      const stage=document.getElementById('stage');if(!stage)return;
      document.querySelector('.quickDock')?.setAttribute('aria-hidden','true');

      const bar=document.createElement('nav');bar.className='krishnaTopSymbols';bar.setAttribute('aria-label','KRISHNA mobile symbols');
      bar.append(
        this.symbol('krishnaBackSymbol','‹','Back','back',()=>this.back()),
        this.symbol('krishnaOmSymbol','ॐ','KRISHNA home','om',()=>this.home()),
        this.symbol('krishnaSudarshanSymbol','✺','Sudarshan chats','sudarshan',()=>this.openSudarshan(),true),
        this.symbol('krishnaBrahmandSymbol','◎','Brahmand and PC pipelines','brahmand',()=>this.openBrahmand())
      );
      const spacer=document.createElement('span');spacer.className='symbolSpacer';bar.appendChild(spacer);
      const notice=this.symbol('krishnaNotificationSymbol','🔔','Notifications','notifications',()=>this.openSudarshan('notifications'),true);
      const hawkeye=this.symbol('krishnaHawkeyeSymbol','◉','Hawkeye camera','hawkeye',()=>this.openHawkeye());
      const voice=this.symbol('krishnaVoiceSymbol','◍','Talk to KRISHNA','voice',()=>this.openVoice());
      bar.append(notice,hawkeye,voice);stage.appendChild(bar);
      this.sudarshanBadge=bar.querySelector('#krishnaSudarshanSymbol .symbolBadge');
      this.notificationBadge=bar.querySelector('#krishnaNotificationSymbol .symbolBadge');

      this.buildSudarshan(stage);this.buildBrahmand(stage);this.moveComposer();this.wrapConversation();
      window.onSudarshanRealtimeEvent=(e)=>this.ingestEvent(e);
      window.krishnaBack=()=>this.back();
      window.openSudarshan=()=>this.openSudarshan();
      window.openBrahmand=()=>this.openBrahmand();
      window.toggleChat=(force)=>{if(force===false)this.closeSudarshan();else this.openSudarshan('krishna')};
      this.renderBadges();
    }

    buildSudarshan(stage){
      const sheet=document.createElement('section');sheet.id='sudarshanSheet';sheet.className='sudarshanSheet';sheet.setAttribute('aria-label','Sudarshan conversation center');
      sheet.innerHTML=`
        <div class="sheetBar">
          <button class="sheetIcon" id="sudarshanInnerBack" aria-label="Back">‹</button>
          <div class="sheetBarTitle" id="sudarshanTitle">SUDARSHAN</div>
          <button class="sheetIcon" id="sudarshanNew" aria-label="New chat">＋</button>
          <button class="sheetIcon" id="sudarshanClose" aria-label="Close">×</button>
        </div>
        <div class="roomList" id="sudarshanRooms"></div>
        <div class="threadPane">
          <div class="threadMessages" id="sudarshanMessages"></div>
          <div class="sudarshanComposer" id="sudarshanComposer"></div>
        </div>`;
      stage.appendChild(sheet);this.sheet=sheet;this.roomList=sheet.querySelector('#sudarshanRooms');this.messageList=sheet.querySelector('#sudarshanMessages');this.titleNode=sheet.querySelector('#sudarshanTitle');this.composerHost=sheet.querySelector('#sudarshanComposer');
      sheet.querySelector('#sudarshanInnerBack').onclick=()=>{if(this.threadView)this.showRoomList();else this.closeSudarshan()};
      sheet.querySelector('#sudarshanClose').onclick=()=>this.closeSudarshan();
      sheet.querySelector('#sudarshanNew').onclick=()=>this.newChat();
    }

    buildBrahmand(stage){
      const sheet=document.createElement('section');sheet.id='brahmandSheet';sheet.className='brahmandSheet';sheet.setAttribute('aria-label','Brahmand PC pipeline overview');
      sheet.innerHTML=`
        <div class="sheetBar">
          <button class="sheetIcon" id="brahmandBack" aria-label="Back">‹</button>
          <div class="sheetBarTitle">BRAHMAND · PC PIPELINE</div>
          <button class="sheetIcon" id="brahmandRefresh" aria-label="Refresh">↻</button>
          <button class="sheetIcon" id="brahmandClose" aria-label="Close">×</button>
        </div>
        <div class="brahmandBody" id="brahmandBody"></div>`;
      stage.appendChild(sheet);this.brahmand=sheet;
      sheet.querySelector('#brahmandBack').onclick=()=>this.closeBrahmand();sheet.querySelector('#brahmandClose').onclick=()=>this.closeBrahmand();sheet.querySelector('#brahmandRefresh').onclick=()=>this.refreshBrahmand();
    }

    moveComposer(){
      const original=document.getElementById('chatSheet');
      const composer=original?.querySelector('.composer');if(composer&&this.composerHost)this.composerHost.appendChild(composer);
      if(original)original.setAttribute('aria-hidden','true');
    }

    wrapConversation(){
      const self=this;
      const originalReply=window.reply;
      if(typeof originalReply==='function'){
        window.reply=function(text,cls=''){
          const value=String(text||'');
          if(/continuous\s+hot\s*-?word.*unavailable|one\s+session\s+at\s+a\s+time.*hot\s*-?word|continuous\s+hotword/i.test(value)){
            self.voiceNotice=value;return;
          }
          const result=originalReply.apply(this,arguments);
          if(!self.transient(value))self.addMessage(self.active||'krishna','assistant',value,{className:cls});
          return result;
        };
      }
      const originalSend=window.send;
      if(typeof originalSend==='function'){
        window.send=async function(){
          const input=document.getElementById('msg');const q=String(input?.value||'').trim();
          if(q)self.addMessage(self.active||'krishna','user',q,{source:'mobile'});
          return originalSend.apply(this,arguments);
        };
      }
    }

    transient(value){
      const s=String(value||'').trim();
      return !s||/^(KRISHNA is thinking|Attaching |Attached |Say “?Krishna|Owner voice gate|Voice gate|Camera session|Private PC link saved|Enable KRISHNA as your Android assistant)/i.test(s);
    }

    glyph(kind){return ({conversation:'ॐ',meeting:'◫',project:'◇',task:'✓',hawkeye:'◉',pipeline:'◎',notification:'🔔',activity:'•'})[kind]||'•'}
    preview(t){const m=t.messages?.[t.messages.length-1];return m?trim(m.text,74):'No messages yet'}
    renderRooms(){
      if(!this.roomList)return;
      const permanent=new Set(PERMANENT.map(x=>x[0]));
      const ids=[...this.state.order].filter(id=>this.thread(id)).sort((a,b)=>{
        const ap=permanent.has(a),bp=permanent.has(b);if(ap!==bp)return ap?-1:1;return Number(this.thread(b)?.updated||0)-Number(this.thread(a)?.updated||0)
      });
      this.roomList.innerHTML=ids.map(id=>{const t=this.thread(id),u=Number(t.unread||0);return `<button class="roomRow" data-room="${esc(id)}"><span class="roomGlyph">${esc(this.glyph(t.kind))}</span><span><div class="roomName">${esc(t.title)}</div><div class="roomPreview">${esc(this.preview(t))}</div></span><span class="roomUnread ${u?'':'zero'}">${u>99?'99+':u}</span></button>`}).join('');
      for(const row of this.roomList.querySelectorAll('[data-room]'))row.onclick=()=>this.openThread(row.dataset.room);
    }
    renderMessages(){
      const t=this.thread(this.active);if(!t||!this.messageList)return;
      this.titleNode.textContent=t.title;
      this.messageList.innerHTML=(t.messages||[]).map(m=>{const role=m.role==='user'?'user':(m.role==='event'?'event':'assistant');const ts=new Date(Number(m.at||now())).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});return `<div class="threadMessage ${role}">${esc(m.text)}<span class="threadTime">${esc(ts)}</span></div>`}).join('')||'<div class="voiceQuietState">No messages yet.</div>';
      this.messageList.scrollTop=this.messageList.scrollHeight;
      const input=document.getElementById('msg');if(input)input.placeholder='Message '+t.title+'…';
    }
    renderBadges(){
      const n=this.unreadNotifications();
      for(const badge of [this.sudarshanBadge,this.notificationBadge]){if(!badge)continue;badge.textContent=n>99?'99+':String(n);badge.classList.toggle('visible',n>0)}
    }

    openSudarshan(roomId=null){
      this.closeBrahmand();if(!this.sheet)return;this.sheet.classList.add('open');
      if(roomId)this.openThread(roomId);else{this.showRoomList();this.renderRooms()}
    }
    closeSudarshan(){if(!this.sheet)return;this.sheet.classList.remove('open','thread');this.threadView=false;this.active='krishna';this.save()}
    showRoomList(){if(!this.sheet)return;this.threadView=false;this.sheet.classList.remove('thread');this.titleNode.textContent='SUDARSHAN';this.renderRooms()}
    openThread(id){
      const t=this.thread(id);if(!t)return;this.active=id;this.threadView=true;this.sheet.classList.add('open','thread');this.clearUnread(id);this.renderMessages();this.save();setTimeout(()=>document.getElementById('msg')?.focus(),100)
    }
    newChat(){
      const title=prompt('Chat name');if(title===null)return;const name=String(title||'').trim();if(!name)return;
      const id='chat-'+now().toString(36);this.createThread(id,name,'conversation');this.openThread(id)
    }
    home(){
      this.closeBrahmand();this.closeSudarshan();
      if(document.getElementById('cameraLayer')?.classList.contains('active'))try{window.stopFieldScan?.()}catch(_){}
      try{window.setMode?.('FLUTE','Radhe Radhe. I am ready.')}catch(_){}
    }
    back(){
      if(document.getElementById('cameraLayer')?.classList.contains('active')){try{window.stopFieldScan?.();return}catch(_){}}
      if(this.brahmand?.classList.contains('open')){this.closeBrahmand();return}
      if(this.sheet?.classList.contains('open')){if(this.threadView){this.showRoomList();return}this.closeSudarshan();return}
      this.home();
    }
    openHawkeye(){this.closeBrahmand();this.closeSudarshan();try{window.startFieldScan?.('automatic live visual check',false)}catch(e){window.reply?.('Camera: '+e.message,'bad')}}
    openVoice(){this.closeBrahmand();this.closeSudarshan();try{window.listen?.()}catch(e){window.reply?.('Voice: '+e.message,'bad')}}

    safeCall(name){
      try{if(!this.api||typeof this.api[name]!=='function')return {available:false};const d=parse(this.api[name](),{});return d&&typeof d==='object'?d:{value:d}}catch(e){return {error:String(e&&e.message||e)}}
    }
    statusText(obj){
      if(!obj||typeof obj!=='object')return trim(obj,900)||'Unavailable';
      const copy={};
      for(const [k,v] of Object.entries(obj)){
        if(/token|secret|credential|authorization|password|api[_-]?key/i.test(k))continue;
        if(typeof v==='object'&&v!==null){const raw=trim(v,520);copy[k]=raw}else copy[k]=v;
        if(Object.keys(copy).length>=12)break;
      }
      try{return JSON.stringify(copy,null,2).slice(0,1900)}catch(_){return trim(obj,1900)}
    }
    openBrahmand(){this.closeSudarshan();if(!this.brahmand)return;this.brahmand.classList.add('open');this.refreshBrahmand()}
    closeBrahmand(){this.brahmand?.classList.remove('open')}
    refreshBrahmand(){
      const body=document.getElementById('brahmandBody');if(!body)return;
      const core=this.safeCall('status'),state=this.safeCall('state'),voice=this.safeCall('assistantStatus'),cloud=this.safeCall('mobileFreeCloudStatus'),hawkeye=this.safeCall('hawkeyeEvidenceStatus');
      const capabilities=['BRAHMAGYAN','SUDARSHAN','RISHI COUNCIL','NARAD','GARUDA / GARUDANETRA','KABACH','MRITYUNJAY','PROJECT / JOB PIPELINE','HAWKEYE SYNC'];
      body.innerHTML=`
        <div class="brahmandCard"><div class="brahmandCardTitle">PC CAPABILITY MAP</div><div class="pipelineCloud">${capabilities.map(x=>`<span class="pipelineChip">${esc(x)}</span>`).join('')}</div></div>
        <div class="brahmandCard"><div class="brahmandCardTitle">CORE</div><div class="brahmandCardBody">${esc(this.statusText(core))}</div></div>
        <div class="brahmandCard"><div class="brahmandCardTitle">CURRENT STATE / PIPELINE</div><div class="brahmandCardBody">${esc(this.statusText(state))}</div></div>
        <div class="brahmandCard"><div class="brahmandCardTitle">VOICE / ASSISTANT</div><div class="brahmandCardBody">${esc(this.statusText(voice))}${this.voiceNotice?'\n\n'+esc(this.voiceNotice):''}</div></div>
        <div class="brahmandCard"><div class="brahmandCardTitle">FREE CLOUD</div><div class="brahmandCardBody">${esc(this.statusText(cloud))}</div></div>
        <div class="brahmandCard"><div class="brahmandCardTitle">HAWKEYE SYNC</div><div class="brahmandCardBody">${esc(this.statusText(hawkeye))}</div></div>`;
    }

    eventKind(e){
      const type=String(e?.type||e?.kind||'').toLowerCase(),p=e?.payload||{};
      const hay=type+' '+String(p.kind||'')+' '+String(p.source||'')+' '+String(p.action||'');
      if(/meeting|calendar/.test(hay))return'meeting';if(/hawkeye|camera|bhumiputra/.test(hay))return'hawkeye';if(/task|mission|job/.test(hay))return'task';if(/project/.test(hay))return'project';if(/notification|alert|warning|critical/.test(hay))return'notification';return'pipeline';
    }
    eventTitle(e,kind){
      const p=e?.payload||{};return trim(p.title||p.name||p.task||p.summary||p.action||p.project||e?.type||kind,64)||kind;
    }
    eventThread(e,kind){
      const p=e?.payload||{};
      const stable=p.chat_id||p.meeting_id||p.task_id||p.mission_id||p.job_id||p.project_id||'';
      if(stable)return 'auto-'+kind+'-'+String(stable).replace(/[^a-zA-Z0-9_.-]/g,'_').slice(0,72);
      if(kind==='meeting')return'meetings';if(kind==='hawkeye')return'hawkeye';if(kind==='task')return'tasks';if(kind==='project')return'projects';if(kind==='notification')return'notifications';return'brahmand';
    }
    eventMessage(e){
      const p=e?.payload||{};return trim(p.summary||p.detail||p.message||p.status||p.action||e?.detail||e?.type||'KRISHNA event',700)
    }
    ingestEvent(e){
      if(!e||typeof e!=='object')return;const kind=this.eventKind(e),id=this.eventThread(e,kind),title=this.eventTitle(e,kind),message=this.eventMessage(e);
      if(!this.thread(id))this.createThread(id,title,kind,false);
      this.addMessage(id,'event',message,{eventType:e.type||'',seq:e.seq||0});
      if(id!=='notifications')this.addMessage('notifications','event',title+' · '+message,{target:id,eventType:e.type||'',seq:e.seq||0});
      this.renderRooms();
    }
  }

  const boot=()=>{
    if(window.sudarshanMobileShell)return;
    const shell=new SudarshanMobileShell(window.Krishna);
    window.sudarshanMobileShell=shell;shell.install();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(boot,0),{once:true});else setTimeout(boot,0);
})();
