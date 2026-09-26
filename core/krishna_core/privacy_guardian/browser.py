from __future__ import annotations

import hashlib
import json
from urllib.parse import urlsplit

from .models import PrivacyFinding, PrivacyRiskClass


BROWSER_EXPOSURE_JS=r"""async () => {
  const safe = async (fn, fallback=null) => {
    try { return await fn(); } catch (_) { return fallback; }
  };
  const bounded = async (fn, ms, fallback=null) => {
    try {
      return await Promise.race([
        Promise.resolve().then(fn),
        new Promise(resolve=>setTimeout(()=>resolve(fallback),ms))
      ]);
    } catch (_) { return fallback; }
  };
  const canvas = await safe(() => {
    const c=document.createElement('canvas'); c.width=320; c.height=80;
    const x=c.getContext('2d'); x.textBaseline='top'; x.font='18px Arial';
    x.fillStyle='#f60'; x.fillRect(0,0,120,24);
    x.fillStyle='#069'; x.fillText('KRISHNA privacy Ω 😀',4,28);
    return c.toDataURL();
  });
  const webgl = await safe(() => {
    const c=document.createElement('canvas');
    const gl=c.getContext('webgl')||c.getContext('experimental-webgl');
    if (!gl) return {available:false};
    const ext=gl.getExtension('WEBGL_debug_renderer_info');
    return {
      available:true,
      vendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : null,
      renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null,
      version: gl.getParameter(gl.VERSION),
      shading: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
      maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
      maxRenderbufferSize: gl.getParameter(gl.MAX_RENDERBUFFER_SIZE)
    };
  });
  const audio = await bounded(async () => {
    const C=window.OfflineAudioContext||window.webkitOfflineAudioContext;
    if (!C) return {available:false};
    const ctx=new C(1,44100,44100);
    const osc=ctx.createOscillator(), comp=ctx.createDynamicsCompressor();
    osc.type='triangle'; osc.frequency.value=10000;
    osc.connect(comp); comp.connect(ctx.destination); osc.start(0);
    const rendered=await ctx.startRendering();
    const data=rendered.getChannelData(0);
    let sum=0; for(let i=0;i<data.length;i+=64) sum+=Math.abs(data[i]);
    return {available:true,sample:sum.toFixed(8)};
  },1800,{available:false,timedOut:true});
  const rect = await safe(() => {
    const d=document.createElement('div');
    d.style.cssText='position:absolute;left:-9999px;width:123.45px;height:67.89px;font:17px Arial';
    d.textContent='KRISHNA Ω'; document.body.appendChild(d);
    const r=d.getBoundingClientRect(); d.remove();
    return {width:r.width,height:r.height};
  });
  const textMetrics = await safe(() => {
    const c=document.createElement('canvas'), x=c.getContext('2d');
    x.font='17px Arial'; const m=x.measureText('KRISHNA Ω 😀');
    return {width:m.width,actualBoundingBoxAscent:m.actualBoundingBoxAscent,actualBoundingBoxDescent:m.actualBoundingBoxDescent};
  });
  const permissionNames=['camera','microphone','geolocation','notifications','clipboard-read','clipboard-write','midi','persistent-storage'];
  const permissionRows=await Promise.all(permissionNames.map(async name=>[
    name,
    await bounded(async()=>navigator.permissions ? (await navigator.permissions.query({name})).state : 'unsupported',700,'timeout')
  ]));
  const permissions=Object.fromEntries(permissionRows);
  const voices=await safe(()=>speechSynthesis.getVoices().map(v=>({lang:v.lang,local:v.localService,name:v.name})).slice(0,100),[]);
  const storage={
    localStorage:await safe(()=>{localStorage.setItem('__krishna_privacy_test','1');localStorage.removeItem('__krishna_privacy_test');return true},false),
    sessionStorage:await safe(()=>{sessionStorage.setItem('__krishna_privacy_test','1');sessionStorage.removeItem('__krishna_privacy_test');return true},false),
    indexedDB:!!window.indexedDB,
    cacheStorage:!!window.caches,
    serviceWorker:!!navigator.serviceWorker,
    broadcastChannel:!!window.BroadcastChannel,
    sharedWorker:!!window.SharedWorker,
    storageAccessAPI:typeof document.hasStorageAccess==='function',
  };
  const supportedApis={
    bluetooth:!!navigator.bluetooth, usb:!!navigator.usb, serial:!!navigator.serial,
    mediaDevices:!!navigator.mediaDevices, webgl:!!webgl?.available,
    webgpu:!!navigator.gpu, clipboard:!!navigator.clipboard,
    screenCapture:!!navigator.mediaDevices?.getDisplayMedia,
  };
  return {
    userAgent:navigator.userAgent,
    userAgentData:await safe(()=>navigator.userAgentData ? {
      brands:navigator.userAgentData.brands, mobile:navigator.userAgentData.mobile, platform:navigator.userAgentData.platform
    }:null),
    language:navigator.language,
    languages:Array.from(navigator.languages||[]),
    platform:navigator.platform,
    timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen:{
      width:screen.width,height:screen.height,availWidth:screen.availWidth,availHeight:screen.availHeight,
      pixelRatio:window.devicePixelRatio,colorDepth:screen.colorDepth,pixelDepth:screen.pixelDepth
    },
    hardwareConcurrency:navigator.hardwareConcurrency||null,
    deviceMemory:navigator.deviceMemory||null,
    maxTouchPoints:navigator.maxTouchPoints||0,
    prefersDark:matchMedia('(prefers-color-scheme: dark)').matches,
    reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,
    pdfViewerEnabled:navigator.pdfViewerEnabled ?? null,
    plugins:Array.from(navigator.plugins||[]).map(x=>x.name).slice(0,50),
    mimeTypes:Array.from(navigator.mimeTypes||[]).map(x=>x.type).slice(0,100),
    voices:voices,
    webgl:webgl,
    canvas:canvas,
    audio:audio,
    domRect:rect,
    textMetrics:textMetrics,
    gpc:navigator.globalPrivacyControl ?? null,
    dnt:navigator.doNotTrack ?? null,
    permissions:permissions,
    storage:storage,
    supportedApis:supportedApis,
    cookieEnabled:navigator.cookieEnabled,
    webdriver:navigator.webdriver,
    javaEnabled:await safe(()=>navigator.javaEnabled(),false),
  };
}"""


