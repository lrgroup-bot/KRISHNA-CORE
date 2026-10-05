import { test, expect } from '@playwright/test';

const systems = [
  ['krishna','KRISHNA'],['brahma','BRAHMA'],['sudarshan','Sudarshan'],['hawkeye','HAWKEYE'],
  ['kabach','KABACH'],['garuda','Garuda'],['garudanetra','Garudanetra'],['narad','NARAD'],
  ['brahmagyan','BRAHMAGYAN'],['gyan','Gyan-Bhandar'],['rishi','Rishi Council'],['amcc','aMCC'],
  ['suryadev','Suryadev'],['chandradev','Chandradev'],['mrityunjaya','Mrityunjaya'],
  ['ui_guardian','UI Guardian'],['developer','Developer'],['specialists','Specialists'],
  ['perfection','Project Perfection'],['vishvakarma','Vishvakarma'],
];

const stateFor = id => id === 'krishna' ? 'working' : id === 'chandradev' ? 'error' : id === 'brahma' ? 'done' : id === 'mrityunjaya' ? 'healing' : 'idle';

const processSnapshot = {
  version:'browser-fixture-v2',
  latest_state:'working',
  gods: systems.map(([id,name]) => ({
    id,name,logo:'◇',state:stateFor(id),
    color: stateFor(id)==='working' ? 'green' : 'yellow',
    detail: id==='krishna' ? 'Coordinating the owner request' : id==='chandradev' ? 'Visual QC debate requires attention' : id==='brahma' ? 'Last QC completed' : id==='mrityunjaya' ? 'Verifying recovery candidate' : 'Idle',
    updated_at: 1791208800,
  })),
  notifications:[
    {component:'brahma',state:'done',title:'BRAHMA QC completed',created_at:1791208700},
    {component:'hawkeye',state:'done',title:'HAWKEYE evidence check completed',created_at:1791208600},
    {component:'chandradev',state:'error',title:'CHANDRADEV visual disagreement',created_at:1791208500},
  ],
  open_errors:{visual:{component:'chandradev'}},
};

function apiFixture(pathname){
  if(pathname==='/api/working-gods'||pathname==='/api/brahma/process-qc') return processSnapshot;
  if(pathname==='/api/brahma/status') return {state:'ready',process_qc:processSnapshot};
  if(pathname==='/api/chandradev/status') return {agent:'CHANDRADEV',ready:true,qc_records:12,camera_observations:31,open_debates:1};
  if(pathname==='/api/hawkeye/status') return {agent_id:'bhumiputra',ready:true,survey_count:3,live_sessions:0,mobile_evidence:{items:8}};
  if(pathname==='/api/suryadev/status') return {status:'ready',nodes:{count:1}};
  if(pathname==='/api/sudarshan/runtime') return {status:'ready',authority:'control-plane'};
  if(pathname==='/api/project-perfection/status') return {status:'ready',run_count:4};
  if(pathname==='/api/gyan-bhandar/inventory') return {kinds:{evidence:4,semantic:3}};
  if(pathname==='/api/garudanetra/sessions') return {sessions:[]};
  if(pathname==='/api/ui-guardian/registry') return {entries:[]};
  if(pathname==='/api/kabach/projects') return {projects:['KRISHNA']};
  if(pathname==='/api/brahmagyan/status') return {status:'ready',mission_count:2,curiosity_queued:0};
  if(pathname==='/api/narad/status') return {status:'ready',dead_letters:0};
  return {};
}

