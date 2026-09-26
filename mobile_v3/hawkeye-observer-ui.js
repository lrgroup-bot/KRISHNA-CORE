(() => {
  const state = {
    active: false,
    learn: false,
    detectBusy: false,
    richBusy: false,
    handBusy: false,
    geminiBusy: false,
    freeCloudBusy: false,
    rich: null,
    handResult: null,
    localSummary: "",
    geminiAnalysis: "",
    freeCloudAnalysis: "",
    lastFreeCloudSignature: "",
    lastFreeCloudProvider: "",
    lastFreeCloudModel: "",
    lastFreeCloudRole: "",
    lastFreeCloudReviews: [],
    lastFreeCloudPc: null,
    aiMode: "LOCAL",
    cloudApproved: false,
    lockedTrackingId: null,
    translationEnabled: false,
    translationTarget: "en",
    translationText: "",
    translationSource: "",
    translationBusy: false,
    translationModelReady: false,
    gesturesEnabled: false,
    gestureCandidate: "NONE",
    gestureCandidateCount: 0,
    lastGesture: "NONE",
    lastGestureAt: 0,
    torchOn: false,
    objects: [],
    researchQueries: [],
    objectTimer: null,
    learnTimer: null,
    richTimer: null,
    handTimer: null,
    geminiTimer: null,
    freeCloudTimer: null,
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

  function sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms));}

  function frameQuality(canvas){
    if(!canvas||!canvas.width||!canvas.height)return {score:0,brightness:0,detail:0,lowLight:true};
    const probe=document.createElement("canvas");probe.width=32;probe.height=24;
    const ctx=probe.getContext("2d",{alpha:false,willReadFrequently:true});ctx.drawImage(canvas,0,0,32,24);
    const data=ctx.getImageData(0,0,32,24).data,lum=new Float32Array(32*24);let mean=0,edge=0,k=0;
    for(let i=0;i<data.length;i+=4){const y=.2126*data[i]+.7152*data[i+1]+.0722*data[i+2];lum[k++]=y;mean+=y;}mean/=lum.length;
    for(let y=0;y<24;y++)for(let x=0;x<32;x++){const i=y*32+x;if(x)edge+=Math.abs(lum[i]-lum[i-1]);if(y)edge+=Math.abs(lum[i]-lum[i-32]);}
    edge/=((31*24)+(23*32));const exposure=Math.max(0,1-Math.abs(mean-128)/118),detail=Math.min(1,edge/24);
    return {score:Math.max(0,Math.min(1,.45*exposure+.55*detail)),brightness:mean,detail,lowLight:mean<45};
  }

  async function captureBestFrame(maxW=720,quality=0.62,samples=4){
    let best=null;
    for(let i=0;i<Math.max(1,samples);i++){
      const frame=captureFrame(maxW,quality);if(frame){const q=frameQuality(frame.canvas);if(!best||q.score>best.quality.score)best={...frame,quality:q};}
      if(i+1<samples)await sleep(90);
    }
    return best;
  }


  function naturalEdit(source,quality){
    const out=document.createElement("canvas");out.width=source.width;out.height=source.height;
    const ctx=out.getContext("2d",{alpha:false});
    const brightness=quality&&quality.brightness<92?1.10:(quality&&quality.brightness>178?0.96:1.04);
    const contrast=quality&&quality.detail<0.28?1.10:1.06;
    ctx.filter="brightness("+brightness+") contrast("+contrast+") saturate(1.08)";
    ctx.drawImage(source,0,0,out.width,out.height);
    ctx.filter="none";
    const glow=ctx.createLinearGradient(0,0,0,out.height);
    glow.addColorStop(0,"rgba(255,226,188,.035)");
    glow.addColorStop(.62,"rgba(255,255,255,0)");
    glow.addColorStop(1,"rgba(12,35,46,.035)");
    ctx.fillStyle=glow;ctx.fillRect(0,0,out.width,out.height);
    return out;
  }

  async function photographerPhoto(){
    if(!cameraActive()||!window.Krishna||!Krishna.saveHawkeyeCapture)return;
    try{
      if(typeof reply==="function")reply("KRISHNA photographer · hold naturally…","good");
      await sleep(550);
      const best=await captureBestFrame(2048,0.95,9);if(!best)throw new Error("camera frame unavailable");
      const edited=naturalEdit(best.canvas,best.quality);
      const meta=metadata();
      meta.photographer_mode=true;
      meta.user_requested_portrait=true;
      meta.capture_quality=best.quality;
      meta.editor="KRISHNA_LOCAL_NATURAL_V1";
      meta.edit_operations=["best-frame-selection","exposure-balance","contrast-balance","natural-saturation","subtle-tone"];
      meta.overlays_baked=false;
      meta.subject_identity_inferred=false;
      meta.raw_cloud_upload=false;
      const b64=edited.toDataURL("image/jpeg",0.94).split(",")[1]||"";
      const out=JSON.parse(Krishna.saveHawkeyeCapture(b64,"image/jpeg","image",JSON.stringify(meta)));
      if(out.error)throw new Error(out.error);
      if(typeof reply==="function")reply(out.gallery_visible?"Photo edited and saved to your KRISHNA gallery.":"Photo saved locally.","good");
      if(typeof setMode==="function")setMode("CHAT","PHOTO SAVED");
      return out;
    }catch(e){if(typeof reply==="function")reply("Photographer: "+e.message,"bad");return null;}
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
    if(state.handResult&&Array.isArray(state.handResult.hands)){
      for(const hand of state.handResult.hands){
        const pts=Array.isArray(hand.landmarks)?hand.landmarks:[];
        for(const p of pts){const x=m.ox+(Number(p.x)||0)*m.dw,y=m.oy+(Number(p.y)||0)*m.dh;ctx.fillStyle="#ffd36b";ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill();}
        if(pts.length){const p=pts[0],x=m.ox+(Number(p.x)||0)*m.dw,y=m.oy+(Number(p.y)||0)*m.dh;ctx.fillStyle="#ffd36b";ctx.fillText(String(hand.handedness||"HAND")+" · "+String(hand.gesture||"None"),x+5,y-5);}
      }
    }
    if(state.translationEnabled&&state.translationText){
      const label=("TRANSLATED "+state.translationTarget.toUpperCase()+" · "+state.translationText).slice(0,150);
      ctx.font="12px sans-serif";const width=Math.min(m.cw-16,Math.max(180,ctx.measureText(label).width+16));
      ctx.fillStyle="rgba(3,19,29,.88)";ctx.fillRect(8,m.ch-38,width,28);
      ctx.fillStyle="#ffffff";ctx.fillText(label,14,m.ch-18);
    }
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
      const top=Array.isArray(item.labels)&&item.labels.length?item.labels[0]:null;
      const conf=top&&Number.isFinite(Number(top.confidence))?" "+Math.round(Number(top.confidence)*100)+"%":"";
      ctx.fillText(String(item.label||"object").slice(0,20)+tid+conf,x+3,Math.max(14,y-2));
    }
  }

  async function autoZoom(objects){
    if(!cameraActive()||Date.now()-state.lastZoomAt<1500||!objects||!objects.length)return;
    const track=fieldStream.getVideoTracks()[0];
    if(!track||!track.getCapabilities||!track.getSettings||!track.applyConstraints)return;
    const caps=track.getCapabilities();
    if(!caps||!caps.zoom||typeof caps.zoom.min!=="number"||typeof caps.zoom.max!=="number")return;
    let best=null,bestArea=-1;
    if(state.lockedTrackingId!==null){
      best=(objects||[]).find(x=>x&&x.tracking_id===state.lockedTrackingId)||null;
      if(best&&Array.isArray(best.bbox))bestArea=Math.max(0,Number(best.bbox[2])||0)*Math.max(0,Number(best.bbox[3])||0);
      if(!best){state.lockedTrackingId=null;const lock=byId("cameraLock");if(lock){lock.classList.remove("active");lock.textContent="LOCK";}}
    }
    if(!best)for(const item of objects){
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
      gesture:r.gesture||{name:"NONE",scope:"upper-body-pose-only"},
      hand_gesture:state.handResult?{
        engine:String(state.handResult.engine||""),
        hand_count:Number(state.handResult.hand_count||0),
        primary:String(state.handResult.primary_gesture||"None"),
        confidence:Number(state.handResult.primary_confidence||0),
        finger_landmarks:!!state.handResult.finger_landmarks
      }:null,
      translation_enabled:state.translationEnabled,
      translation_target:state.translationTarget,
      translated_text:String(state.translationText||"").slice(0,1500),
      privacy_unknown_faces_local_only:true,
      recommended_next_scan:String(r.recommended_next_scan||""),
      evidence_state:"OBSERVED"
    };
  }

  async function translateCurrentOcr(force=false){
    if(!state.translationEnabled||state.translationBusy||!window.Krishna||!Krishna.hawkeyeTranslateText)return;
    const text=String(state.rich&&state.rich.ocr&&state.rich.ocr.text||"").trim();
    if(!text||(!force&&text===state.translationSource))return;
    state.translationBusy=true;
    try{
      const out=JSON.parse(Krishna.hawkeyeTranslateText(text,state.translationTarget,!state.translationModelReady));
      if(out.error)throw new Error(out.error);
      state.translationText=String(out.translated_text||"").trim();
      state.translationSource=text;
      state.translationModelReady=!!out.model_downloaded_or_available;
      drawRich(state.rich);
    }catch(e){
      if(force&&typeof reply==="function")reply("Translation: "+e.message,"warn");
    }finally{state.translationBusy=false;}
  }

  async function toggleTranslation(){
    const btn=byId("cameraTranslate");
    if(state.translationEnabled){
      state.translationEnabled=false;state.translationText="";state.translationSource="";
      if(btn){btn.classList.remove("active");btn.textContent="TRANS";}
      if(state.rich)drawRich(state.rich);
      return;
    }
    const target=(prompt("Translate HAWKEYE OCR to language code:","en")||"").trim().toLowerCase();if(!target)return;
    state.translationTarget=target;state.translationEnabled=true;
    if(btn){btn.classList.add("active");btn.textContent="TRANS:"+target.toUpperCase();}
    await translateCurrentOcr(true);
  }

  function handleFingerGesture(result){
    if(!state.gesturesEnabled)return;
    const name=String(result&&result.primary_gesture||"None"),confidence=Number(result&&result.primary_confidence||0);
    if(!name||name==="None"||confidence<0.65){state.gestureCandidate="NONE";state.gestureCandidateCount=0;return;}
    const key="HAND:"+name;
    if(key===state.gestureCandidate)state.gestureCandidateCount++;else{state.gestureCandidate=key;state.gestureCandidateCount=1;}
    if(state.gestureCandidateCount<2||Date.now()-state.lastGestureAt<3500)return;
    state.lastGestureAt=Date.now();state.lastGesture=name;state.gestureCandidateCount=0;
    if(name==="Pointing_Up")toggleTargetLock();
    else if(name==="Thumb_Up")photo();
    else if(name==="Victory")research();
    else if(name==="Closed_Fist")toggleTorch();
    else if(name==="Thumb_Down"&&state.lockedTrackingId!==null)toggleTargetLock();
  }

  async function handPerception(){
    if(!cameraActive()||!state.gesturesEnabled||state.handBusy||!window.Krishna||!Krishna.hawkeyeHandGesture)return;
    const frame=captureFrame(480,0.58);if(!frame||!frame.b64)return;
    state.handBusy=true;
    try{
      const result=JSON.parse(Krishna.hawkeyeHandGesture(frame.b64));
      if(result.error){state.handResult=null;return;}
      state.handResult=result;handleFingerGesture(result);if(state.rich)drawRich(state.rich);
    }catch(_){state.handResult=null;}
    finally{state.handBusy=false;}
  }

  function handleGesture(result){
    if(!state.gesturesEnabled)return;
    const g=result&&result.gesture||{},name=String(g.name||"NONE"),confidence=Number(g.confidence||0);
    if(name==="NONE"||confidence<0.65){state.gestureCandidate="NONE";state.gestureCandidateCount=0;return;}
    if(name===state.gestureCandidate)state.gestureCandidateCount++;else{state.gestureCandidate=name;state.gestureCandidateCount=1;}
    if(state.gestureCandidateCount<2||Date.now()-state.lastGestureAt<3500)return;
    state.lastGestureAt=Date.now();state.lastGesture=name;state.gestureCandidateCount=0;
    if(name==="LEFT_HAND_RAISED")toggleTargetLock();
    else if(name==="RIGHT_HAND_RAISED")photo();
    else if(name==="BOTH_HANDS_RAISED")research();
  }

  function toggleGestures(){
    state.gesturesEnabled=!state.gesturesEnabled;state.gestureCandidate="NONE";state.gestureCandidateCount=0;
    const btn=byId("cameraGesture");if(btn){btn.classList.toggle("active",state.gesturesEnabled);btn.textContent=state.gesturesEnabled?"GEST ON":"GEST";}
    if(typeof reply==="function")reply(state.gesturesEnabled
      ?"HAWKEYE hand gestures enabled. MediaPipe: Pointing Up=LOCK, Thumb Up=PHOTO+DATA, Victory=SEARCH, Closed Fist=LIGHT, Thumb Down=release LOCK. Pose hand-raise remains fallback."
      :"HAWKEYE gesture mode disabled.","good");
    if(state.gesturesEnabled)setTimeout(handPerception,80);else state.handResult=null;
  }

  async function toggleTorch(){
    if(!cameraActive())return;
    const track=fieldStream&&fieldStream.getVideoTracks()[0],btn=byId("cameraTorch");
    if(!track||!track.getCapabilities||!track.applyConstraints){if(typeof reply==="function")reply("Camera torch control is unavailable on this device.","warn");return;}
    const caps=track.getCapabilities();if(!caps||caps.torch!==true){if(typeof reply==="function")reply("This camera does not expose hardware torch control.","warn");return;}
    const wanted=!state.torchOn;
    try{
      await track.applyConstraints({advanced:[{torch:wanted}]});state.torchOn=wanted;
      if(btn){btn.classList.toggle("active",wanted);btn.textContent=wanted?"LIGHT ON":"LIGHT";}
    }catch(e){if(typeof reply==="function")reply("Torch: "+e.message,"warn");}
  }

  async function richPerception(){
    if(!cameraActive()||state.richBusy||!window.Krishna||!Krishna.hawkeyeRichPerception)return;
    const frame=captureFrame(720,0.62);if(!frame||!frame.b64)return;
    state.richBusy=true;
    try{
      const result=JSON.parse(Krishna.hawkeyeRichPerception(frame.b64));if(result.error)return;
      state.rich=result;drawRich(result);
      if(!state.handResult||!Number(state.handResult.hand_count||0))handleGesture(result);
      if(state.translationEnabled)await translateCurrentOcr(false);
      const parts=[];
      const text=String(result.ocr&&result.ocr.text||"").trim();if(text)parts.push("OCR: "+text.slice(0,180));
      if(Array.isArray(result.barcodes)&&result.barcodes.length)parts.push("Codes: "+result.barcodes.map(x=>String(x.value||"").slice(0,50)).filter(Boolean).join(" · "));
      if(result.recommended_next_scan)parts.push("Next view: "+result.recommended_next_scan);
      const probe=frameQuality(frame.canvas);if(probe.lowLight)parts.push("LOW LIGHT · use LIGHT if this phone exposes torch control");
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

  async function freeCloudTick(force=false){
    if(!cameraActive()||state.aiMode==="LOCAL"||state.freeCloudBusy||!state.cloudApproved||!window.Krishna||!Krishna.hawkeyeFreeCloudAnalyze)return;
    const sig=sceneSignature();if(state.aiMode==="AUTO"&&!force&&sig&&sig===state.lastFreeCloudSignature)return;
    const meta=geminiMetadata({source:"HAWKEYE_MOBILE_FREE_CLOUD"});
    if(meta.contains_biometrics||meta.contains_credentials||meta.private_document)return;
    const frame=await captureBestFrame(720,0.60,3);if(!frame||!frame.b64)return;
    const provider=state.aiMode==="OPENROUTER"?"openrouter":(state.aiMode==="GEMINI"?"gemini":"auto");
    state.freeCloudBusy=true;state.lastFreeCloudSignature=sig;
    try{
      const out=JSON.parse(Krishna.hawkeyeFreeCloudAnalyze(
        frame.b64,"image/jpeg",geminiPrompt(),JSON.stringify(meta),
        provider,"hawkeye_vision","",!!force
      ));
      if(out.error)throw new Error(out.error);
      state.freeCloudAnalysis=String(out.analysis||"").trim();
      state.lastFreeCloudProvider=String(out.provider||"free-cloud");
      state.lastFreeCloudModel=String(out.model||"");
      state.lastFreeCloudRole=String(out.role||"hawkeye_vision");
      state.lastFreeCloudReviews=Array.isArray(out.reviews)?out.reviews.slice(0,4):[];
      const local=state.localSummary?state.localSummary+"\n\n":"";
      const label=state.lastFreeCloudProvider+(state.lastFreeCloudModel?" · "+state.lastFreeCloudModel:"");
      let review="";
      if(state.lastFreeCloudReviews.length){
        review="\n\nReviewers: "+state.lastFreeCloudReviews.map(x=>String(x.provider_family||x.provider||"free")).join(", ");
      }
      if(state.freeCloudAnalysis)byId("cameraAnalysis").textContent=local+label+": "+state.freeCloudAnalysis+review;

      if(state.freeCloudAnalysis&&window.Krishna&&Krishna.hawkeyeFreeCloudFinding){
        try{
          const finding={
            analysis:state.freeCloudAnalysis,
            provider:state.lastFreeCloudProvider,
            model:state.lastFreeCloudModel,
            role:state.lastFreeCloudRole,
            reviews:state.lastFreeCloudReviews,
            local_context:richMetadata(),
            metadata:meta,
            zero_cost_verified:!!out.zero_cost_verified,
            selected_keyframe:true,
            scene_signature:sig
          };
          const pc=JSON.parse(Krishna.hawkeyeFreeCloudFinding(
            String(typeof fieldSession!=="undefined"?fieldSession:"field"),
            String(typeof fieldGoal!=="undefined"?fieldGoal:"live visual assistance"),
            JSON.stringify(finding)
          ));
          if(!pc.error)state.lastFreeCloudPc=pc;
        }catch(_){}
      }
    }catch(e){if(force&&typeof reply==="function")reply("HAWKEYE free cloud: "+e.message,"warn");}
    finally{state.freeCloudBusy=false;}
  }

  function pcOffloadContext(){
    const pc=state.lastFreeCloudPc||{};
    return {
      free_cloud_active:state.aiMode!=="LOCAL",
      analysis:String(state.freeCloudAnalysis||"").slice(0,4000),
      provider:String(state.lastFreeCloudProvider||""),
      model:String(state.lastFreeCloudModel||""),
      role:String(state.lastFreeCloudRole||""),
      pc_recorded:!!pc.pc_recorded,
      pc_observation_id:String(pc.observation_id||""),
      pc_session_id:String(pc.pc_session_id||""),
      scene_signature:String(state.lastFreeCloudSignature||""),
      local_vision_skip_recommended:!!(pc.pc_recorded&&state.freeCloudAnalysis)
    };
  }

  async function geminiTick(force=false){return freeCloudTick(force);}

  function toggleAI(){
    const order=["LOCAL","AUTO","OPENROUTER","GEMINI"];
    const at=Math.max(0,order.indexOf(state.aiMode));
    const next=order[(at+1)%order.length];
    state.aiMode=next;state.cloudApproved=next!=="LOCAL";
    const btn=byId("cameraAI");if(btn){btn.textContent="AI:"+next;btn.classList.toggle("active",next!=="LOCAL");}
    if(next==="LOCAL"){
      state.freeCloudAnalysis="";state.geminiAnalysis="";
      if(typeof reply==="function")reply("HAWKEYE cloud reasoning is off; ML Kit and MediaPipe stay local.","good");
    }else{
      const note=next==="AUTO"
        ?"AUTO uses verified zero-cost OpenRouter vision first, then Gemini fallback; selected non-sensitive frames only."
        :(next==="OPENROUTER"
          ?"OpenRouter vision uses the role-selected model only if the live catalog still reports zero cost."
          :"Gemini selected-keyframe mode enabled; sensitive scenes remain local.");
      if(typeof reply==="function")reply(note,"good");
      setTimeout(()=>freeCloudTick(true),80);
    }
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
      const url="wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained?access_token="+encodeURIComponent(token.token);
      const ws=new WebSocket(url);state.liveSocket=ws;
      const btn=byId("cameraGeminiLive");if(btn){btn.classList.add("active");btn.textContent="G-LIVE…";}
      ws.onopen=()=>{
        ws.send(JSON.stringify({setup:{model:"models/"+token.live_model,generationConfig:{responseModalities:["AUDIO"]},outputAudioTranscription:{}}}));
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
    if(/\bbook\b|textbook/.test(goal))return"book";
    if(/\bpage\b/.test(goal))return"page";
    if(/document|\bpdf\b|form|letter/.test(goal))return"document";
    if(/screen|display|monitor/.test(goal))return"screen";
    if(/video|film|watch/.test(goal))return"video";
    if(/listen|audio|sound/.test(goal))return"audio";
    if(/image|photo|picture/.test(goal))return"image";
    if(/object|device|machine|car|vehicle|tree|flower|animal|circuit/.test(goal))return"object";
    return"camera";
  }

  function currentAnalysis(){
    return String(byId("cameraAnalysis")?.textContent||"").trim();
  }

  function learningAnalysis(){
    return currentAnalysis()
      .split("\nLearning route:")[0]
      .split("\nKnowledge status:")[0]
      .split("\nResearch:")[0]
      .trim();
  }

  function publicClues(){
    const clues=[];
    const add=value=>{
      const text=String(value||"").replace(/\s+/g," ").trim();
      if(!text||/\[SECRET REDACTED\]|\[WIFI CREDENTIAL REDACTED\]/i.test(text))return;
      if(!clues.includes(text))clues.push(text.slice(0,240));
    };
    const rich=state.rich||{},ocr=rich.ocr||{};
    for(const block of (Array.isArray(ocr.blocks)?ocr.blocks:[]))add(block&&block.text);
    for(const code of (Array.isArray(rich.barcodes)?rich.barcodes:[]))add(code&&code.value);
    return clues.slice(0,12);
  }

  async function learningTick(force=false){
    if(!cameraActive()||(!state.learn&&!force)||!window.Krishna||!Krishna.hawkeyeObserveLearning)return;
    const analysis=learningAnalysis();
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
        public_clues:publicClues(),
        outcome:"finding",
        contradictions:[],
        lessons:[]
      };
      const learned=JSON.parse(Krishna.hawkeyeObserveLearning(JSON.stringify(payload)));
      if(learned.error)throw new Error(learned.error);
      state.researchQueries=learned.research_plan&&Array.isArray(learned.research_plan.queries)?learned.research_plan.queries:[];
      if(learned.lead_rishi){
        const team=Array.isArray(learned.rishi_team)&&learned.rishi_team.length?" · "+learned.rishi_team.join(", "):"";
        const base=learningAnalysis();
        const status=String(learned.knowledge_status||"candidate");
        const verification=learned.verification_required===false?"":" / verification required";
        byId("cameraAnalysis").textContent=base+"\nLearning route: "+learned.lead_rishi+team+"\nKnowledge status: "+status+verification;
      }
      if(learned.research_required&&learned.observation_id&&Krishna.hawkeyeResearchObservation){
        try{
          const queued=JSON.parse(Krishna.hawkeyeResearchObservation(String(learned.observation_id)));
          if(queued.queued){
            byId("cameraAnalysis").textContent=currentAnalysis().split("\nResearch:")[0]+
              "\nResearch: queued · local-first Rishi/Garuda/Gautama verification";
          }
        }catch(_){}
      }
    }catch(_){}
  }

  function onResearchResult(raw){
    let result={};
    try{result=typeof raw==="string"?JSON.parse(raw):raw||{};}catch(_){result={error:"invalid research result"};}
    const box=byId("cameraAnalysis");if(!box)return;
    const base=currentAnalysis().split("\nResearch:")[0];
    if(result.error){
      box.textContent=base+"\nResearch: failed · candidate retained · "+String(result.error).slice(0,180);
      return;
    }
    const status=String(result.status||"COMPLETED").toLowerCase();
    const knowledge=String(result.knowledge_status||"candidate");
    const proposals=Number(result.gyan_proposal_count||((result.gyan_proposal_ids||[]).length)||0);
    const contradiction=Number(result.unresolved_contradictions||0);
    box.textContent=base+"\nResearch: "+status+" · "+knowledge+
      (proposals?" · Gyan proposals "+proposals:"")+
      (contradiction?" · contradictions "+contradiction:"");
  }

  function sensorSnapshot(){
    try{
      if(window.Krishna&&Krishna.hawkeyeSensorSnapshot){
        const out=JSON.parse(Krishna.hawkeyeSensorSnapshot());
        return out&&typeof out==="object"?out:{available:false};
      }
    }catch(_){}
    return {available:false,evidence_state:"UNKNOWN",pose_authority:false,survey_grade:false};
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
      gemini_analysis:String(state.geminiAnalysis||"").slice(0,2000),
      free_cloud_analysis:String(state.freeCloudAnalysis||"").slice(0,2000),
      translation:{enabled:state.translationEnabled,target:state.translationTarget,text:String(state.translationText||"").slice(0,1500)},
      gestures:{enabled:state.gesturesEnabled,scope:state.handResult?"mediapipe-hand-finger":"upper-body-pose-fallback",last:state.lastGesture},
      torch_on:state.torchOn,
      sensor_fusion:sensorSnapshot(),
      spatial_handoff:{bhumiputra_ready:true,slam_pose_claimed:false,depth_claimed:false,survey_grade:false},
      privacy:{unknown_face_capture_masking:true,raw_cloud_upload:false}
    };
  }

  function maskUnknownFaces(ctx,sourceCanvas){
    const faces=state.rich&&Array.isArray(state.rich.faces)?state.rich.faces:[];
    if(!faces.length)return 0;
    let count=0;
    for(const face of faces){
      const b=face&&face.bbox;if(!Array.isArray(b)||b.length!==4)continue;
      const pad=.025,x=Math.max(0,(Number(b[0])||0)-pad),y=Math.max(0,(Number(b[1])||0)-pad);
      const w=Math.min(1-x,(Number(b[2])||0)+pad*2),h=Math.min(1-y,(Number(b[3])||0)+pad*2);
      const sx=Math.round(x*sourceCanvas.width),sy=Math.round(y*sourceCanvas.height),sw=Math.max(1,Math.round(w*sourceCanvas.width)),sh=Math.max(1,Math.round(h*sourceCanvas.height));
      ctx.save();ctx.filter="blur(18px)";ctx.drawImage(sourceCanvas,sx,sy,sw,sh,sx,sy,sw,sh);ctx.restore();count++;
    }
    return count;
  }

  async function photo(){
    if(!cameraActive()||!Krishna.saveHawkeyeCapture)return;
    const v=video();if(!v||!v.videoWidth||!v.videoHeight)return;
    try{
      const best=await captureBestFrame(1280,0.90,4);if(!best)throw new Error("camera frame unavailable");
      const c=document.createElement("canvas");c.width=best.canvas.width;c.height=best.canvas.height;
      const ctx=c.getContext("2d",{alpha:false});ctx.drawImage(best.canvas,0,0,c.width,c.height);
      const source=document.createElement("canvas");source.width=c.width;source.height=c.height;source.getContext("2d",{alpha:false}).drawImage(c,0,0);
      const masked=maskUnknownFaces(ctx,source);
      for(const id of ["diagnosticOverlay","objectOverlay","richOverlay"]){
        const overlay=byId(id);if(overlay&&overlay.width&&overlay.height)ctx.drawImage(overlay,0,0,c.width,c.height);
      }
      const meta=metadata();meta.capture_quality=best.quality;meta.privacy_faces_masked=masked>0;meta.privacy_face_count=masked;
      const caption=String(meta.analysis||"").replace(/\s+/g," ").slice(0,180);
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

  function toggleTargetLock(){
    const btn=byId("cameraLock");
    if(state.lockedTrackingId!==null){
      state.lockedTrackingId=null;
      if(btn){btn.classList.remove("active");btn.textContent="LOCK";}
      if(typeof reply==="function")reply("HAWKEYE target lock released.","good");
      return;
    }
    let best=null,bestArea=-1;
    for(const item of state.objects||[]){
      const b=item&&item.bbox;if(!Array.isArray(b)||b.length!==4||item.tracking_id===null||item.tracking_id===undefined)continue;
      const area=Math.max(0,Number(b[2])||0)*Math.max(0,Number(b[3])||0);
      if(area>bestArea){bestArea=area;best=item;}
    }
    if(!best){if(typeof reply==="function")reply("No trackable target is visible yet.","warn");return;}
    state.lockedTrackingId=best.tracking_id;
    if(btn){btn.classList.add("active");btn.textContent="LOCK #"+best.tracking_id;}
    if(typeof reply==="function")reply("HAWKEYE locked target #"+best.tracking_id+". Auto zoom will follow this tracking ID.","good");
  }

  function research(){
    const labels=state.objects.map(x=>String(x.label||"")).filter(Boolean);
    const ocr=String(state.rich&&state.rich.ocr&&state.rich.ocr.text||"").replace(/\s+/g," ").trim();
    const codes=(state.rich&&Array.isArray(state.rich.barcodes)?state.rich.barcodes:[]).map(x=>String(x.value||"")).filter(x=>x&&!x.includes("[")).join(" ");
    const initial=state.researchQueries[0]||codes||ocr.slice(0,180)||labels.join(" ")||String(typeof fieldGoal!=="undefined"?fieldGoal:"current observed object");
    const q=(prompt("Research what HAWKEYE is seeing:",initial)||"").trim();if(!q)return;
    try{
      const out=JSON.parse(Krishna.openResearchQuery(q));if(out.error)throw new Error(out.error);
      if(typeof reply==="function")reply("Research opened in your browser session.","good");
    }catch(e){if(typeof reply==="function")reply("Research: "+e.message,"bad");}
  }

  function isLearning(){return !!state.learn;}

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
    state.handTimer=setInterval(handPerception,900);
    state.learnTimer=setInterval(()=>learningTick(false),6000);
    state.freeCloudTimer=setInterval(()=>freeCloudTick(false),8000);
    setTimeout(detect,300);setTimeout(richPerception,650);
  }
  function deactivate(){
    if(!state.active)return;state.active=false;
    clearInterval(state.objectTimer);clearInterval(state.learnTimer);clearInterval(state.richTimer);clearInterval(state.handTimer);clearInterval(state.geminiTimer);clearInterval(state.freeCloudTimer);
    state.objectTimer=state.learnTimer=state.richTimer=state.handTimer=state.geminiTimer=state.freeCloudTimer=null;
    stopGeminiLive();
    if(state.torchOn&&fieldStream){try{const t=fieldStream.getVideoTracks()[0];if(t&&t.applyConstraints)t.applyConstraints({advanced:[{torch:false}]});}catch(_){}}
    state.objects=[];state.researchQueries=[];state.lastLearnText="";state.rich=null;state.handResult=null;state.localSummary="";state.geminiAnalysis="";state.freeCloudAnalysis="";state.lastFreeCloudSignature="";state.lastFreeCloudProvider="";state.lastFreeCloudModel="";state.lastFreeCloudRole="";state.lastFreeCloudReviews=[];state.lastFreeCloudPc=null;
    state.aiMode="LOCAL";state.cloudApproved=false;state.lockedTrackingId=null;
    state.translationEnabled=false;state.translationText="";state.translationSource="";state.translationBusy=false;
    state.gesturesEnabled=false;state.gestureCandidate="NONE";state.gestureCandidateCount=0;state.lastGesture="NONE";state.torchOn=false;
    for(const id of ["objectOverlay","richOverlay"]){const c=byId(id);if(c){const ctx=c.getContext("2d");ctx.clearRect(0,0,c.width,c.height);}}
    if(state.recorder)stopRecording();
    state.learn=false;const btn=byId("cameraLearn");if(btn){btn.classList.remove("active");btn.textContent="LEARN";}
    const ai=byId("cameraAI");if(ai){ai.classList.remove("active");ai.textContent="AI:LOCAL";}
    const lock=byId("cameraLock");if(lock){lock.classList.remove("active");lock.textContent="LOCK";}
    const trans=byId("cameraTranslate");if(trans){trans.classList.remove("active");trans.textContent="TRANS";}
    const gest=byId("cameraGesture");if(gest){gest.classList.remove("active");gest.textContent="GEST";}
    const torch=byId("cameraTorch");if(torch){torch.classList.remove("active");torch.textContent="LIGHT";}
  }

  setInterval(()=>{if(cameraActive())activate();else deactivate();},500);

  window.HawkeyeObserverUI={isLearning,toggleLearn,research,photo,photographerPhoto,record,detect,richPerception,learningTick,onResearchResult,toggleAI,freeCloudTick,pcOffloadContext,geminiTick,toggleGeminiLive,stopGeminiLive,toggleTargetLock,toggleTranslation,toggleGestures,toggleTorch,captureBestFrame,handPerception};
})();