WEBRTC_JS=r"""async () => {
  if (!window.RTCPeerConnection) return {available:false,candidates:[]};
  const pc=new RTCPeerConnection({iceServers:[]});
  const candidates=[];
  pc.createDataChannel('krishna-privacy');
  pc.onicecandidate=e=>{ if(e.candidate) candidates.push(e.candidate.candidate); };
  try {
    await pc.setLocalDescription(await pc.createOffer());
    await new Promise(resolve=>setTimeout(resolve,1200));
  } finally {
    pc.close();
  }
  const types=candidates.map(x => {
    const m=x.match(/ typ (host|srflx|relay|prflx)/); return m ? m[1] : 'unknown';
  });
  return {
    available:true,
    candidateTypes:Array.from(new Set(types)),
    candidateCount:candidates.length,
    hostExposed:types.includes('host'),
    publicCandidateExposed:types.includes('srflx'),
    relayObserved:types.includes('relay'),
    mdnsMasked:candidates.some(x=>x.includes('.local')),
    rawCandidateValuesStored:false
  };
}"""


def _hash(value) -> str:
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def local_fingerprint_identifier(observation: dict) -> dict:
    selected={
        "ua":observation.get("userAgent"),
        "ua_data":observation.get("userAgentData"),
        "language":observation.get("language"),
        "languages":observation.get("languages"),
        "platform":observation.get("platform"),
        "timezone":observation.get("timezone"),
        "screen":observation.get("screen"),
        "hardwareConcurrency":observation.get("hardwareConcurrency"),
        "deviceMemory":observation.get("deviceMemory"),
        "maxTouchPoints":observation.get("maxTouchPoints"),
        "webgl":observation.get("webgl"),
        "canvas_sha256":_hash(observation.get("canvas")) if observation.get("canvas") else None,
        "audio":observation.get("audio"),
        "domRect":observation.get("domRect"),
        "textMetrics":observation.get("textMetrics"),
    }
    return {
        "algorithm":"sha256-local-v1",
        "identifier":_hash(selected),
        "signal_names":[k for k,v in selected.items() if v is not None],
        "uploaded":False,
    }