test('KRISHNA Spatial Command OS keeps all upper systems professional and owner-readable', async ({page}) => {
  test.setTimeout(60_000);

  await page.route('**/api/**', async route => {
    const request=route.request();
    const url=new URL(request.url());
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(apiFixture(url.pathname))});
  });

  await page.goto('http://127.0.0.1:4173/operational-preview.html',{waitUntil:'domcontentloaded'});
  await expect(page.locator('#candidate')).toBeVisible();
  await expect(page.locator('#candidate')).toHaveAttribute('src','legacy-dashboard.html');

  await expect.poll(
    () => page.frames().some(frame => /legacy-dashboard\.html/.test(frame.url())),
    {timeout:15_000,message:'legacy KRISHNA dashboard iframe should navigate'}
  ).toBe(true);
  const legacy = page.frames().find(frame => /legacy-dashboard\.html/.test(frame.url()));
  expect(legacy).toBeTruthy();
  await legacy.waitForFunction(() => window.KRISHNA_OPERATIONAL_UI?.version === '2026.10-spatial-command-os-v1',null,{timeout:15_000});

  await expect(legacy.locator('#workingGodsMini .miniGodRow')).toHaveCount(20);
  await expect(legacy.locator('#opHomeDeck')).toBeVisible();
  await expect(legacy.locator('#opHomeDeck')).toContainText('One command. Verified execution.');

  for (const [id,name] of systems) {
    const button=legacy.locator(`#workingGodsMini .miniGodRow[data-god-id="${id}"]`);
    await expect(button).toBeVisible();
    await expect(button.locator('.miniGodName')).toBeVisible();
    await expect(button.locator('.miniGodName')).toHaveText(name);
    await expect(button.locator('.miniGodState')).toBeVisible();
    await button.click();
    await expect(legacy.locator('#godDetailDialog')).toHaveAttribute('open','');
    await expect(legacy.locator('#godDetailName')).toHaveText(name);
    await expect(legacy.locator('#opPurpose')).not.toBeEmpty();
    await expect(legacy.locator('#opWorking')).not.toBeEmpty();
    await expect(legacy.locator('#opProgressLabel')).not.toBeEmpty();
    await expect(legacy.locator('#opDone')).not.toBeEmpty();
    await expect(legacy.locator('#opProblems')).not.toBeEmpty();
    await expect(legacy.locator('#opNext')).not.toBeEmpty();
    await expect(legacy.locator('#opApproval')).not.toBeEmpty();
    await legacy.locator('#godDetailDialog .opClose').click();
  }

  await legacy.locator('#workingGodsMini .miniGodRow[data-god-id="hawkeye"]').click();
  await expect(legacy.locator('#godDetailRole')).toContainText('Mobile and field eyes');
  await expect(legacy.locator('#opMeta')).toContainText('LIVE SESSIONS');
  await legacy.locator('#godDetailDialog .opClose').click();

  await legacy.locator('#workingGodsMini .miniGodRow[data-god-id="amcc"]').click();
  await expect(legacy.locator('#godDetailRole')).toContainText('Adaptive effort controller');
  await expect(legacy.locator('#opTechnicalJson')).toContainText('No separate detailed telemetry endpoint');
  await legacy.locator('#godDetailDialog .opClose').click();

  await legacy.locator('#workingGodsMini .miniGodRow[data-god-id="chandradev"]').click();
  await expect(legacy.locator('#godDetailRole')).toContainText('Independent visual QC');
  await expect(legacy.locator('#opHealthBadge')).toContainText(/attention|debate/i);
  await expect(legacy.locator('#opProblems')).toContainText(/debate/i);
  await legacy.locator('#godDetailDialog .opClose').click();

  await expect(legacy.locator('#workingGodsMini .miniGodRow[data-god-id="hawkeye"] .godLight')).toHaveClass(/op-ready/);
  await expect(legacy.locator('#workingGodsMini .miniGodRow[data-god-id="mrityunjaya"] .godLight')).toHaveClass(/op-healing/);
  await expect(legacy.locator('#workingGodsMini .miniGodRow[data-god-id="chandradev"] .godLight')).toHaveClass(/op-attention/);

  for (const helper of ['File','Plugin','Project','Investigate','Research']) {
    const button=legacy.locator('.composerWrap .composeFoot .tools button.tool',{hasText:helper});
    await expect(button).toBeHidden();
  }
  await expect(legacy.locator('.composerWrap .send')).toHaveText('RUN');
  await expect(legacy.locator('#input')).toHaveAttribute('placeholder','Tell KRISHNA what you want done…');

  await page.screenshot({path:'spatial-command-os-candidate.png',fullPage:true});
});
