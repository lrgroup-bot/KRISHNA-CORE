(() => {
  "use strict";

  const histories=new Map();
  const MAX_HISTORY=6;

  const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,Number(v)||0));
  const area=b=>Array.isArray(b)&&b.length===4?Math.max(0,Number(b[2])||0)*Math.max(0,Number(b[3])||0):0;
  const center=b=>Array.isArray(b)&&b.length===4?[clamp((Number(b[0])||0)+(Number(b[2])||0)/2),clamp((Number(b[1])||0)+(Number(b[3])||0)/2)]:[.5,.5];
  const boxValid=b=>Array.isArray(b)&&b.length===4&&Number(b[2])>0&&Number(b[3])>0;

  function pointMap(hand){
    const out=new Map();
    for(const p of (hand&&Array.isArray(hand.landmarks)?hand.landmarks:[])){
      const i=Number(p&&p.index);if(!Number.isFinite(i))continue;
      out.set(i,{x:clamp(p.x),y:clamp(p.y),z:Number(p.z)||0});
    }
    return out;
  }

  function pointingRay(handResult){
    let best=null;
    for(const hand of (handResult&&Array.isArray(handResult.hands)?handResult.hands:[])){
      const pts=pointMap(hand),pip=pts.get(6),dip=pts.get(7),tip=pts.get(8),mcp=pts.get(5);
      if(!tip||(!dip&&!pip)||!mcp)continue;
      const base=dip||pip;
      let dx=tip.x-base.x,dy=tip.y-base.y;
      const mag=Math.hypot(dx,dy);if(mag<.025)continue;
      dx/=mag;dy/=mag;
      const straight=Math.hypot(tip.x-mcp.x,tip.y-mcp.y);
      const confidence=clamp(.35+Math.min(.65,straight*2.4));
      const row={origin:{x:tip.x,y:tip.y},dir:{x:dx,y:dy},confidence,handedness:String(hand.handedness||"UNKNOWN")};
      if(!best||row.confidence>best.confidence)best=row;
    }
    return best;
  }

  function rayScore(ray,bbox){
    if(!ray||!boxValid(bbox))return null;
    const c=center(bbox),vx=c[0]-ray.origin.x,vy=c[1]-ray.origin.y;
    const t=vx*ray.dir.x+vy*ray.dir.y;
    if(t<-.03)return null;
    const perp=Math.abs(vx*ray.dir.y-vy*ray.dir.x);
    const halfDiag=.5*Math.hypot(Number(bbox[2])||0,Number(bbox[3])||0);
    const tolerance=Math.max(.035,halfDiag*.9);
    if(perp>tolerance)return null;
    return 20 - 18*perp - 1.4*Math.max(0,t) + Math.min(2,area(bbox)*8);
  }

  function autoScore(item){
    if(!item||!boxValid(item.bbox))return -1e9;
    const a=area(item.bbox),c=center(item.bbox),d=Math.hypot(c[0]-.5,c[1]-.5);
    const ideal=1-Math.min(1,Math.abs(a-.22)/.22);
    const top=Array.isArray(item.labels)&&item.labels.length?item.labels[0]:null;
    const conf=clamp(top&&top.confidence,0,1);
    return 3.2*(1-Math.min(1,d/.7))+2.2*ideal+1.2*conf+Math.min(1.2,a*4);
  }

  function targetKey(item){
    if(!item)return "";
    if(item.tracking_id!==null&&item.tracking_id!==undefined)return "track:"+String(item.tracking_id);
    const b=item.bbox||[],q=b.map(x=>Math.round((Number(x)||0)*20)).join("-");
    return "box:"+String(item.label||"object").toLowerCase()+":"+q;
  }

  function selectTarget(objects,handResult,lockedTrackingId){
    const rows=(objects||[]).filter(x=>x&&boxValid(x.bbox));
    const ray=pointingRay(handResult);
    if(ray){
      let pointed=null,score=-1e9;
      for(const item of rows){
        const s=rayScore(ray,item.bbox);
        if(s!==null&&s>score){score=s;pointed=item;}
      }
      if(pointed)return {item:pointed,source:"POINTED",ray,key:targetKey(pointed),score};
    }
    if(lockedTrackingId!==null&&lockedTrackingId!==undefined){
      const locked=rows.find(x=>x.tracking_id===lockedTrackingId);
      if(locked)return {item:locked,source:"LOCKED",ray,key:targetKey(locked),score:50};
    }
    let best=null,score=-1e9;
    for(const item of rows){const s=autoScore(item);if(s>score){score=s;best=item;}}
    return best?{item:best,source:"AUTO",ray,key:targetKey(best),score}:null;
  }

  function normalizeText(value){
    return String(value||"")
      .replace(/\[SECRET REDACTED\]|\[WIFI CREDENTIAL REDACTED\]/gi,"")
      .replace(/\s+/g," ").trim().slice(0,1800);
  }
  function tokens(value){
    return new Set(normalizeText(value).toLowerCase().match(/[a-z0-9][a-z0-9._/-]{1,}/g)||[]);
  }
  function similarity(a,b){
    const A=tokens(a),B=tokens(b);if(!A.size||!B.size)return 0;
    let inter=0;for(const x of A)if(B.has(x))inter++;
    return inter/Math.max(A.size,B.size);
  }

  function decodedBarcodes(read){
    const out=[];
    for(const row of (read&&Array.isArray(read.barcodes)?read.barcodes:[])){
      const value=String(row&&row.value||"").trim();
      if(value&&value!=="[WIFI CREDENTIAL REDACTED]"&&!out.includes(value))out.push(value);
    }
    return out.slice(0,8);
  }

  function extract(text,codes){
    const src=normalizeText(text),get=(re)=>{const m=src.match(re);return m?String(m[2]||m[1]||"").trim().slice(0,120):"";};
    const model=get(/\b(model(?:\s*(?:no|number))?|mdl)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/-]{2,})/i);
    const serial=get(/\b(s\/?n|serial(?:\s*(?:no|number))?)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/-]{3,})/i);
    const input=get(/\b(input)\s*[:#-]?\s*([^;|]{3,80})/i);
    const output=get(/\b(output)\s*[:#-]?\s*([^;|]{3,80})/i);
    const watt=(src.match(/\b\d+(?:\.\d+)?\s*W(?:ATT)?S?\b/i)||[])[0]||"";
    const voltage=(src.match(/\b\d+(?:\.\d+)?\s*V(?:DC|AC)?\b/i)||[])[0]||"";
    const current=(src.match(/\b\d+(?:\.\d+)?\s*(?:mA|A)\b/i)||[])[0]||"";
    const lines=src.split(/(?<=[.:])\s+|\s{2,}/).filter(Boolean);
    const name=(lines.find(x=>x.length>=4&&x.length<=90&&!/^(model|serial|s\/n|input|output)\b/i.test(x))||"").slice(0,90);
    return {name,model,serial,input,output,power:watt,voltage,current,barcode:codes[0]||""};
  }

  function registerRead(selection,read,quality){
    if(!selection||!selection.key)return {state:"SEARCH",complete:false,confidence:0,details:{},text:"",barcodes:[]};
    const key=selection.key,now=Date.now(),text=normalizeText(read&&read.ocr&&read.ocr.text),codes=decodedBarcodes(read);
    let h=histories.get(key);
    if(!h)h={createdAt:now,rows:[],complete:false,details:{},lastSeen:now};
    h.lastSeen=now;
    h.rows.push({at:now,text,codes,quality:quality||{}});
    if(h.rows.length>MAX_HISTORY)h.rows.splice(0,h.rows.length-MAX_HISTORY);

    let textVotes=0,bestText=text;
    for(let i=0;i<h.rows.length;i++){
      const candidate=h.rows[i].text;if(candidate.length>bestText.length)bestText=candidate;
      if(text.length>=8&&similarity(text,candidate)>=.80)textVotes++;
    }
    const codeCounts=new Map();
    for(const row of h.rows)for(const c of row.codes)codeCounts.set(c,(codeCounts.get(c)||0)+1);
    let bestCode="",bestCodeVotes=0;
    for(const [c,n] of codeCounts)if(n>bestCodeVotes){bestCode=c;bestCodeVotes=n;}
    const q=quality||{},readable=bestText.replace(/[^A-Za-z0-9]/g,"").length>=8;
    const stableText=readable&&textVotes>=2;
    const stableCode=!!bestCode&&bestCodeVotes>=1;
    const age=now-h.createdAt;
    h.complete=age>=180&&(stableText||stableCode);
    h.details=extract(bestText,bestCode?[bestCode]:codes);
    const confidence=clamp((stableText?.55:0)+(stableCode?.35:0)+Math.min(.1,Number(q.score||0)*.1));
    histories.set(key,h);
    return {
      state:h.complete?"COMPLETE":"READING",
      complete:h.complete,
      confidence,
      details:h.details,
      text:bestText,
      barcodes:bestCode?[bestCode]:codes,
      samples:h.rows.length,
      age_ms:age,
      quality:q,
    };
  }

  function recovery(readResult,quality,selection){
    if(readResult&&readResult.complete)return {state:"COMPLETE",actions:[]};
    const q=quality||{},actions=[];
    if(q.lowLight||Number(q.brightness||0)<48)actions.push("LIGHT");
    if(Number(q.detail||0)<.22)actions.push("REFOCUS");
    const a=selection&&selection.item?area(selection.item.bbox):0;
    if(a>0&&a<.16)actions.push("ZOOM_IN");
    if(a>.55)actions.push("ZOOM_OUT");
    if(!(readResult&&readResult.text)&&!(readResult&&readResult.barcodes&&readResult.barcodes.length))actions.push("ENHANCE");
    if(!actions.length)actions.push("MULTIFRAME_RETRY");
    return {state:"RECOVER",actions:[...new Set(actions)]};
  }

  function zoomFactor(selection,readResult){
    if(!selection||!selection.item)return 1;
    const a=area(selection.item.bbox);if(a<=0)return 1;
    let factor=1;
    if(a<.08)factor=Math.min(2.2,Math.sqrt(.18/a));
    else if(a<.16)factor=Math.min(1.6,Math.sqrt(.20/a));
    else if(a>.55)factor=.88;
    if(readResult&&!readResult.complete&&readResult.samples>=2&&a<.28)factor=Math.max(factor,1.12);
    return factor;
  }

  function prune(){
    const now=Date.now();
    for(const [k,v] of histories)if(now-(v.lastSeen||0)>30000)histories.delete(k);
  }

  function status(){
    prune();
    return {schema:"hawkeye.active-vision.v1",histories:histories.size,max_history:MAX_HISTORY};
  }

  window.HawkeyeActiveVision={
    selectTarget,targetKey,registerRead,recovery,zoomFactor,pointingRay,status,area,center,
    reset:key=>{if(key)histories.delete(key);else histories.clear();}
  };
})();