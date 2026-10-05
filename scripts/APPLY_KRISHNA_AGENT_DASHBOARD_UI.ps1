param(
    [string]$SourceRoot = "E:\KRISHNA-SOURCE"
)

$ErrorActionPreference = "Stop"
$htmlPath = Join-Path $SourceRoot "core\web_validation.html"
if (-not (Test-Path -LiteralPath $htmlPath)) { throw "KRISHNA UI not found: $htmlPath" }

$html = Get-Content -LiteralPath $htmlPath -Raw -Encoding UTF8
$marker = "KRISHNA AGENT WORK DASHBOARD v1"
if ($html.Contains($marker)) {
    Write-Host "KRISHNA Agent Work Dashboard v1 is already applied." -ForegroundColor Yellow
    exit 0
}

$css = @'
<style id="krishna-agent-work-dashboard-v1">
/* KRISHNA AGENT WORK DASHBOARD v1
   Inspiration principles only: strong hierarchy, dimensional icon layers,
   restrained glass, readable labels, and honest work-state semantics. */
.opsInformer{
  min-height:78px!important;max-height:88px!important;
  background:
    radial-gradient(circle at 8% 0%,rgba(230,198,111,.075),transparent 24%),
    linear-gradient(135deg,rgba(9,28,40,.91),rgba(4,13,21,.86))!important;
  border-color:rgba(119,215,231,.24)!important;
  box-shadow:0 18px 50px rgba(0,0,0,.34),inset 0 1px 0 rgba(255,255,255,.035)!important;
}
.projectHomeMini{gap:8px!important;padding:3px 5px 6px!important}
.miniGodRow{
  position:relative!important;flex:0 0 108px!important;width:108px!important;height:58px!important;min-width:108px!important;
  display:grid!important;grid-template-columns:38px minmax(0,1fr)!important;grid-template-rows:1fr 1fr!important;
  column-gap:8px!important;row-gap:0!important;align-items:center!important;padding:6px 9px!important;
  border-radius:15px!important;overflow:hidden!important;
  border:1px solid rgba(119,215,231,.15)!important;
  background:linear-gradient(145deg,rgba(18,42,55,.86),rgba(6,18,28,.92))!important;
  color:#e9f3f6!important;
  box-shadow:0 10px 22px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.05),inset 0 -1px 0 rgba(0,0,0,.35)!important;
  transform-style:preserve-3d!important;perspective:500px!important;
  transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease,background .18s ease!important;
}
.miniGodRow::after{
  content:"";position:absolute;inset:0;pointer-events:none;border-radius:inherit;
  background:linear-gradient(115deg,rgba(255,255,255,.075),transparent 31%,transparent 67%,rgba(119,215,231,.035));
}
.miniGodRow:hover,.miniGodRow:focus-visible{
  transform:translateY(-3px) rotateX(3deg)!important;
  border-color:rgba(230,198,111,.46)!important;
  box-shadow:0 15px 30px rgba(0,0,0,.34),0 0 20px rgba(119,215,231,.075),inset 0 1px 0 rgba(255,255,255,.075)!important;
  outline:none!important;
}
.miniGodLogo{
  grid-row:1 / 3!important;grid-column:1!important;
  width:34px!important;height:34px!important;display:grid!important;place-items:center!important;
  border-radius:11px!important;font-size:18px!important;line-height:1!important;color:#f2d681!important;
  background:
    radial-gradient(circle at 32% 22%,rgba(255,255,255,.24),transparent 23%),
    linear-gradient(145deg,rgba(42,87,103,.94),rgba(10,27,39,.98))!important;
  border:1px solid rgba(230,198,111,.36)!important;
  box-shadow:0 7px 13px rgba(0,0,0,.4),inset 0 2px 1px rgba(255,255,255,.12),inset 0 -3px 5px rgba(0,0,0,.34),0 0 12px rgba(230,198,111,.08)!important;
  text-shadow:0 1px 0 #000,0 0 10px rgba(230,198,111,.25)!important;
  transform:translateZ(12px)!important;
}
.miniGodName{
  position:static!important;width:auto!important;height:auto!important;clip:auto!important;overflow:hidden!important;
  grid-column:2!important;grid-row:1!important;align-self:end!important;
  display:block!important;white-space:nowrap!important;text-overflow:ellipsis!important;
  font:800 9px/1.15 Inter,"Segoe UI",Arial,sans-serif!important;letter-spacing:.055em!important;
  text-transform:none!important;color:#e8f1f4!important;text-shadow:0 1px 0 rgba(0,0,0,.55)!important;
}
.miniGodState{
  position:static!important;width:auto!important;height:auto!important;clip:auto!important;overflow:hidden!important;
  grid-column:2!important;grid-row:2!important;align-self:start!important;
  display:block!important;white-space:nowrap!important;text-overflow:ellipsis!important;
  font:700 7px/1.2 Inter,"Segoe UI",Arial,sans-serif!important;letter-spacing:.09em!important;text-transform:uppercase!important;
  color:#7f9aa5!important;
}
.miniGodRow .godLight{right:5px!important;top:5px!important;width:6px!important;height:6px!important}
/* Idle/done is neutral-gold, not failure-red. Real error remains red. */
.miniGodRow.workstate-idle .godLight,.miniGodRow.workstate-done .godLight,.miniGodRow.workstate-fixed .godLight{
  background:#d7b45f!important;color:#d7b45f!important;box-shadow:0 0 8px rgba(215,180,95,.55)!important;
}
.miniGodRow.workstate-working .godLight,.miniGodRow.workstate-handling .godLight{
  background:#53f0a5!important;color:#53f0a5!important;box-shadow:0 0 10px rgba(83,240,165,.72)!important;
}
.miniGodRow.workstate-error .godLight,.miniGodRow.workstate-blocked .godLight{
  background:#ef6875!important;color:#ef6875!important;box-shadow:0 0 10px rgba(239,104,117,.58)!important;
}

