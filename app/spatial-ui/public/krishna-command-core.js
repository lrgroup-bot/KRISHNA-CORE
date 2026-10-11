(() => {
  if (window.__KRISHNA_COMMAND_CORE__) return;
  window.__KRISHNA_COMMAND_CORE__ = true;

  const $ = (id) => document.getElementById(id);
  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  let sidebarRefreshing = false;
  let lastSidebarRefresh = 0;
  let coreOnline = false;

  function viewName() {
    return String(document.body.dataset.view || 'home').trim() || 'home';
  }

  function displayViewLabel(id) {
    const map = {
      home: 'KRISHNA',
      sudarshan: 'SUDARSHAN',
      lrUniverse: 'LR UNIVERSE',
      brahmand: 'BRAHMAND',
      plugins: 'PLUGINS',
      projects: 'PROJECTS',
    };
    return map[id] || String(id || 'KRISHNA').replace(/([a-z])([A-Z])/g, '$1 $2').toUpperCase();
  }

  function setTextIfChanged(node, value) {
    if (node && node.textContent !== value) node.textContent = value;
  }

  function injectHud() {
    const main = qs('.main');
    if (!main || $('krishnaCommandHud')) return;
    const hud = document.createElement('div');
    hud.id = 'krishnaCommandHud';
    hud.className = 'kc-command-hud';
    hud.innerHTML = `
      <div class="kc-hud-block"><span class="kc-live-dot"></span><span><span class="kc-hud-kicker">KRISHNA CORE</span><br><b id="kcCoreState" class="kc-hud-value kc-core-value">SCANNING</b></span></div>
      <div class="kc-hud-block"><span><span class="kc-hud-kicker">ACTIVE CHAMBER</span><br><b id="kcViewState" class="kc-hud-value">KRISHNA</b></span></div>
      <div class="kc-hud-block"><span><span class="kc-hud-kicker">LOCAL TIME</span><br><b id="kcClock" class="kc-hud-value">--:--:--</b></span></div>`;
    main.appendChild(hud);
  }

  function syncHud() {
    injectHud();
    setTextIfChanged($('kcViewState'), displayViewLabel(viewName()));
    setTextIfChanged($('kcClock'), new Date().toLocaleTimeString([], { hour12: false }));
    setTextIfChanged($('kcCoreState'), coreOnline ? 'ONLINE · VERIFIED LINK' : 'OFFLINE · FRONTEND MODE');
    const wanted = coreOnline ? 'online' : 'offline';
    if (document.documentElement.dataset.kcCore !== wanted) document.documentElement.dataset.kcCore = wanted;
  }

  function navTarget(button) {
    if (button.id === 'kbNavLR') return 'lrUniverse';
    if (button.id === 'kbNavBrahmand') return 'brahmand';
    if (button.classList.contains('mainMenuPlugin')) return 'plugins';
    const onclick = button.getAttribute('onclick') || '';
    const match = onclick.match(/showView\(['\"]([^'\"]+)['\"]\)/);
    return match?.[1] || '';
  }

  function syncNavigation() {
    const current = viewName();
    qsa('.mainMenuNav>button,.bottomNav>button,.mainMenuPlugin').forEach((button) => {
      const target = navTarget(button);
      const active = Boolean(target && target === current);
      button.classList.toggle('active', active);
      if (active) {
        if (button.getAttribute('aria-current') !== 'page') button.setAttribute('aria-current', 'page');
      } else if (button.hasAttribute('aria-current')) {
        button.removeAttribute('aria-current');
      }
    });
  }

  function ensureCountBadge(head, id) {
    if (!head) return null;
    let badge = $(id);
    if (badge) return badge;
    badge = document.createElement('span');
    badge.id = id;
    badge.className = 'kc-side-count';
    badge.textContent = '0';
    const label = head.querySelector('span:first-child') || head.querySelector('.appleSectionLabel');
    if (label) label.appendChild(badge);
    else head.prepend(badge);
    return badge;
  }

  function sidebarHasProjectRows() {
    return Boolean(qs('#projectMenuTree .projectBranch'));
  }

  function sidebarHasChatRows() {
    return Boolean(qs('#recentChats .chatRow'));
  }

  function setSidebarState(container, message, tone = 'loading') {
    if (!container || container.querySelector('.projectBranch,.chatRow')) return;
    let node = container.querySelector('.kc-sidebar-state');
    if (!node) {
      node = document.createElement('div');
      node.className = 'kc-sidebar-state';
      container.replaceChildren(node);
    }
    const wantedClass = `kc-sidebar-state ${tone}`;
    if (node.className !== wantedClass) node.className = wantedClass;
    setTextIfChanged(node, message);
  }

  function syncSidebarCounts(projectCount = null, chatCount = null) {
    const projectBadge = ensureCountBadge(qs('.projectsHead'), 'kcProjectCount');
    const chatBadge = ensureCountBadge(qs('.chatsHead'), 'kcChatCount');
    const p = projectCount ?? qsa('#projectMenuTree .projectBranch').length;
    const c = chatCount ?? qsa('#recentChats .chatRow').length;
    setTextIfChanged(projectBadge, String(p));
    setTextIfChanged(chatBadge, String(c));
  }

  async function fetchJson(url, timeoutMs = 2200) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`${response.status}`);
      return await response.json();
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function refreshLiveSidebar(force = false) {
    const now = Date.now();
    if (sidebarRefreshing || (!force && now - lastSidebarRefresh < 3500)) return;
    sidebarRefreshing = true;
    lastSidebarRefresh = now;
    const projectTree = $('projectMenuTree');
    const chats = $('recentChats');

    if (!sidebarHasProjectRows()) setSidebarState(projectTree, 'Scanning project registry…', 'loading');
    if (!sidebarHasChatRows()) setSidebarState(chats, 'Scanning conversation memory…', 'loading');

    try {
      const [projectsPayload, chatsPayload] = await Promise.all([
        fetchJson('/api/projects'),
        fetchJson('/api/chats'),
      ]);
      coreOnline = true;

      if (typeof window.refreshSidebarData === 'function') {
        await window.refreshSidebarData();
      } else {
        if (typeof window.renderSidebarProjectTree === 'function') await window.renderSidebarProjectTree();
        if (typeof window.loadGeneralChats === 'function') await window.loadGeneralChats();
      }

      const visibleProjects = (projectsPayload.projects || []).filter((p) => p?.name !== 'KRISHNA' && p?.name !== 'KRISHNA-E2E-PROBE');
      const visibleChats = (chatsPayload.chats || []).filter((ch) => !ch?.project || ch.project === 'KRISHNA' || ch.project === 'general');
      if (!sidebarHasProjectRows() && projectTree && !projectTree.querySelector('.chatEmpty')) setSidebarState(projectTree, 'No projects yet · use + to create one', 'empty');
      if (!sidebarHasChatRows() && chats && !chats.querySelector('.chatEmpty')) setSidebarState(chats, 'No chats yet · use + to start Sudarshan', 'empty');
      syncSidebarCounts(visibleProjects.length, visibleChats.length);
    } catch (_) {
      coreOnline = false;
      if (!sidebarHasProjectRows()) setSidebarState(projectTree, 'Core offline · projects will appear automatically when KRISHNA connects', 'offline');
      if (!sidebarHasChatRows()) setSidebarState(chats, 'Core offline · chat history will appear automatically when KRISHNA connects', 'offline');
      syncSidebarCounts();
    } finally {
      sidebarRefreshing = false;
      syncHud();
    }
  }

  function attachEnergyParallax() {
    const shell = qs('#home .kb-core-shell');
    if (!shell || shell.dataset.kcParallax === '1') return;
    shell.dataset.kcParallax = '1';
    let frame = 0;
    shell.addEventListener('pointermove', (event) => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const rect = shell.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / Math.max(1, rect.width) - .5) * 2;
        const y = ((event.clientY - rect.top) / Math.max(1, rect.height) - .5) * 2;
        shell.style.setProperty('--kc-px', x.toFixed(3));
        shell.style.setProperty('--kc-py', y.toFixed(3));
      });
    }, { passive: true });
    shell.addEventListener('pointerleave', () => {
      shell.style.setProperty('--kc-px', '0');
      shell.style.setProperty('--kc-py', '0');
    }, { passive: true });
  }

  function repair() {
    injectHud();
    syncNavigation();
    syncHud();
    syncSidebarCounts();
    attachEnergyParallax();
  }

  const bodyObserver = new MutationObserver((mutations) => {
    if (mutations.some((m) => m.type === 'attributes' && m.attributeName === 'data-view')) {
      syncNavigation();
      syncHud();
    }
  });
  bodyObserver.observe(document.body, { attributes: true, attributeFilter: ['data-view'] });

  const sidebarObserver = new MutationObserver(() => syncSidebarCounts());
  const workspace = qs('.sidebarWorkspace');
  if (workspace) sidebarObserver.observe(workspace, { childList: true, subtree: true });

  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) void refreshLiveSidebar(true);
  });
  window.addEventListener('online', () => void refreshLiveSidebar(true));

  repair();
  void refreshLiveSidebar(true);
  window.setInterval(() => {
    syncHud();
    if (!document.hidden) void refreshLiveSidebar(false);
  }, 4000);
  window.setInterval(syncHud, 1000);
})();
