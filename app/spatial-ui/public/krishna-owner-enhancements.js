(() => {
  if (window.__KRISHNA_OWNER_ENHANCEMENTS__) return;
  window.__KRISHNA_OWNER_ENHANCEMENTS__ = true;

  const $ = (id) => document.getElementById(id);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const SVG_NS = 'http://www.w3.org/2000/svg';
  let pipelineOnline = null;
  let truthTimer = 0;

  function normalizeOverflowButtons() {
    qsa('.chatMore,.projectBranchMore').forEach((button) => {
      if (button.textContent !== '⋯') button.textContent = '⋯';
      if (button.getAttribute('aria-haspopup') !== 'menu') button.setAttribute('aria-haspopup', 'menu');
      if (!button.getAttribute('aria-label')) {
        button.setAttribute('aria-label', button.classList.contains('projectBranchMore') ? 'Project actions' : 'Chat actions');
      }
    });

    const chatMenu = $('krishnaChatMenu');
    const chatLabel = 'Chat actions: rename, pin, share, move or delete';
    if (chatMenu && chatMenu.getAttribute('aria-label') !== chatLabel) chatMenu.setAttribute('aria-label', chatLabel);
    const projectMenu = $('krishnaProjectMenu');
    const projectLabel = 'Project actions: rename, share or delete';
    if (projectMenu && projectMenu.getAttribute('aria-label') !== projectLabel) projectMenu.setAttribute('aria-label', projectLabel);
  }

  function ensurePipelineTruthBadge() {
    const toolbar = $('kbGraphToolbar') || document.querySelector('#brahmand .kb-dash-actions');
    if (!toolbar) return null;
    let badge = $('kbPipelineTruth');
    if (badge) return badge;
    badge = document.createElement('span');
    badge.id = 'kbPipelineTruth';
    badge.className = 'kb-live-badge';
    badge.textContent = 'PIPELINE CHECKING';
    badge.title = 'Flow is gated by KRISHNA Core health, task ledger and per-node endpoint probes.';
    const refresh = $('kbGraphRefresh2') || $('kbRefreshGraph');
    if (refresh?.parentElement === toolbar) toolbar.insertBefore(badge, refresh);
    else toolbar.appendChild(badge);
    return badge;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) throw new Error(`${url} HTTP ${response.status}`);
    return response.json();
  }

  async function refreshBackendTruth() {
    const [health, status, tasks, garuda] = await Promise.allSettled([
      fetchJson('/health'),
      fetchJson('/api/status'),
      fetchJson('/api/tasks?limit=500'),
      fetchJson('/api/garudanetra/fabric'),
    ]);

    const coreOnline = health.status === 'fulfilled' && status.status === 'fulfilled' && tasks.status === 'fulfilled';
    const taskRows = tasks.status === 'fulfilled' && Array.isArray(tasks.value?.tasks) ? tasks.value.tasks : [];
    document.documentElement.dataset.kbPipelineBackend = coreOnline ? 'online' : 'offline';

    const badge = ensurePipelineTruthBadge();
    if (badge) {
      badge.className = `kb-live-badge ${coreOnline ? 'good' : 'bad'}`;
      const working=taskRows.filter((row)=>['running','working','executing','verifying'].includes(String(row.status||'').toLowerCase())).length;
      badge.textContent = coreOnline ? `CORE CONNECTED · ${working} ACTIVE` : 'CORE OFFLINE';
      badge.title = coreOnline
        ? 'Live pipeline truth: /health + /api/status + /api/tasks. Dedicated nodes also use their own endpoint probes.'
        : 'Pipeline animation is paused because KRISHNA Core truth is unavailable.';
    }

    const garudaReady = garuda.status === 'fulfilled';
    const browserToggle = $('kbBrowserToggle');
    if (browserToggle) {
      browserToggle.dataset.garudanetraStatus = garudaReady ? 'ready' : 'offline';
      browserToggle.setAttribute('aria-label', garudaReady ? 'Toggle Garudanetra browser split · backend ready' : 'Toggle Garudanetra browser split · backend offline');
    }
    const liveState = $('liveState');
    if (liveState && !garudaReady && !$('liveWork')?.hidden) liveState.textContent = 'BACKEND OFFLINE';

    if (!coreOnline) {
      qsa('.kb-flow-drop', $('kbGraphSvg') || document).forEach((node) => node.remove());
    } else if (pipelineOnline === false) {
      // Backend recovered: force the canonical Brahmand renderer to obtain fresh
      // task/endpoint truth before flow animation resumes.
      $('kbRefreshGraph')?.click();
    }

    pipelineOnline = coreOnline;
    scheduleFlow();
    return { coreOnline, garudaReady, taskCount: taskRows.length };
  }

  function enhanceFlow() {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    const svg = $('kbGraphSvg');
    if (!svg) return;

    if (document.documentElement.dataset.kbPipelineBackend !== 'online') {
      qsa('.kb-flow-drop', svg).forEach((node) => node.remove());
      svg.dataset.kbFlowSignature = '';
      return;
    }

    // Every rendered connection is backend-derived by the canonical graph renderer:
    // active = live mapped task, green = verified/connected endpoint, yellow/red =
    // unverified/blocked. Only active/connected truth gets moving water droplets.
    const paths = qsa('path.kb-edge.active', svg);
    const signature = paths.map((path) => `${path.getAttribute('d') || ''}:${path.classList.contains('green') ? 'g' : 'a'}`).join('|');
    if (svg.dataset.kbFlowSignature === signature && qsa('.kb-flow-drop', svg).length === paths.length * 3) return;

    qsa('.kb-flow-drop', svg).forEach((node) => node.remove());
    svg.dataset.kbFlowSignature = signature;

    paths.forEach((path, pathIndex) => {
      const d = path.getAttribute('d');
      if (!d) return;
      const tone = path.classList.contains('green') ? 'green' : 'active';
      const duration = tone === 'active' ? 1.15 : 1.45;

      for (let i = 0; i < 3; i += 1) {
        const circle = document.createElementNS(SVG_NS, 'circle');
        circle.setAttribute('r', i === 0 ? '3.3' : '2.5');
        circle.setAttribute('class', `kb-flow-drop ${tone}`);
        circle.setAttribute('aria-hidden', 'true');

        const motion = document.createElementNS(SVG_NS, 'animateMotion');
        motion.setAttribute('path', d);
        motion.setAttribute('dur', `${duration}s`);
        motion.setAttribute('begin', `${-(i * duration / 3) - (pathIndex * 0.07)}s`);
        motion.setAttribute('repeatCount', 'indefinite');
        motion.setAttribute('calcMode', 'linear');
        circle.appendChild(motion);
        svg.appendChild(circle);
      }
    });
  }

  let flowQueued = false;
  function scheduleFlow() {
    if (flowQueued) return;
    flowQueued = true;
    window.requestAnimationFrame(() => {
      flowQueued = false;
      enhanceFlow();
    });
  }

  function makeSudarshanClear() {
    const sudarshan = $('sudarshan');
    if (!sudarshan) return;
    const label = 'Sudarshan full-screen conversation workspace';
    if (sudarshan.getAttribute('aria-label') !== label) sudarshan.setAttribute('aria-label', label);
    const messages = $('messages');
    if (messages && messages.getAttribute('aria-live') !== 'polite') messages.setAttribute('aria-live', 'polite');
  }

  function run() {
    normalizeOverflowButtons();
    makeSudarshanClear();
    ensurePipelineTruthBadge();
    void refreshBackendTruth();
    scheduleFlow();
  }

  const observer = new MutationObserver((mutations) => {
    let menuChanged = false;
    let graphChanged = false;
    for (const mutation of mutations) {
      if (mutation.type !== 'childList' || mutation.addedNodes.length === 0) continue;
      const target = mutation.target;
      if (target instanceof Element && (target.closest?.('.sidebarWorkspace') || target.closest?.('#projectChatList') || target.classList?.contains('sidebarWorkspace'))) menuChanged = true;
      for (const node of mutation.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.matches?.('.chatRow,.projectBranch,.chatMore,.projectBranchMore') || node.querySelector?.('.chatMore,.projectBranchMore')) menuChanged = true;
        if (node.matches?.('#kbGraphSvg,.kb-edge') || node.querySelector?.('.kb-edge')) graphChanged = true;
      }
    }
    if (menuChanged) normalizeOverflowButtons();
    if (graphChanged) scheduleFlow();
  });

  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener('resize', scheduleFlow, { passive: true });
  truthTimer = window.setInterval(() => { void refreshBackendTruth(); }, 4000);
  window.addEventListener('beforeunload', () => window.clearInterval(truthTimer), { once: true });
  window.KRISHNA_PIPELINE_TRUTH = { refresh: refreshBackendTruth };
  run();
})();