def summarize_browser_observation(observation: dict, *, profile: str, url: str,
                                  webrtc: dict|None=None, request_urls: list[str]|None=None) -> dict:
    obs=dict(observation or {})
    findings=[]
    webgl=obs.get("webgl") or {}
    canvas=obs.get("canvas")
    audio=obs.get("audio") or {}
    permissions=obs.get("permissions") or {}
    storage=obs.get("storage") or {}
    gpc=obs.get("gpc")
    fingerprint=local_fingerprint_identifier(obs)

    def add(test,state,summary,risk,evidence=None,recommendation="",limitations=None):
        findings.append(PrivacyFinding(
            test=test,state=state,summary=summary,risk_class=risk,
            evidence=evidence or {},recommendation=recommendation,
            limitations=list(limitations or []),
            source_methodology="KRISHNA Fingerprint Surface Inspector; CreepJS/PrivacyTests/FingerprintJS methodology inspiration",
            sensitive=test.startswith("browser.fingerprint"),
        ).as_dict())

    add("browser.gpc",
        "enabled" if gpc is True else ("disabled" if gpc is False else "unsupported"),
        "Global Privacy Control is enabled." if gpc is True else ("Global Privacy Control is disabled." if gpc is False else "Global Privacy Control is not exposed by this browser context."),
        PrivacyRiskClass.LOW_EXPOSURE if gpc is True else PrivacyRiskClass.INCONCLUSIVE,
        {"javascript_state":"enabled" if gpc is True else ("disabled" if gpc is False else "unsupported")},
        "Use a GPC-capable browser configuration if that signal matches the owner's preference." if gpc is not True else "")
    add("browser.webgl",
        "available" if webgl.get("available") else "blocked",
        "WebGL renderer information is exposed." if webgl.get("renderer") else ("WebGL is available with limited renderer detail." if webgl.get("available") else "WebGL is unavailable/blocked."),
        PrivacyRiskClass.MODERATE_EXPOSURE if webgl.get("renderer") else PrivacyRiskClass.LOW_EXPOSURE,
        {"available":bool(webgl.get("available")),"renderer_exposed":bool(webgl.get("renderer")),"vendor_exposed":bool(webgl.get("vendor"))})
    add("browser.canvas",
        "available" if canvas else "blocked",
        "Canvas rendering is available to page JavaScript." if canvas else "Canvas probe was unavailable.",
        PrivacyRiskClass.MODERATE_EXPOSURE if canvas else PrivacyRiskClass.LOW_EXPOSURE,
        {"available":bool(canvas),"sample_sha256":_hash(canvas) if canvas else None},
        limitations=["A single run cannot establish whether canvas is stable, randomized, or standardized. Compare profiles/runs."])
    add("browser.audio_context",
        "available" if audio.get("available") else "blocked",
        "AudioContext rendering is available." if audio.get("available") else "AudioContext probe was unavailable.",
        PrivacyRiskClass.MODERATE_EXPOSURE if audio.get("available") else PrivacyRiskClass.LOW_EXPOSURE,
        {"available":bool(audio.get("available")),"sample_sha256":_hash(audio.get("sample")) if audio.get("sample") else None},
        limitations=["A single run does not establish cross-session stability."])
    add("browser.permissions","observed",
        "Browser permission-query states were inspected without activating hardware.",
        PrivacyRiskClass.LOW_EXPOSURE,
        {"states":permissions})
    add("browser.storage","observed",
        "Browser storage API availability was inspected using temporary test keys only.",
        PrivacyRiskClass.LOW_EXPOSURE,
        {"capabilities":storage})
    if webrtc:
        state="unsupported" if not webrtc.get("available") else "observed"
        risk=PrivacyRiskClass.MODERATE_EXPOSURE if webrtc.get("publicCandidateExposed") or (webrtc.get("hostExposed") and not webrtc.get("mdnsMasked")) else PrivacyRiskClass.LOW_EXPOSURE
        add("browser.webrtc",state,
            "WebRTC candidate types were inspected; raw candidate values were not retained.",
            risk,
            {k:webrtc.get(k) for k in ("available","candidateTypes","candidateCount","hostExposed","publicCandidateExposed","relayObserved","mdnsMasked")},
            "Review browser/VPN WebRTC configuration if an unexpected public or unmasked host candidate appears." if risk==PrivacyRiskClass.MODERATE_EXPOSURE else "")
    third_party=[]
    target_host=(urlsplit(url).hostname or "").lower()
    for raw in request_urls or []:
        h=(urlsplit(raw).hostname or "").lower()
        if h and target_host and h!=target_host and not h.endswith("."+target_host):
            third_party.append(h)
    add("browser.third_party_requests","observed",
        f"{len(set(third_party))} third-party domain(s) were observed in this controlled page load.",
        PrivacyRiskClass.MODERATE_EXPOSURE if third_party else PrivacyRiskClass.LOW_EXPOSURE,
        {"third_party_domains":sorted(set(third_party))[:100],"raw_urls_stored":False})
    return {
        "profile":profile,
        "url":url,
        "fingerprint":fingerprint,
        "browser":{
            "userAgent":obs.get("userAgent"),
            "userAgentData":obs.get("userAgentData"),
            "language":obs.get("language"),
            "languages":obs.get("languages"),
            "platform":obs.get("platform"),
            "timezone":obs.get("timezone"),
            "screen":obs.get("screen"),
            "hardwareConcurrency":obs.get("hardwareConcurrency"),
            "deviceMemory":obs.get("deviceMemory"),
            "maxTouchPoints":obs.get("maxTouchPoints"),
            "gpc":obs.get("gpc"),
            "dnt":obs.get("dnt"),
            "webdriver":obs.get("webdriver"),
        },
        "surfaces":{
            "webgl":webgl,
            "canvas":{"available":bool(canvas),"sha256":_hash(canvas) if canvas else None},
            "audio":{"available":bool(audio.get("available")),"sha256":_hash(audio.get("sample")) if audio.get("sample") else None},
            "domRect":obs.get("domRect"),
            "textMetrics":obs.get("textMetrics"),
            "voices_count":len(obs.get("voices") or []),
            "plugins_count":len(obs.get("plugins") or []),
            "mime_types_count":len(obs.get("mimeTypes") or []),
            "supportedApis":obs.get("supportedApis") or {},
        },
        "permissions":permissions,
        "storage":storage,
        "webrtc":(
            {k:webrtc.get(k) for k in ("available","candidateTypes","candidateCount","hostExposed","publicCandidateExposed","relayObserved","mdnsMasked")}
            if webrtc else {"available":False,"state":"not_run"}
        ),
        "findings":findings,
        "raw_fingerprint_uploaded":False,
    }


def compare_browser_reports(a: dict,b: dict) -> dict:
    left=(a or {}).get("fingerprint",{}).get("identifier")
    right=(b or {}).get("fingerprint",{}).get("identifier")
    same=bool(left and right and left==right)
    changed=[]
    for key in ("browser","surfaces","permissions","storage","webrtc"):
        if (a or {}).get(key)!=(b or {}).get(key):
            changed.append(key)
    return {
        "same_local_fingerprint":same,
        "linkability":"HIGH LINKABILITY" if same else ("MODERATE EXPOSURE" if left and right else "INCONCLUSIVE"),
        "changed_sections":changed,
        "interpretation":"A matching local identifier indicates these tested contexts exposed the same selected signal set; it does not prove universal trackability." if same else "The selected signal set changed; this does not by itself prove unlinkability.",
    }
