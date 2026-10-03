/* KRISHNA Mobile resilient transport state machine.
   Native Android bridge performs network I/O off the WebView thread.
   A synchronous compatibility path remains for non-Android harnesses. */
class KrishnaRealtime {
  constructor(api){
    this.api=api;this.seq=Number(localStorage.getItem('krishna_seq')||0);
    this.attempt=0;this.maxAttempts=12;this.timer=null;this.connected=false;this.inflight=false;
  }
  backoff(){const cap=Math.min(500*Math.pow(2,this.attempt++),30000);return Math.floor(cap*(.5+Math.random()*.5))}
  start(){
    this.stop();
    window.onKrishnaRealtimeResult=(raw)=>this.accept(raw);
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
      for(const e of (r.events||[])){this.seq=Math.max(this.seq,Number(e.seq||0));this.onEvent?.(e)}
      localStorage.setItem('krishna_seq',String(this.seq));
      this.schedule(3000);
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

/* LR Mail owner view. This UI is deliberately read-only. Mail creation,
   sending, deletion and mailbox administration never enter KRISHNA Mobile. */
(()=>{
  const escapeHtml=(value)=>String(value??'').replace(/[&<>"']/g,(c)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const parse=(raw)=>{try{return typeof raw==='string'?JSON.parse(raw):raw}catch(_){return {error:'invalid response'}}};
  const address=(rows)=>Array.isArray(rows)&&rows.length?String(rows[0]?.email||rows[0]?.name||''):'';
  let selectedId='';

  function ensureUi(){
    if(document.getElementById('lrMailPanel'))return;
    const style=document.createElement('style');
    style.textContent=`
      .lrMailPanel{position:absolute;inset:max(10px,env(safe-area-inset-top)) 10px calc(max(10px,env(safe-area-inset-bottom)) + 8px);z-index:60;display:none;flex-direction:column;background:#03111bf7;border:1px solid #5ad9ea66;border-radius:22px;box-shadow:0 22px 60px #000d;backdrop-filter:blur(18px);overflow:hidden}
      .lrMailPanel.open{display:flex}.lrMailHead{display:flex;align-items:center;gap:9px;padding:12px;border-bottom:1px solid #5ad9ea33}.lrMailHead strong{flex:1;color:#f2c96f;letter-spacing:1.5px}.lrMailHead button,.lrMailToolbar button{border:1px solid #4b9eb2;background:#082535;color:#e9fbff;border-radius:10px;min-height:34px;padding:0 10px}
      .lrMailToolbar{display:flex;gap:7px;padding:9px 12px;border-bottom:1px solid #5ad9ea22;align-items:center}.lrMailToolbar input{min-width:0;flex:1;border:1px solid #315b69;border-radius:10px;background:#061923;color:#fff;padding:9px}
      .lrMailStats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;padding:9px 12px}.lrMailStat{background:#092431;border:1px solid #315b69;border-radius:12px;padding:8px;text-align:center}.lrMailStat b{display:block;font-size:16px;color:#9defff}.lrMailStat span{font-size:8px;color:#93b5c0;letter-spacing:.6px}
      .lrMailBody{display:grid;grid-template-columns:minmax(0,1fr);flex:1;min-height:0}.lrMailList{overflow:auto;padding:8px}.lrMailItem{width:100%;text-align:left;border:1px solid #234b59;background:#061a25;color:#e9fbff;border-radius:12px;padding:9px;margin-bottom:7px}.lrMailItem.unread{border-color:#54ddec}.lrMailItem b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.lrMailMeta{font-size:9px;color:#84aab8;margin-top:4px}.lrMailPreview{font-size:10px;color:#bcd6df;margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.lrMailRoute{font-size:9px;color:#f2c96f;margin-top:5px}.lrMailEmpty{padding:20px;text-align:center;color:#83a9b6}
      .lrMailDetail{position:absolute;inset:64px 8px 8px;z-index:2;display:none;flex-direction:column;background:#04141efc;border:1px solid #4b9eb2;border-radius:16px;overflow:hidden}.lrMailDetail.open{display:flex}.lrMailDetailHead{padding:11px;border-bottom:1px solid #345b68;display:flex;gap:8px}.lrMailDetailHead button{border:1px solid #4b9eb2;background:#082535;color:#fff;border-radius:9px}.lrMailDetailContent{overflow:auto;padding:12px;white-space:pre-wrap;font-size:12px;line-height:1.5}.lrMailSubject{font-size:16px;font-weight:800;color:#fff;margin-bottom:8px}.lrMailSecurity{font-size:9px;color:#6fa0ad;padding:0 12px 9px;text-align:center}
      .quickBtn.mail{border-color:#9defff88;color:#9defff}
    `;
    document.head.appendChild(style);

    const panel=document.createElement('section');
    panel.id='lrMailPanel';panel.className='lrMailPanel';panel.setAttribute('aria-label','LR Mail owner view');
    panel.innerHTML=`
      <div class="lrMailHead"><strong>LR MAIL · READ ONLY</strong><button id="lrMailRefresh" type="button">REFRESH</button><button id="lrMailClose" type="button">×</button></div>
      <div class="lrMailToolbar"><input id="lrMailSearch" type="search" placeholder="Search LR mail"><button id="lrMailSearchBtn" type="button">SEARCH</button></div>
      <div id="lrMailStats" class="lrMailStats"></div>
      <div class="lrMailBody"><div id="lrMailList" class="lrMailList"><div class="lrMailEmpty">Open Mail to load LR messages.</div></div></div>
      <div id="lrMailDetail" class="lrMailDetail"><div class="lrMailDetailHead"><button id="lrMailBack" type="button">←</button><strong style="flex:1">MESSAGE</strong></div><div id="lrMailDetailContent" class="lrMailDetailContent"></div></div>
      <div class="lrMailSecurity">Paired KRISHNA device · LR read gateway · no send/delete/admin controls</div>`;
    document.querySelector('.app')?.appendChild(panel);

    const dock=document.querySelector('.quickDock');
    if(dock&&!document.getElementById('mailQuick')){
      const button=document.createElement('button');
      button.id='mailQuick';button.className='quickBtn mail';button.type='button';button.textContent='✉';button.setAttribute('aria-label','Open LR Mail');
      button.onclick=()=>openLrMail();
      const chat=document.getElementById('chatQuick');dock.insertBefore(button,chat||null);
    }
    document.getElementById('lrMailClose').onclick=closeLrMail;
    document.getElementById('lrMailBack').onclick=()=>document.getElementById('lrMailDetail').classList.remove('open');
    document.getElementById('lrMailRefresh').onclick=()=>refreshLrMail('');
    document.getElementById('lrMailSearchBtn').onclick=()=>refreshLrMail(document.getElementById('lrMailSearch').value);
    document.getElementById('lrMailSearch').addEventListener('keydown',(e)=>{if(e.key==='Enter')refreshLrMail(e.target.value)});
  }

  function renderStats(data){
    const el=document.getElementById('lrMailStats');if(!el)return;
    const values=[['UNREAD',data?.unread||0],['TOTAL',data?.providerTotal??data?.total??0],['ESCALATED',data?.escalated||0],['HIGH',data?.highPriority||0]];
    el.innerHTML=values.map(([label,value])=>`<div class="lrMailStat"><b>${escapeHtml(value)}</b><span>${label}</span></div>`).join('');
  }

  function renderList(data){
    const el=document.getElementById('lrMailList');if(!el)return;
    if(data?.error){el.innerHTML=`<div class="lrMailEmpty">${escapeHtml(data.error)}</div>`;return}
    const rows=Array.isArray(data?.messages)?data.messages:[];
    if(!rows.length){el.innerHTML='<div class="lrMailEmpty">No messages found.</div>';return}
    el.innerHTML=rows.map((m)=>{
      const company=m?.route?.company?.companyName||'Unassigned';
      const queue=m?.route?.queue||'mail';
      return `<button class="lrMailItem ${m.unread?'unread':''}" data-mail-id="${escapeHtml(m.id)}">
        <b>${escapeHtml(m.subject||'(no subject)')}</b>
        <div class="lrMailMeta">${escapeHtml(address(m.from))} · ${escapeHtml(m.receivedAt||'')}</div>
        <div class="lrMailPreview">${escapeHtml(m.preview||'')}</div>
        <div class="lrMailRoute">${escapeHtml(company)} · ${escapeHtml(queue)}${m.escalated?' · ESCALATED':''}</div>
      </button>`;
    }).join('');
    el.querySelectorAll('[data-mail-id]').forEach((button)=>button.onclick=()=>loadLrMailMessage(button.dataset.mailId));
  }

  function bodyText(message){
    const values=message?.bodyValues&&typeof message.bodyValues==='object'?Object.values(message.bodyValues):[];
    const joined=values.map((v)=>v?.value||'').filter(Boolean).join('\n\n');
    return joined||message?.preview||'';
  }

  function renderDetail(message){
    const detail=document.getElementById('lrMailDetail'),content=document.getElementById('lrMailDetailContent');if(!detail||!content)return;
    if(message?.error){content.textContent=message.error;detail.classList.add('open');return}
    const route=message?.route||{},company=route?.company?.companyName||'Unassigned';
    content.innerHTML=`<div class="lrMailSubject">${escapeHtml(message?.subject||'(no subject)')}</div>
      <div><b>From:</b> ${escapeHtml(address(message?.from))}</div>
      <div><b>To:</b> ${escapeHtml(address(message?.to))}</div>
      <div><b>Received:</b> ${escapeHtml(message?.receivedAt||'')}</div>
      <div><b>Route:</b> ${escapeHtml(company)} · ${escapeHtml(route?.queue||'mail')} · ${escapeHtml(route?.intent||'')}</div>
      <hr style="border:0;border-top:1px solid #345b68;margin:12px 0">
      <div>${escapeHtml(bodyText(message))}</div>`;
    detail.classList.add('open');
  }

  function refreshLrMail(text=''){
    ensureUi();
    document.getElementById('lrMailList').innerHTML='<div class="lrMailEmpty">Loading…</div>';
    try{
      if(!window.Krishna||typeof Krishna.lrMailSummaryAsync!=='function')throw new Error('Update KRISHNA Mobile/Core to enable LR Mail.');
      Krishna.lrMailSummaryAsync(100);
      Krishna.lrMailListAsync(50,0,String(text||''));
    }catch(error){renderList({error:String(error?.message||error)})}
  }

  function loadLrMailMessage(id){
    selectedId=String(id||'');if(!selectedId)return;
    const detail=document.getElementById('lrMailDetail'),content=document.getElementById('lrMailDetailContent');
    detail?.classList.add('open');if(content)content.textContent='Loading message…';
    try{Krishna.lrMailMessageAsync(selectedId)}catch(error){renderDetail({error:String(error?.message||error)})}
  }

  function openLrMail(){ensureUi();document.getElementById('lrMailPanel').classList.add('open');refreshLrMail('')}
  function closeLrMail(){document.getElementById('lrMailPanel')?.classList.remove('open');document.getElementById('lrMailDetail')?.classList.remove('open')}

  window.openLrMail=openLrMail;
  window.closeLrMail=closeLrMail;
  window.onLrMailSummary=(raw)=>renderStats(parse(raw));
  window.onLrMailList=(raw)=>renderList(parse(raw));
  window.onLrMailMessage=(raw)=>renderDetail(parse(raw));
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ensureUi,{once:true});else ensureUi();
})();
