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
