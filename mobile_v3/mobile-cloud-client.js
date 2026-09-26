/* KRISHNA Mobile direct free-cloud conversation fabric.
   A permanent provider credential never enters the APK. The paired PC brokers
   one short-lived free-only token; eligible general chat then flows device ->
   provider directly until the socket ends. Private/action/stateful work falls
   back to KRISHNA Core. */
class KrishnaMobileCloudChat {
  constructor(api){
    this.api=api;this.ws=null;this.ready=null;this.pending=null;this.model='';
    this.provider='google-gemini-live';this.lastError='';this.turn=0;
    this.ephemeralToken='';this.tokenExpiresAt=0;this.resumeHandle='';
  }
  eligible(text,attachmentCount=0){
    const q=String(text||'').trim();
    if(!q||attachmentCount>0||q.length>5000)return false;
    const sensitive=/(password|passwd|\bpwd\b|api[ _-]?key|secret|token|authorization|aadhaar|aadhar|pan card|bank account|credit card|debit card|\botp\b|\bpin\b|medical record|diagnosis|prescription|private document|biometric|face embedding)/i;
    const action=/\b(implement|install|delete|remove|modify|edit|fix|repair|audit|deploy|restart|run|execute|commit|merge|push|pull|github|repository|repo|file|folder|email|gmail|calendar|slack|whatsapp|payment|pay|buy|purchase|spend|transfer|krishna project|kuber|manibhadra|narad|sudarshan|mrityunjay)\b/i;
    const stateful=/\b(gita|geeta|shloka|verse|my project|my file|my chat|remember|last time)\b/i;
    return !(sensitive.test(q)||action.test(q)||stateful.test(q));
  }
  status(){
    return {connected:!!(this.ws&&this.ws.readyState===WebSocket.OPEN),model:this.model,provider:this.provider,last_error:this.lastError,pc_per_turn:false,permanent_key_on_device:false,resumable:!!this.resumeHandle,token_persisted:false};
  }
  playAudio(parts){
    try{
      const chunks=(parts||[]).filter(x=>x&&x.data);if(!chunks.length)return false;
      let total=0;const decoded=chunks.map(x=>{const b=atob(x.data),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);total+=u.length;return u});
      const joined=new Uint8Array(total);let off=0;for(const u of decoded){joined.set(u,off);off+=u.length}
      const rateMatch=String(chunks[0].mimeType||'').match(/rate=(\d+)/i),rate=rateMatch?Number(rateMatch[1]):24000;
      const samples=Math.floor(joined.length/2),ctx=new (window.AudioContext||window.webkitAudioContext)();
      const buffer=ctx.createBuffer(1,samples,rate),channel=buffer.getChannelData(0),view=new DataView(joined.buffer,joined.byteOffset,joined.byteLength);
      for(let i=0;i<samples;i++)channel[i]=view.getInt16(i*2,true)/32768;
      const src=ctx.createBufferSource();src.buffer=buffer;src.connect(ctx.destination);src.onended=()=>{try{ctx.close()}catch(_){};try{window.onKrishnaCloudAudioEnd?.()}catch(_){}};src.start();return true;
    }catch(_){return false}
  }
  close(forgetSession=false){
    try{if(this.ws){this.ws.onclose=null;this.ws.close();}}catch(_){}
    this.ws=null;this.ready=null;
    if(forgetSession){this.ephemeralToken='';this.tokenExpiresAt=0;this.resumeHandle='';}
    if(this.pending){clearTimeout(this.pending.timer);this.pending.reject(new Error('free-cloud session closed'));this.pending=null;}
  }
  tokenUsable(){return !!(this.ephemeralToken&&this.resumeHandle&&Date.now()+15000<this.tokenExpiresAt)}
  async connect(){
    if(this.ws&&this.ws.readyState===WebSocket.OPEN&&this.ready)return this.ready;
    if(this.ready)return this.ready;
    this.ready=new Promise((resolve,reject)=>{
      let token;
      try{
        if(!this.api||typeof this.api.mobileFreeCloudSession!=='function')throw new Error('mobile free-cloud bridge unavailable');
        if(this.tokenUsable()){
          token={token:this.ephemeralToken,live_model:this.model,free_only:true,permanent_key_exposed:false,resumed:true};
        }else{
          token=JSON.parse(this.api.mobileFreeCloudSession('chat',JSON.stringify({
            cloud_approved:true,user_explicit:true,purpose:'chat',
            contains_credentials:false,contains_biometrics:false,private_document:false
          })));
          if(token.error)throw new Error(token.error);
          if(!token.free_only)throw new Error('provider session is not marked free-only');
          if(token.permanent_key_exposed)throw new Error('unsafe cloud token response');
          this.ephemeralToken=String(token.token||'');
          this.tokenExpiresAt=Date.parse(String(token.expires_at||''))||Date.now()+25*60*1000;
          if(!token.resumed)this.resumeHandle='';
        }
        this.model=String(token.live_model||this.model||'');
        const url='wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained?access_token='+encodeURIComponent(token.token);
        const ws=new WebSocket(url);this.ws=ws;
        let settled=false;
        const fail=(message)=>{
          this.lastError=String(message||'cloud session failed');
          if(!settled){settled=true;this.ready=null;reject(new Error(this.lastError));}
          this.close(false);
        };
        const startup=setTimeout(()=>fail('free-cloud setup timed out'),12000);
        ws.onopen=()=>{
          ws.send(JSON.stringify({setup:{
            model:'models/'+this.model,
            generationConfig:{responseModalities:['AUDIO'],temperature:0.3},outputAudioTranscription:{},
            sessionResumption:this.resumeHandle?{handle:this.resumeHandle}:{},
            contextWindowCompression:{slidingWindow:{}},
            systemInstruction:{parts:[{text:
              'You are KRISHNA Mobile free-cloud conversational helper. Answer general non-sensitive informational questions only. '+
              'You cannot see KRISHNA PC, local files, private memory, credentials, projects, connected accounts or tools. '+
              'Never claim to perform actions. If the request needs private state, files, purchases, account actions or system changes, say it requires KRISHNA PC escalation.'
            }]}
          }}));
        };
        ws.onmessage=e=>{
          try{
            const msg=JSON.parse(String(e.data||'{}'));
            const resume=msg.sessionResumptionUpdate||{};
            if(resume.resumable&&resume.newHandle)this.resumeHandle=String(resume.newHandle);
            if(msg.setupComplete&&!settled){clearTimeout(startup);settled=true;resolve(this.status());}
            const sc=msg.serverContent||{};
            if(this.pending){
              const transcript=String(sc.outputTranscription&&sc.outputTranscription.text||'');
              if(transcript)this.pending.parts.push(transcript);
              const parts=sc.modelTurn&&Array.isArray(sc.modelTurn.parts)?sc.modelTurn.parts:[];
              for(const p of parts){
                if(p&&p.text)this.pending.parts.push(String(p.text));
                if(p&&p.inlineData&&p.inlineData.data&&String(p.inlineData.mimeType||'').startsWith('audio/'))this.pending.audio.push(p.inlineData);
              }
              if(sc.turnComplete){
                const p=this.pending;this.pending=null;clearTimeout(p.timer);
                const text=p.parts.join('').trim(),audioPlayed=this.playAudio(p.audio);
                if(text)p.resolve({text,provider:this.provider,model:this.model,direct:true,free_only:true,audio_played:audioPlayed});
                else p.reject(new Error('free-cloud returned an empty response'));
              }
            }
          }catch(_){}
        };
        ws.onerror=()=>fail('free-cloud socket error');
        ws.onclose=()=>{this.ws=null;this.ready=null;if(this.pending){const p=this.pending;this.pending=null;clearTimeout(p.timer);p.reject(new Error('free-cloud session disconnected'));}};
      }catch(e){this.ready=null;reject(e);}
    });
    return this.ready;
  }
  async ask(text){
    if(!this.eligible(text,0))throw new Error('request requires KRISHNA PC');
    await this.connect();
    if(!this.ws||this.ws.readyState!==WebSocket.OPEN)throw new Error('free-cloud socket is unavailable');
    if(this.pending)throw new Error('a mobile cloud turn is already running');
    return new Promise((resolve,reject)=>{
      const pending={parts:[],audio:[],resolve,reject,timer:null};
      pending.timer=setTimeout(()=>{if(this.pending===pending)this.pending=null;reject(new Error('free-cloud response timed out'));},45000);
      this.pending=pending;this.turn++;
      try{
        this.ws.send(JSON.stringify({clientContent:{
          turns:[{role:'user',parts:[{text:String(text)}]}],turnComplete:true
        }}));
      }catch(e){this.pending=null;clearTimeout(pending.timer);reject(e);}
    });
  }
}
