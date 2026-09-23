(() => {
  const state = {
    active: false,
    learn: false,
    detectBusy: false,
    objects: [],
    researchQueries: [],
    objectTimer: null,
    learnTimer: null,
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
      raw_cloud_upload:false
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
    state.learnTimer=setInterval(()=>learningTick(false),6000);
    setTimeout(detect,300);
  }
  function deactivate(){
    if(!state.active)return;state.active=false;
    clearInterval(state.objectTimer);clearInterval(state.learnTimer);state.objectTimer=state.learnTimer=null;
    state.objects=[];state.researchQueries=[];state.lastLearnText="";
    const c=byId("objectOverlay");if(c){const ctx=c.getContext("2d");ctx.clearRect(0,0,c.width,c.height);}
    if(state.recorder)stopRecording();
    state.learn=false;const btn=byId("cameraLearn");if(btn){btn.classList.remove("active");btn.textContent="LEARN";}
  }

  setInterval(()=>{if(cameraActive())activate();else deactivate();},500);

  window.HawkeyeObserverUI={toggleLearn,research,photo,record,detect,learningTick};
})();
