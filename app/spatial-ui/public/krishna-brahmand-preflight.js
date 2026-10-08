(() => {
  const checks = [];
  const record = (name, ok, detail = '') => checks.push({ name, ok: Boolean(ok), detail });
  const has = (selector) => Boolean(document.querySelector(selector));
  const textOf = (selector) => (document.querySelector(selector)?.textContent || '').trim();

  record('legacy KRISHNA home preserved', has('#home') && has('#assistantOm'));
  record('legacy Sudarshan preserved', has('#sudarshan'));
  record('projects preserved', has('#projects'));
  record('plugins preserved', has('#plugins'));
  record('KRISHNA cosmic core injected', has('.kb-core-shell') && has('.kb-cosmos'));
  record('LR Universe main navigation injected', has('#kbNavLR') && textOf('#kbNavLR').includes('LR Universe'));
  record('Brahmand main navigation injected', has('#kbNavBrahmand') && textOf('#kbNavBrahmand').includes('Brahmand'));
  record('Plugins moved into main menu', Boolean(document.querySelector('.mainMenuNav .mainMenuPlugin')));
  record('Brahmand dashboard injected', has('#brahmand') && has('#kbGraphNodes') && has('#kbInspector'));
  record('Brahmand back control injected', has('#kbGraphBack'));
  record('compact system load injected', has('#kbOwnerLoad') && has('#kbCpu') && has('#kbRam') && has('#kbGpu') && has('#kbNet'));
  record('standalone Surya sidebar card removed', !has('#kbSuryaCard'));
  record('compact Mobile telemetry injected', has('#kbMobileCard') && has('#kbMobileState'));
  record('Sudarshan Garudanetra toggle injected', has('#kbBrowserToggle') && has('#kbBrowserDrawer') && has('#kbBrowserFrame'));
  record('old live-system button rail retained for legacy but hidden by preview CSS', has('#opsInformer'));

  const data = window.KRISHNA_BRAHMAND_DATA;
  record('pipeline registry loaded', Boolean(data?.nodes?.krishna && data?.nodes?.['rishi-council'] && data?.nodes?.sudarshan));
  record('pipeline node IDs normalized', Boolean(data?.nodes?.krishna?.id === 'krishna' && data?.nodes?.['rishi-council']?.id === 'rishi-council'));
  record('Rishi Council drill-down available', Array.isArray(data?.nodes?.['rishi-council']?.children) && data.nodes['rishi-council'].children.length >= 10);
  record('Sudarshan drill-down available', Array.isArray(data?.nodes?.sudarshan?.children) && data.nodes.sudarshan.children.length >= 4);
  record('Surya and Chandra live inside Vision group', Boolean(data?.nodes?.vision?.children?.includes('suryadev') && data?.nodes?.vision?.children?.includes('chandradev')));
  record('LR Universe connected to Brahmand root', Boolean(data?.root?.includes('lr-universe') && data?.nodes?.['lr-universe']?.children?.length));
  record('LR Universe source model loaded', Boolean(window.LR_UNIVERSE_SOURCE_DATA?.sourceRepo && window.LR_UNIVERSE_SOURCE_DATA?.sharedDepartments?.length));

  const failed = checks.filter((check) => !check.ok);
  window.KRISHNA_BRAHMAND_PREFLIGHT = { ok: failed.length === 0, checks, failed, checked_at: new Date().toISOString() };
  if (failed.length) console.warn('[KRISHNA Brahmand preflight] failed', failed);
  else console.info('[KRISHNA Brahmand preflight] PASS', checks.length, 'checks');
})();
