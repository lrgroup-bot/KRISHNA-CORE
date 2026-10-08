(() => {
  const checks = [];
  const record = (name, ok, detail = '') => checks.push({ name, ok: Boolean(ok), detail });
  const has = (selector) => Boolean(document.querySelector(selector));

  record('legacy KRISHNA home preserved', has('#home') && has('#assistantOm'));
  record('legacy Sudarshan preserved', has('#sudarshan'));
  record('projects preserved', has('#projects'));
  record('plugins preserved', has('#plugins'));
  record('KRISHNA cosmic core injected', has('.kb-core-shell') && has('.kb-cosmos'));
  record('LR Universe navigation injected', has('#kbNavLR'));
  record('Krishna Brahmand navigation injected', has('#kbNavBrahmand'));
  record('Brahmand dashboard injected', has('#brahmand') && has('#kbGraphNodes') && has('#kbInspector'));
  record('Surya telemetry injected', has('#kbSuryaCard') && has('#kbSuryaCount'));
  record('Mobile telemetry injected', has('#kbMobileCard') && has('#kbMobileState'));
  record('old live-system button rail hidden by preview CSS', has('#opsInformer'));

  const data = window.KRISHNA_BRAHMAND_DATA;
  record('pipeline registry loaded', Boolean(data?.nodes?.krishna && data?.nodes?.['rishi-council'] && data?.nodes?.sudarshan));
  record('pipeline node IDs normalized', Boolean(data?.nodes?.krishna?.id === 'krishna' && data?.nodes?.['rishi-council']?.id === 'rishi-council'));
  record('Rishi Council drill-down available', Array.isArray(data?.nodes?.['rishi-council']?.children) && data.nodes['rishi-council'].children.length >= 10);
  record('Sudarshan drill-down available', Array.isArray(data?.nodes?.sudarshan?.children) && data.nodes.sudarshan.children.length >= 4);

  const failed = checks.filter((check) => !check.ok);
  window.KRISHNA_BRAHMAND_PREFLIGHT = { ok: failed.length === 0, checks, failed, checked_at: new Date().toISOString() };
  if (failed.length) console.warn('[KRISHNA Brahmand preflight] failed', failed);
  else console.info('[KRISHNA Brahmand preflight] PASS', checks.length, 'checks');
})();
