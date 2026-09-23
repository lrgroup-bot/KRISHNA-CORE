(() => {
  const state = {
    active: false,
    learn: false,
    detectBusy: false,
    richBusy: false,
    geminiBusy: false,
    rich: null,
    localSummary: "",
    geminiAnalysis: "",
    aiMode: "LOCAL",
    cloudApproved: false,
    objects: [],
    researchQueries: [],
    objectTimer: null,
    learnTimer: null,
    richTimer: null,
    geminiTimer: null,
    liveSocket: null,
    liveVideoTimer: null,
    liveAudioContext: null,
    liveAudioSource: null,
    liveAudioNode: null,
    liveAudioNextTime: 0,
    lastZoomAt: 0,
    lastLearnText: "",
    recorder: null,
    chunks: [],
    recordStopTimer: null,
  };

  function byId(id){ return document.getElementById(id); }
  function cameraActive(){
    const layer=byId("cameraLayer");
    return !!(layer && layer.classList.contains("active") && typeof fieldStream!=="undefined" && fieldStream);
  }
  function video(){ return byId("fieldVideo"); }

  function captureFrame(maxW=480, quality=0.58){
    const v=video();
    if(!v || !v.videoWidth || !v.videoHeight) return null;
    const scale=Math.min(1,maxW/v.videoWidth);
    const c=document.createElement("canvas");
    c.width=Math.max(1,Math.round(v.videoWidth*scale));
    c.height=Math.max(1,Math.round(v.videoHeight*scale));
    c.getContext("2d",{alpha:false}).drawImage(v,0,0,c.width,c.height);
    return {canvas:c,b64:(c.toDataURL("image/jpeg",quality).split(",")[1]||"")};
  }

  function ensureObjectCanvas(){
    let c=byId("objectOverlay");
    if(c) return c;
    c=document.createElement("canvas");
    c.id="objectOverlay";
    c.className="diagnosticOverlay";
    const diagnostic=byId("diagnosticOverlay");
    if(diagnostic && diagnostic.parentNode) diagnostic.parentNode.insertBefore(c,diagnostic.nextSibling);
    return c;
  }

  function ensureRichCanvas(){
    let c=byId("richOverlay");
    if(c)return c;
    c=document.createElement("canvas");
    c.id="richOverlay";
    c.className="diagnosticOverlay";
    const object=ensureObjectCanvas();
    if(object&&object.parentNode)object.parentNode.insertBefore(c,object.nextSibling);
    return c;
  }

  function fitOverlay(canvas){
    const v=video();if(!canvas||!v||!v.videoWidth||!v.videoHeight)return null;
    const cw=canvas.clientWidth||v.clientWidth,ch=canvas.clientHeight||v.clientHeight;if(!cw||!ch)return null;
    const dpr=Math.max(1,window.devicePixelRatio||1);canvas.width=Math.round(cw*dpr);canvas.height=Math.round(ch*dpr);
    const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,cw,ch);
    const scale=Math.max(cw/v.videoWidth,ch/v.videoHeight),dw=v.videoWidth*scale,dh=v.videoHeight*scale,ox=(cw-dw)/2,oy=(ch-dh)/2;
    return {ctx,cw,ch,dw,dh,ox,oy,rect:b=>({x:ox+(Number(b[0])||0)*dw,y:oy+(Number(b[1])||0)*dh,w:(Number(b[2])||0)*dw,h:(Number(b[3])||0)*dh})};
  }

  function drawRich(result){
    const c=ensureRichCanvas(),m=fitOverlay(c);if(!m)return;
    const {ctx,rect}=m;ctx.font="11px sans-serif";ctx.textBaseline="bottom";ctx.lineWidth=1.4;
    const ocr=result&&result.ocr&&Array.isArray(result.ocr.blocks)?result.ocr.blocks:[];
    for(const item of ocr){if(!Array.isArray(item.bbox))continue;const r=rect(item.bbox);ctx.strokeStyle="#45d4e8";ctx.fillStyle="#45d4e8";ctx.strokeRect(r.x,r.y,r.w,r.h);ctx.fillText(String(item.text||"TEXT").slice(0,28),r.x+2,Math.max(12,r.y-1));}
    for(const item of (result&&Array.isArray(result.faces)?result.faces:[])){if(!Array.isArray(item.bbox))continue;const r=rect(item.bbox);ctx.strokeStyle="#ff9bd7";ctx.fillStyle="#ff9bd7";ctx.strokeRect(r.x,r.y,r.w,r.h);ctx.fillText("FACE · UNKNOWN",r.x+2,Math.max(12,r.y-1));}
    for(const item of (result&&Array.isArray(result.subjects)?result.subjects:[])){if(!Array.isArray(item.bbox))continue;const r=rect(item.bbox);ctx.setLineDash([5,4]);ctx.strokeStyle="#f2c96f";ctx.strokeRect(r.x,r.y,r.w,r.h);ctx.setLineDash([]);}
    for(const p of (result&&Array.isArray(result.pose_landmarks)?result.pose_landmarks:[])){const x=m.ox+(Number(p.x)||0)*m.dw,y=m.oy+(Number(p.y)||0)*m.dh;ctx.fillStyle="#b9ff9c";ctx.beginPath();ctx.arc(x,y,2.3,0,Math.PI*2);ctx.fill();}
  }

  function drawObjects(objects){
    const c=ensureObjectCanvas(),v=video();
    if(!c||!v||!v.videoWidth||!v.videoHeight)return;
    const cw=c.clientWidth||v.clientWidth,ch=c.clientHeight||v.clientHeight;
    if(!cw||!ch)return;
    const dpr=Math.max(1,window.devicePixelRatio||1);
    c.width=Math.round(cw*dpr);c.height=Math.round(ch*dpr);
    const ctx=c.getContext("2d");
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,cw,ch);
    const scale=Math.max(cw/v.videoWidth,ch/v.videoHeight),dw=v.videoWidth*scale,dh=v.videoHeight*scale,ox=(cw-dw)/2,oy=(ch-dh)/2;
    ctx.lineWidth=2;ctx.font="12px sans-serif";ctx.textBaseline="bottom";
    for(const item of objects||[]){
      const b=item&&item.bbox;if(!Array.isArray(b)||b.length!==4)continue;
      const x=ox+(Number(b[0])||0)*dw,y=oy+(Number(b[1])||0)*dh,w=(Number(b[2])||0)*dw,h=(Number(b[3])||0)*dh;
      ctx.strokeStyle="#50f0ac";ctx.fillStyle="#50f0ac";ctx.strokeRect(x,y,w,h);
      const tid=item.tracking_id===null||item.tracking_id===undefined?"":" #"+item.tracking_id;
      ctx.fillText(String(item.label||"object").slice(0,20)+tid,x+3,Math.max(14,y-2));
    }
  }

  async function autoZoom(objects){
    if(!cameraActive()||Date.now()-state.lastZoomAt<1500||!objects||!objects.length)return;
    const track=fieldStream.getVideoTracks()[0];
    if(!track||!track.getCapabilities||!track.getSettings||!track.applyConstraints)return;
    const caps=track.getCapabilities();
    if(!caps||!caps.zoom||typeof caps.zoom.min!=="number"||typeof caps.zoom.max!=="number")return;
    let best=null,bestArea=-1;
    for(const item of objects){
      const b=item&&item.bbox;if(!Array.isArray(b)||b.length!==4)continue;
      const area=Math.max(0,Number(b[2])||0)*Math.max(0,Number(b[3])||0);
      if(area>bestArea){bestArea=area;best=item;}
    }
    if(!best||bestArea<=0)return;
    const current=Number(track.getSettings().zoom||caps.zoom.min||1);
    let desired=current;
    if(bestArea<0.10)desired=current*Math.min(1.8,Math.sqrt(0.16/bestArea));
    else if(bestArea>0.42)desired=current*0.88;
    else return;
    desired=Math.max(caps.zoom.min,Math.min(caps.zoom.max,desired));
    if(Math.abs(desired-current)<0.08)return;
    try{
      state.lastZoomAt=Date.now();
      await track.applyConstraints({advanced:[{zoom:desired}]});
    }catch(_){}
  }

  async function detect(){
    if(!cameraActive()||state.detectBusy||!window.Krishna||!Krishna.hawkeyeDetectObjects)return;
    const frame=captureFrame(480,0.55);if(!frame||!frame.b64)return;
    state.detectBusy=true;
    try{
      const result=JSON.parse(Krishna.hawkeyeDetectObjects(frame.b64));
      if(result.error)return;
      state.objects=Array.isArray(result.objects)?result.objects:[];
      drawObjects(state.objects);
      await autoZoom(state.objects);
    }catch(_){}
    finally{state.detectBusy=false;}
  }

  function richMetadata(){
    const r=state.rich||{},ocr=r.ocr||{};
    return {
      ocr_text:String(ocr.text||"").slice(0,1500),
      barcodes:Array.isArray(r.barcodes)?r.barcodes.slice(0,12):[],
      face_count:Array.isArray(r.faces)?r.faces.length:0,
      pose_landmark_count:Array.isArray(r.pose_landmarks)?r.pose_landmarks.length:0,
      subject_count:Array.isArray(r.subjects)?r.subjects.length:0,
      recommended_next_scan:String(r.recommended_next_scan||""),
      evidence_state:"OBSERVED"
    };
  }

  async function richPerception(){
    if(!cameraActive()||state.richBusy||!window.Krishna||!Krishna.hawkeyeRichPerception)return;
    const frame=captureFrame(720,0.62);if(!frame||!frame.b64)return;
    state.richBusy=true;
    try{
      const result=JSON.parse(Krishna.hawkeyeRichPerception(frame.b64));if(result.error)return;
      state.rich=result;drawRich(result);
      const parts=[];
      const text=String(result.ocr&&result.ocr.text||"").trim();if(text)parts.push("OCR: "+text.slice(0,180));
      if(Array.isArray(result.barcodes)&&result.barcodes.length)parts.push("Codes: "+result.barcodes.map(x=>String(x.value||"").slice(0,50)).filter(Boolean).join(" · "));
      if(result.recommended_next_scan)parts.push("Next view: "+result.recommended_next_scan);
      state.localSummary=parts.join("\n");
      if(Array.isArray(result.faces)&&result.faces.length&&state.liveSocket)stopGeminiLive("Gemini Live stopped because a face entered the frame; HAWKEYE stays local.");
    }catch(_){}
    finally{state.richBusy=false;}
  }

  function sceneSignature(){
    const labels=state.objects.map(x=>String(x.label||"object")+":"+String(x.tracking_id??"")).sort().join("|");
    const text=String(state.rich&&state.rich.ocr&&state.rich.ocr.text||"").slice(0,180);
    return labels+"#"+text;
  }

  function geminiMetadata(extra={}){
    const r=state.rich||{},ocr=String(r.ocr&&r.ocr.text||"");
    return Object.assign({
      cloud_approved:!!state.cloudApproved,
      selected_keyframe:true,
      contains_biometrics:Array.isArray(r.faces)&&r.faces.length>0,
      contains_credentials:ocr.includes("[SECRET REDACTED]"),
      private_document:/\b(private|confidential|secret document|personal document)\b/i.test(String(typeof fieldGoal!=="undefined"?fieldGoal:"")),
      raw_recording:false,
      session_id:String(typeof fieldSession!=="undefined"?fieldSession:""),
      source:"HAWKEYE_MOBILE_SELECTED_KEYFRAME"
    },extra||{});
  }

  function geminiPrompt(){
    const labels=state.objects.map(x=>String(x.label||"object")).filter(Boolean).join(", ");
    const ocr=String(state.rich&&state.rich.ocr&&state.rich.ocr.text||"").slice(0,1200);
    return [
      "You are the Gemini worker inside KRISHNA HAWKEYE.",
      "Analyze only this selected camera keyframe. Distinguish OBSERVED facts from INFERRED possibilities.",
      "Do not identify unknown people and do not reconstruct credentials.",
      "User goal: "+String(typeof fieldGoal!=="undefined"?fieldGoal:"live visual assistance"),
      labels?"Local tracked objects: "+labels:"",
      ocr?"Local OCR (already redacted): "+ocr:"",
      "Return a concise result and the next camera view that would reduce uncertainty."
    ].filter(Boolean).join("\n");
  }

  async function geminiTick(force=false){
    if(!cameraActive()||state.aiMode==="LOCAL"||state.geminiBusy||!state.cloudApproved||!window.Krishna||!Krishna.hawkeyeGeminiAnalyze)return;
    const sig=sceneSignature();if(state.aiMode==="AUTO"&&!force&&sig&&sig===state.lastGeminiSignature)return;
    const meta=geminiMetadata();
    if(meta.contains_biometrics||meta.contains_credentials||meta.private_document)return;
    const frame=captureFrame(720,0.60);if(!frame||!frame.b64)return;
    state.geminiBusy=true;state.lastGeminiSignature=sig;
    try{
      const out=JSON.parse(Krishna.hawkeyeGeminiAnalyze(frame.b64,"image/jpeg",geminiPrompt(),JSON.stringify(meta)));
      if(out.error)throw new Error(out.error);
      state.geminiAnalysis=String(out.analysis||"").trim();
      const local=state.localSummary?state.localSummary+"\n\n":"";
      if(state.geminiAnalysis)byId("cameraAnalysis").textContent=local+"Gemini: "+state.geminiAnalysis;
    }catch(e){if(force&&typeof reply==="function")reply("Gemini: "+e.message,"warn");}
    finally{state.geminiBusy=false;}
  }

  function toggleAI(){
    const next=state.aiMode==="LOCAL"?"AUTO":(state.aiMode==="AUTO"?"GEMINI":"LOCAL");
    state.aiMode=next;state.cloudApproved=next!=="LOCAL";
    const btn=byId("cameraAI");if(btn){btn.textContent=next==="LOCAL"?"AI:LOCAL":("AI:"+next);btn.classList.toggle("active",next!=="LOCAL");}
    if(next==="LOCAL"){state.geminiAnalysis="";if(typeof reply==="function")reply("HAWKEYE cloud reasoning is off; camera processing remains local.","good");}
    else {if(typeof reply==="function")reply("HAWKEYE "+next+" enabled for selected non-sensitive keyframes only.","good");setTimeout(()=>geminiTick(true),80);}
  }

  function bytesToBase64(bytes){
    let s="",step=0x8000;for(let i=0;i<bytes.length;i+=step)s+=String.fromCharCode.apply(null,bytes.subarray(i,Math.min(bytes.length,i+step)));return btoa(s);
  }

  function playLivePcm(b64,mimeType){
    try{
      const rate=Number((String(mimeType||"").match(/rate=(\d+)/)||[])[1]||24000);
      if(!state.liveAudioContext)state.liveAudioContext=new (window.AudioContext||window.webkitAudioContext)({sampleRate:rate});
      const raw=atob(String(b64||"")),bytes=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
      const samples=new Int16Array(bytes.buffer,bytes.byteOffset,Math.floor(bytes.byteLength/2)),buf=state.liveAudioContext.createBuffer(1,samples.length,rate),ch=buf.getChannelData(0);
      for(let i=0;i<samples.length;i++)ch[i]=Math.max(-1,Math.min(1,samples[i]/32768));
      const src=state.liveAudioContext.createBufferSource();src.buffer=buf;src.connect(state.liveAudioContext.destination);
      const when=Math.max(state.liveAudioContext.currentTime,state.liveAudioNextTime||0);src.start(when);state.liveAudioNextTime=when+buf.duration;
    }catch(_){}
  }

  function startLiveAudioInput(){
    if(!fieldStream||!fieldStream.getAudioTracks().length||!state.liveSocket)return;
    try{
      const ctx=new (window.AudioContext||window.webkitAudioContext)(),src=ctx.createMediaStreamSource(new MediaStream([fieldStream.getAudioTracks()[0]])),node=ctx.createScriptProcessor(4096,1,1);
      state.liveAudioContext=state.liveAudioContext||ctx;state.liveInputAudioContext=ctx;state.liveAudioSource=src;state.liveAudioNode=node;
      node.onaudioprocess=e=>{
        const ws=state.liveSocket;if(!ws||ws.readyState!==WebSocket.OPEN)return;
        const f=e.inputBuffer.getChannelData(0),pcm=new Int16Array(f.length);
        for(let i=0;i<f.length;i++){const v=Math.max(-1,Math.min(1,f[i]));pcm[i]=v<0?v*32768:v*32767;}
        ws.send(JSON.stringify({realtimeInput:{audio:{data:bytesToBase64(new Uint8Array(pcm.buffer)),mimeType:"audio/pcm;rate="+ctx.sampleRate}}}));
      };
      src.connect(node);node.connect(ctx.destination);
    }catch(_){}
  }

  function stopGeminiLive(message=""){
    clearInterval(state.liveVideoTimer);state.liveVideoTimer=null;
    try{if(state.liveAudioNode)state.liveAudioNode.disconnect();}catch(_){}
    try{if(state.liveAudioSource)state.liveAudioSource.disconnect();}catch(_){}
    try{if(state.liveInputAudioContext)state.liveInputAudioContext.close();}catch(_){}
    state.liveAudioNode=state.liveAudioSource=state.liveInputAudioContext=null;
    try{if(state.liveSocket){state.liveSocket.onclose=null;state.liveSocket.close();}}catch(_){}
    state.liveSocket=null;
    const btn=byId("cameraGeminiLive");if(btn){btn.classList.remove("active","recording");btn.textContent="G-LIVE";}
    if(message&&typeof reply==="function")reply(message,"warn");
  }

  async function toggleGeminiLive(){
    if(state.liveSocket){stopGeminiLive("Gemini Live stopped.");return;}
    if(!cameraActive()||!window.Krishna||!Krishna.hawkeyeGeminiLiveToken)return;
    state.cloudApproved=true;
    const meta=geminiMetadata({cloud_approved:true,user_explicit:true});
    if(meta.contains_biometrics||meta.contains_credentials||meta.private_document){if(typeof reply==="function")reply("Gemini Live is blocked for this sensitive scene; HAWKEYE stays local.","warn");return;}
    try{
      const token=JSON.parse(Krishna.hawkeyeGeminiLiveToken(JSON.stringify(meta)));if(token.error)throw new Error(token.error);
      const url="wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?access_token="+encodeURIComponent(token.token);
      const ws=new WebSocket(url);state.liveSocket=ws;
      const btn=byId("cameraGeminiLive");if(btn){btn.classList.add("active");btn.textContent="G-LIVE…";}
      ws.onopen=()=>{
        ws.send(JSON.stringify({setup:{model:"models/"+token.live_model,responseModalities:["AUDIO"]}}));
        state.liveVideoTimer=setInterval(()=>{
          if(!state.liveSocket||state.liveSocket.readyState!==WebSocket.OPEN)return;
          const f=captureFrame(640,0.52);if(f&&f.b64)state.liveSocket.send(JSON.stringify({realtimeInput:{video:{data:f.b64,mimeType:"image/jpeg"}}}));
        },1000);
        startLiveAudioInput();
        if(btn)btn.textContent="G-LIVE ON";
        if(typeof reply==="function")reply("Gemini Live connected with a short-lived token; local HAWKEYE remains active.","good");
      };
      ws.onmessage=e=>{
        try{
          const msg=JSON.parse(String(e.data||"{}")),sc=msg.serverContent||{};
          const text=String(sc.outputTranscription&&sc.outputTranscription.text||"").trim();
          if(text){state.geminiAnalysis=text;byId("cameraAnalysis").textContent=(state.localSummary?state.localSummary+"\n\n":"")+"Gemini Live: "+text;}
          const parts=sc.modelTurn&&Array.isArray(sc.modelTurn.parts)?sc.modelTurn.parts:[];
          for(const p of parts)if(p.inlineData&&p.inlineData.data)playLivePcm(p.inlineData.data,p.inlineData.mimeType);
        }catch(_){}
      };
      ws.onerror=()=>stopGeminiLive("Gemini Live connection error; local HAWKEYE is still running.");
      ws.onclose=()=>{if(state.liveSocket)stopGeminiLive("Gemini Live disconnected; local HAWKEYE is still running.");};
    }catch(e){stopGeminiLive();if(typeof reply==="function")reply("Gemini Live: "+e.message,"bad");}
  }

  function sourceType(){
    const goal=String(typeof fieldGoal!=="undefined"?fieldGoal:"").toLowerCase();
    if(/book|page|read|textbook|manual/.test(goal))return"book";
    if(/video|film|watch|screen/.test(goal))return"video";
    if(/listen|audio|sound/.test(goal))return"audio";
    if(/object|device|machine|car|vehicle|tree|flower|animal/.test(goal))return"object";
    return"camera";
  }

  function currentAnalysis(){
    return String(byId("cameraAnalysis")?.textContent||"").trim();
  }

  async function learningTick(force=false){
    if(!cameraActive()||(!state.learn&&!force)||!window.Krishna||!Krishna.hawkeyeObserveLearning)return;
    const analysis=currentAnalysis();
    if(!analysis||(!force&&analysis===state.lastLearnText))return;
    state.lastLearnText=analysis;
    try{
      const modalities=["image"];
      if(typeof fieldAudio!=="undefined"&&fieldAudio)modalities.push("audio");
      if(sourceType()==="video")modalities.push("video");
      const payload={
        utterance:"Learn, verify and route what I am showing you.",
        source_type:sourceType(),
        source_ref:String(typeof fieldSession!=="undefined"?fieldSession:""),
        modalities,
        subject:String(typeof fieldGoal!=="undefined"?fieldGoal:"HAWKEYE observation"),
        analysis,
        confidence:0.65,
        evidence_state:"OBSERVED",
        novelty:0.6,
        quality:0.7,
        importance:state.learn?0.9:0.65,
        audio_observations:{live_microphone:!!(typeof fieldAudio!=="undefined"&&fieldAudio),timestamp_ms:Date.now()},
        public_clues:[]
      };
      const learned=JSON.parse(Krishna.hawkeyeObserveLearning(JSON.stringify(payload)));
      if(learned.error)throw new Error(learned.error);
      state.researchQueries=learned.research_plan&&Array.isArray(learned.research_plan.queries)?learned.research_plan.queries:[];
      if(learned.lead_rishi){
        const team=Array.isArray(learned.rishi_team)&&learned.rishi_team.length?" · "+learned.rishi_team.join(", "):"";
        const base=currentAnalysis().split("\nLearning route:")[0];
        byId("cameraAnalysis").textContent=base+"\nLearning route: "+learned.lead_rishi+team;
      }
    }catch(_){}
  }

  function metadata(){
    let zoom=1;
    try{
      const track=fieldStream&&fieldStream.getVideoTracks()[0];
      zoom=Number(track&&track.getSettings?track.getSettings().zoom||1:1);
    }catch(_){}
    return {
      schema:"hawkeye.mobile-capture.v1",
      session_id:String(typeof fieldSession!=="undefined"?fieldSession:""),
      goal:String(typeof fieldGoal!=="undefined"?fieldGoal:""),
      timestamp_ms:Date.now(),
      analysis:currentAnalysis(),
      objects:state.objects,
      zoom,
      learning_mode:state.learn,
      evidence_state:"OBSERVED",
      raw_cloud_upload:false,
      ai_mode:state.aiMode,
      rich_perception:richMetadata(),
      gemini_analysis:String(state.geminiAnalysis||"").slice(0,2000)
    };
  }

  async function photo(){
    if(!cameraActive()||!Krishna.saveHawkeyeCapture)return;
    const v=video();if(!v||!v.videoWidth||!v.videoHeight)return;
    try{
      const maxW=1280,scale=Math.min(1,maxW/v.videoWidth),c=document.createElement("canvas");
      c.width=Math.max(1,Math.round(v.videoWidth*scale));c.height=Math.max(1,Math.round(v.videoHeight*scale));
      const ctx=c.getContext("2d",{alpha:false});ctx.drawImage(v,0,0,c.width,c.height);
      for(const id of ["diagnosticOverlay","objectOverlay"]){
        const overlay=byId(id);if(overlay&&overlay.width&&overlay.height)ctx.drawImage(overlay,0,0,c.width,c.height);
      }
      const meta=metadata(),caption=String(meta.analysis||"").replace(/\s+/g," ").slice(0,180);
      ctx.fillStyle="rgba(0,0,0,.68)";ctx.fillRect(0,c.height-68,c.width,68);ctx.fillStyle="#fff";
      ctx.font=Math.max(14,Math.round(c.width/60))+"px sans-serif";
      ctx.fillText("KRISHNA HAWKEYE · "+new Date(meta.timestamp_ms).toLocaleString(),14,c.height-40);
      ctx.fillText(caption,14,c.height-15);
      const b64=c.toDataURL("image/jpeg",0.88).split(",")[1]||"";
      const out=JSON.parse(Krishna.saveHawkeyeCapture(b64,"image/jpeg","image",JSON.stringify(meta)));
      if(out.error)throw new Error(out.error);
      if(typeof reply==="function")reply("HAWKEYE photo + data saved on this phone.","good");
    }catch(e){if(typeof reply==="function")reply("Capture: "+e.message,"bad");}
  }

  function supportedVideoType(){
    if(typeof MediaRecorder==="undefined")return"";
    for(const t of ["video/webm;codecs=vp8,opus","video/webm","video/mp4"]){
      try{if(MediaRecorder.isTypeSupported(t))return t;}catch(_){}
    }
    return"";
  }
  function blobBase64(blob){
    return new Promise((resolve,reject)=>{
      const r=new FileReader();r.onerror=()=>reject(r.error||new Error("media read failed"));
      r.onload=()=>resolve(String(r.result||"").split(",")[1]||"");r.readAsDataURL(blob);
    });
  }

  async function stopRecording(){
    if(state.recorder&&state.recorder.state!=="inactive"){
      try{state.recorder.stop();}catch(_){}
    }
  }

  async function record(){
    const btn=byId("cameraRecord");
    if(state.recorder){await stopRecording();return;}
    if(!cameraActive())return;
    const mime=supportedVideoType();if(!mime){if(typeof reply==="function")reply("Video recording is unavailable.","bad");return;}
    try{
      state.chunks=[];
      const clones=[...fieldStream.getVideoTracks(),...fieldStream.getAudioTracks()].map(t=>t.clone());
      const stream=new MediaStream(clones);
      const rec=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:600000,audioBitsPerSecond:48000});
      state.recorder=rec;if(btn){btn.classList.add("recording");btn.textContent="STOP";}
      rec.ondataavailable=e=>{if(e.data&&e.data.size)state.chunks.push(e.data);};
      rec.onstop=async()=>{
        clearTimeout(state.recordStopTimer);state.recordStopTimer=null;state.recorder=null;
        if(btn){btn.classList.remove("recording");btn.textContent="REC+DATA";}
        for(const t of clones)try{t.stop();}catch(_){}
        try{
          const blob=new Blob(state.chunks,{type:rec.mimeType||mime});
          if(!blob.size||blob.size>20*1024*1024)throw new Error("recording exceeded bounded size");
          const b64=await blobBase64(blob);
          const out=JSON.parse(Krishna.saveHawkeyeCapture(b64,blob.type||mime,"video",JSON.stringify(metadata())));
          if(out.error)throw new Error(out.error);
          if(typeof reply==="function")reply("HAWKEYE video + data saved on this phone.","good");
        }catch(e){if(typeof reply==="function")reply("Recording: "+e.message,"bad");}
      };
      rec.start();
      state.recordStopTimer=setTimeout(stopRecording,8000);
    }catch(e){state.recorder=null;if(btn){btn.classList.remove("recording");btn.textContent="REC+DATA";}if(typeof reply==="function")reply("Recording: "+e.message,"bad");}
  }

  function research(){
    const labels=state.objects.map(x=>String(x.label||"")).filter(Boolean);
    const initial=state.researchQueries[0]||labels.join(" ")||String(typeof fieldGoal!=="undefined"?fieldGoal:"current observed object");
    const q=(prompt("Research what HAWKEYE is seeing:",initial)||"").trim();if(!q)return;
    try{
      const out=JSON.parse(Krishna.openResearchQuery(q));if(out.error)throw new Error(out.error);
      if(typeof reply==="function")reply("Research opened in your browser session.","good");
    }catch(e){if(typeof reply==="function")reply("Research: "+e.message,"bad");}
  }

  function toggleLearn(){
    state.learn=!state.learn;
    const btn=byId("cameraLearn");if(btn){btn.classList.toggle("active",state.learn);btn.textContent=state.learn?"LEARNING":"LEARN";}
    const mode=byId("cameraMode");if(mode)mode.textContent=state.learn?"HAWKEYE · LEARNING":"HAWKEYE · AUTO SCAN";
    if(state.learn)learningTick(true);
  }

  function activate(){
    if(state.active)return;state.active=true;
    state.objectTimer=setInterval(detect,1200);
    state.richTimer=setInterval(richPerception,2600);
    state.learnTimer=setInterval(()=>learningTick(false),6000);
    state.geminiTimer=setInterval(()=>geminiTick(false),8000);
    setTimeout(detect,300);setTimeout(richPerception,650);
  }
  function deactivate(){
    if(!state.active)return;state.active=false;
    clearInterval(state.objectTimer);clearInterval(state.learnTimer);clearInterval(state.richTimer);clearInterval(state.geminiTimer);
    state.objectTimer=state.learnTimer=state.richTimer=state.geminiTimer=null;
    stopGeminiLive();
    state.objects=[];state.researchQueries=[];state.lastLearnText="";state.rich=null;state.localSummary="";state.geminiAnalysis="";
    state.aiMode="LOCAL";state.cloudApproved=false;
    for(const id of ["objectOverlay","richOverlay"]){const c=byId(id);if(c){const ctx=c.getContext("2d");ctx.clearRect(0,0,c.width,c.height);}}
    if(state.recorder)stopRecording();
    state.learn=false;const btn=byId("cameraLearn");if(btn){btn.classList.remove("active");btn.textContent="LEARN";}
    const ai=byId("cameraAI");if(ai){ai.classList.remove("active");ai.textContent="AI:LOCAL";}
  }

  setInterval(()=>{if(cameraActive())activate();else deactivate();},500);

  window.HawkeyeObserverUI={toggleLearn,research,photo,record,detect,richPerception,learningTick,toggleAI,geminiTick,toggleGeminiLive,stopGeminiLive};
})();