.godDetailDialog.agentWorkDashboard{
  width:min(820px,calc(100vw - 34px))!important;max-height:min(88dvh,820px)!important;padding:0!important;
  border:1px solid rgba(119,215,231,.28)!important;border-radius:24px!important;
  background:
    radial-gradient(circle at 90% 0%,rgba(119,215,231,.08),transparent 27%),
    radial-gradient(circle at 0% 0%,rgba(230,198,111,.07),transparent 30%),
    linear-gradient(155deg,rgba(9,28,40,.99),rgba(4,12,19,.995))!important;
  box-shadow:0 36px 120px rgba(0,0,0,.7)!important;
}
.agentDash{padding:22px!important}
.agentDashHead{display:grid;grid-template-columns:56px minmax(0,1fr) auto;gap:13px;align-items:center}
.agentDashLogo{
  width:54px;height:54px;display:grid;place-items:center;border-radius:16px;font-size:27px;color:#f2d681;
  border:1px solid rgba(230,198,111,.4);
  background:radial-gradient(circle at 30% 20%,rgba(255,255,255,.22),transparent 25%),linear-gradient(145deg,rgba(42,87,103,.95),rgba(8,24,36,.98));
  box-shadow:0 10px 22px rgba(0,0,0,.4),inset 0 2px 1px rgba(255,255,255,.12),inset 0 -4px 8px rgba(0,0,0,.34),0 0 20px rgba(230,198,111,.08);
  text-shadow:0 2px 0 #000,0 0 12px rgba(230,198,111,.25)
}
.agentDashIdentity{min-width:0}.agentDashIdentity strong{display:block;font-size:20px;letter-spacing:.025em;color:#edf6f8}.agentDashIdentity p{margin:5px 0 0;color:#8199a3;font-size:11px;line-height:1.45}
.agentDashClose{width:36px;height:36px;border:1px solid rgba(119,215,231,.14);border-radius:11px;background:rgba(8,23,33,.72);color:#dcebed;font-size:21px;cursor:pointer}
.agentDashStatus{display:flex;gap:8px;align-items:center;margin:18px 0 12px;padding:10px 12px;border:1px solid rgba(119,215,231,.11);border-radius:13px;background:rgba(119,215,231,.035)}
.agentDashStatus b{font-size:11px;letter-spacing:.08em}.agentDashStatus span{margin-left:auto;color:#78909a;font-size:9px}
.agentDashCurrent{padding:15px;border:1px solid rgba(230,198,111,.14);border-radius:15px;background:linear-gradient(135deg,rgba(230,198,111,.05),rgba(119,215,231,.025))}
.agentDashLabel{font-size:8px;letter-spacing:.14em;text-transform:uppercase;color:#6f8993;font-weight:850}
.agentDashCurrentTask{margin-top:6px;color:#dce9ed;font-size:13px;line-height:1.5}
.agentDashProgressRow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:9px;align-items:center;margin-top:12px;color:#758e98;font-size:8px;letter-spacing:.08em;text-transform:uppercase}
.agentDashProgress{height:6px;border-radius:999px;overflow:hidden;background:rgba(255,255,255,.055)}
.agentDashProgress>i{display:block;height:100%;width:0;border-radius:inherit;background:linear-gradient(90deg,#57d8ef,#58dfa2);box-shadow:0 0 10px rgba(87,216,239,.28);transition:width .25s ease}
.agentDashMetrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0}
.agentDashMetric{padding:11px;border:1px solid rgba(119,215,231,.105);border-radius:13px;background:rgba(119,215,231,.026)}
.agentDashMetric span{display:block;color:#6f8791;font-size:8px;letter-spacing:.11em;text-transform:uppercase}.agentDashMetric b{display:block;margin-top:6px;color:#e4eef1;font-size:18px}
.agentDashRecent{margin-top:8px;border:1px solid rgba(119,215,231,.10);border-radius:14px;overflow:hidden;background:rgba(4,13,20,.35)}
.agentDashRecentHead{padding:10px 12px;border-bottom:1px solid rgba(119,215,231,.08);font-size:8px;letter-spacing:.13em;text-transform:uppercase;color:#6f8993;font-weight:850}
.agentDashRecentList{max-height:220px;overflow:auto}.agentDashEvent{display:grid;grid-template-columns:8px minmax(0,1fr) auto;gap:9px;align-items:start;padding:9px 12px;border-top:1px solid rgba(119,215,231,.055)}.agentDashEvent:first-child{border-top:0}.agentDashEventDot{width:7px;height:7px;margin-top:4px;border-radius:50%;background:#d7b45f}.agentDashEvent.working .agentDashEventDot,.agentDashEvent.handling .agentDashEventDot{background:#53f0a5;box-shadow:0 0 7px rgba(83,240,165,.5)}.agentDashEvent.error .agentDashEventDot,.agentDashEvent.blocked .agentDashEventDot{background:#ef6875}.agentDashEventText{min-width:0;color:#cbdcdf;font-size:10px;line-height:1.4}.agentDashEventText small{display:block;color:#667f89;margin-top:2px}.agentDashEventTime{font-size:8px;color:#5f7680;white-space:nowrap}
.agentDashActions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}.agentDashActions button{min-height:36px}
@media(max-width:1100px){.miniGodRow{flex-basis:96px!important;width:96px!important;min-width:96px!important}.miniGodName{font-size:8px!important}}
@media(max-width:820px){
  .opsInformer{min-height:72px!important;max-height:82px!important}
  .miniGodRow{flex:0 0 42px!important;width:42px!important;height:42px!important;min-width:42px!important;display:grid!important;place-items:center!important;padding:0!important}
  .miniGodLogo{grid-area:auto!important;width:30px!important;height:30px!important;font-size:16px!important}
  .miniGodName,.miniGodState{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip:rect(0 0 0 0)!important;white-space:nowrap!important}
  .agentDash{padding:15px!important}.agentDashMetrics{grid-template-columns:1fr 1fr}.agentDashHead{grid-template-columns:48px minmax(0,1fr) auto}.agentDashLogo{width:46px;height:46px;font-size:23px}
}
</style>
'@

$newDialog = @'
<dialog id="godDetailDialog" class="godDetailDialog agentWorkDashboard" aria-labelledby="godDetailName"><div class="agentDash">
 <div class="agentDashHead"><span id="godDetailLogo" class="agentDashLogo">◈</span><div class="agentDashIdentity"><strong id="godDetailName">System</strong><p id="godDetailRole"></p></div><button class="agentDashClose" type="button" onclick="document.getElementById('godDetailDialog').close()" aria-label="Close system dashboard">×</button></div>
 <div class="agentDashStatus"><b id="godDetailState">IDLE</b><span id="godDetailUpdated">—</span></div>
 <div class="agentDashCurrent"><div class="agentDashLabel">Current / latest task</div><div id="godDetailActivity" class="agentDashCurrentTask">No recent work is recorded.</div><div class="agentDashProgressRow"><span>Progress</span><div class="agentDashProgress"><i id="godDetailProgressBar"></i></div><b id="godDetailProgress">Not reported</b></div></div>
 <div class="agentDashMetrics"><div class="agentDashMetric"><span>Completed</span><b id="godMetricDone">0</b></div><div class="agentDashMetric"><span>Working</span><b id="godMetricWorking">0</b></div><div class="agentDashMetric"><span>Attention</span><b id="godMetricAttention">0</b></div><div class="agentDashMetric"><span>Recent events</span><b id="godMetricEvents">0</b></div></div>
 <div class="agentDashRecent"><div class="agentDashRecentHead">Recent activity</div><div id="godDetailRecent" class="agentDashRecentList"></div></div>
 <div class="agentDashActions"><button id="godDetailOpen" class="ghost" type="button" hidden>Open workspace</button></div>
</div></dialog>
'@

$newUpdateFunction = @'
function updateGodDetail(){
 const g=(workingGodsSnapshot?.gods||[]).find(x=>x.id===selectedGodId);if(!g)return;
 const [role,view]=godRoles[g.id]||['A KRISHNA system component.','workingGods'];
 $('godDetailLogo').textContent=g.logo||'◈';$('godDetailName').textContent=g.name||g.id;$('godDetailRole').textContent=role;
 const state=String(g.state||'idle').toLowerCase();
 $('godDetailState').textContent=state.toUpperCase();
 const updated=Number(g.updated_at||0);$('godDetailUpdated').textContent=updated?('Updated '+new Date(updated*1000).toLocaleString()):'No update timestamp';
 const events=(workingGodsSnapshot?.notifications||[]).filter(n=>n.component===g.id).slice(-80);
 const completed=events.filter(n=>['done','fixed'].includes(String(n.state||'').toLowerCase())).length;
 const working=events.filter(n=>['working','handling'].includes(String(n.state||'').toLowerCase())).length;
 const attention=events.filter(n=>['error','blocked','failed'].includes(String(n.state||'').toLowerCase())).length;
 $('godMetricDone').textContent=String(completed);$('godMetricWorking').textContent=String(working);$('godMetricAttention').textContent=String(attention);$('godMetricEvents').textContent=String(events.length);
 const detail=String(g.detail||'').trim();const latest=events.at(-1);
 let activity=state==='idle'&&(!detail||detail.toLowerCase()==='idle')?'No recent work is recorded for this system.':detail||'No activity details have been reported.';
 if(latest?.detail==='ConnectionAbortedError'||latest?.detail?.includes('ConnectionAbortedError'))activity=g.id==='brahma'?'BRAHMA recorded an interrupted connection and is handling the reported error.':'A connection closed before the task finished. The error is recorded for review.';
 else if(latest?.detail==='action.requested')activity='A task was requested and this system is working on it.';
 $('godDetailActivity').textContent=workingGodsFetchError?'Live update unavailable. Last report: '+activity:activity;
 let progressRaw=g.progress ?? latest?.metadata?.progress ?? latest?.metadata?.percent ?? latest?.metadata?.completion_percent;
 let progress=Number(progressRaw);if(Number.isFinite(progress)&&progress>=0&&progress<=1)progress*=100;
 const hasProgress=Number.isFinite(progress)&&progress>=0&&progress<=100;progress=hasProgress?Math.round(progress):0;
 $('godDetailProgress').textContent=hasProgress?(progress+'%'):'Not reported';$('godDetailProgressBar').style.width=hasProgress?(progress+'%'):'0%';
 const recent=$('godDetailRecent');recent.replaceChildren();
 events.slice(-10).reverse().forEach(n=>{const row=document.createElement('div'),ns=String(n.state||'idle').toLowerCase();row.className='agentDashEvent '+ns;const dot=document.createElement('i');dot.className='agentDashEventDot';const text=document.createElement('div');text.className='agentDashEventText';text.textContent=n.title||n.detail||n.topic||'Activity';const small=document.createElement('small');small.textContent=[n.topic,n.project].filter(Boolean).join(' · ');text.appendChild(small);const tm=document.createElement('span');tm.className='agentDashEventTime';tm.textContent=n.created_at?new Date(Number(n.created_at)*1000).toLocaleTimeString():'';row.append(dot,text,tm);recent.appendChild(row)});
 if(!events.length){const empty=document.createElement('div');empty.className='agentDashEvent';const dot=document.createElement('i');dot.className='agentDashEventDot';const text=document.createElement('div');text.className='agentDashEventText';text.textContent='No recent lifecycle events have been recorded for this component.';empty.append(dot,text);recent.appendChild(empty)}
 const open=$('godDetailOpen');open.hidden=!view;open.textContent=view==='home'?'Talk to KRISHNA':'Open '+(g.name||'system')+' workspace';open.onclick=()=>{const d=$('godDetailDialog');if(d.open)d.close();if(view==='home'){showView('home');toggleKrishnaPopup(true)}else showView(view)};
}
'@

# 1) Add final CSS override before </head> so it wins the cascade.
if (-not $html.Contains('</head>')) { throw "UI head closing tag not found" }
$html = $html.Replace('</head>', $css + "`r`n</head>")

# 2) Replace the generic component popup with the work dashboard.
$dialogPattern = '(?s)<dialog id="godDetailDialog" class="godDetailDialog" aria-labelledby="godDetailName">.*?</dialog>'
if (-not [regex]::IsMatch($html,$dialogPattern)) { throw "Generic system detail dialog not found; refusing blind patch" }
$html = [regex]::Replace($html,$dialogPattern,[System.Text.RegularExpressions.MatchEvaluator]{ param($m) $newDialog },1)

# 3) Replace only the detail-rendering function; preserve all other runtime JS.
$updatePattern = '(?s)function updateGodDetail\(\)\{.*?\n\}\nfunction godRowElement'
if (-not [regex]::IsMatch($html,$updatePattern)) { throw "updateGodDetail function not found; refusing blind patch" }
$replacement = $newUpdateFunction + "`r`nfunction godRowElement"
$html = [regex]::Replace($html,$updatePattern,[System.Text.RegularExpressions.MatchEvaluator]{ param($m) $replacement },1)

# 4) Give compact rows an explicit semantic state class so idle != failed.
$needle = "row.className='miniGodRow';row.type='button';row.dataset.godId=g.id;row.dataset.label=g.name||g.id;"
$insert = "row.className='miniGodRow';row.type='button';row.dataset.godId=g.id;row.dataset.label=g.name||g.id;row.classList.add('workstate-'+String(g.state||'idle').toLowerCase());"
if (-not $html.Contains($needle)) { throw "Compact system-row constructor not found; refusing blind patch" }
$html = $html.Replace($needle,$insert)

# Sanity guards before writing.
foreach($required in @(
    $marker,
    'class="godDetailDialog agentWorkDashboard"',
    'id="godMetricDone"',
    'id="godDetailProgressBar"',
    "row.classList.add('workstate-'"
)) {
    if (-not $html.Contains($required)) { throw "Patch sanity check failed: $required" }
}

# Ensure old desktop clipping rule is overridden by the new final style.
if (-not $html.Contains('.miniGodName{')) { throw "miniGodName styling missing" }

$tmp = "$htmlPath.agent-ui.tmp"
[System.IO.File]::WriteAllText($tmp,$html,[System.Text.UTF8Encoding]::new($false))
Move-Item -Force -LiteralPath $tmp -Destination $htmlPath

Write-Host "Applied KRISHNA Agent Work Dashboard v1 to $htmlPath" -ForegroundColor Green
Write-Host "No runtime deployment was performed. Run tests, then use verified deployment." -ForegroundColor Cyan
