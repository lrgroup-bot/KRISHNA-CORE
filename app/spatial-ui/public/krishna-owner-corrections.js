(() => {
  if (window.__KRISHNA_OWNER_CORRECTIONS__) return;
  window.__KRISHNA_OWNER_CORRECTIONS__ = true;

  const $ = (id) => document.getElementById(id);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const FREE_WEB_PLUGINS = [
    {
      id: 'chatgpt-free-web',
      name: 'ChatGPT Free',
      provider: 'OpenAI',
      mark: '◎',
      url: 'https://chatgpt.com/',
      copy: 'Zero-spend browser connector through Garudanetra. Uses ChatGPT Free on the web; manual sign-in may be required.',
    },
    {
      id: 'claude-free-web',
      name: 'Claude Free',
      provider: 'Anthropic',
      mark: 'C',
      url: 'https://claude.ai/',
      copy: 'Zero-spend browser connector through Garudanetra. Uses Claude Free on the web; manual sign-in may be required.',
    },
  ];

  function normalizeOverflowButtons() {
    qsa('.chatMore,.projectBranchMore').forEach((button) => {
      button.textContent = '⋯';
      button.setAttribute('aria-haspopup', 'menu');
      button.setAttribute('aria-expanded', button.getAttribute('aria-expanded') || 'false');
      if (!button.getAttribute('aria-label')) {
        button.setAttribute('aria-label', button.classList.contains('projectBranchMore') ? 'Project actions' : 'Chat actions');
      }
    });

    const chatMenu = $('krishnaChatMenu');
    if (chatMenu) chatMenu.setAttribute('aria-label', 'Chat actions: Rename, Pin, Share, Move to Project, Delete');
    const projectMenu = $('krishnaProjectMenu');
    if (projectMenu) projectMenu.setAttribute('aria-label', 'Project actions: Rename, Share, Delete');
  }

  let observedDrawer = null;
  const drawerObserver = new MutationObserver(() => syncBrowserSplit());

  function syncBrowserSplit() {
    const sudarshan = $('sudarshan');
    const drawer = $('kbBrowserDrawer');
    const open = Boolean(drawer?.classList.contains('open'));
    sudarshan?.classList.toggle('kb-browser-split-open', open);
    document.body.classList.toggle('kb-browser-split-open', open);
  }

  function bindBrowserSplit() {
    const drawer = $('kbBrowserDrawer');
    if (drawer && drawer !== observedDrawer) {
      drawerObserver.disconnect();
      drawerObserver.observe(drawer, { attributes: true, attributeFilter: ['class'] });
      observedDrawer = drawer;
    }
    syncBrowserSplit();
  }

  function openFreeWebPlugin(spec) {
    if (typeof window.showView === 'function') window.showView('sudarshan');

    window.setTimeout(() => {
      const toggle = $('kbBrowserToggle');
      const drawer = $('kbBrowserDrawer');
      const input = $('kbBrowserUrl');
      const go = $('kbBrowserGo');

      if (!drawer?.classList.contains('open')) toggle?.click();
      if (input) input.value = spec.url;
      bindBrowserSplit();

      window.setTimeout(() => {
        if (go) go.click();
      }, 40);
    }, 40);
  }

  function pluginMatchesSearch(spec) {
    const search = String($('pluginSearch')?.value || '').trim().toLowerCase();
    if (!search) return true;
    const haystack = `${spec.name} ${spec.provider} free web browser garudanetra zero spend`.toLowerCase();
    return haystack.includes(search);
  }

  function createFreePluginCard(spec) {
    const card = document.createElement('article');
    card.className = 'kb-free-plugin-card';
    card.dataset.kbFreePlugin = spec.id;

    const head = document.createElement('div');
    head.className = 'kb-free-plugin-head';

    const icon = document.createElement('div');
    icon.className = 'kb-free-plugin-icon';
    icon.textContent = spec.mark;

    const title = document.createElement('div');
    title.className = 'kb-free-plugin-title';
    const strong = document.createElement('strong');
    strong.textContent = spec.name;
    const small = document.createElement('small');
    small.textContent = `${spec.provider} · browser connector`;
    title.append(strong, small);

    const badge = document.createElement('span');
    badge.className = 'kb-free-plugin-badge';
    badge.textContent = 'FREE WEB';
    head.append(icon, title, badge);

    const copy = document.createElement('div');
    copy.className = 'kb-free-plugin-copy';
    copy.textContent = spec.copy;

    const meta = document.createElement('div');
    meta.className = 'kb-free-plugin-meta';
    ['₹0 API spend', 'No API key', 'Garudanetra', 'Owner login'].forEach((label) => {
      const chip = document.createElement('span');
      chip.textContent = label;
      meta.appendChild(chip);
    });

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'kb-free-plugin-open';
    button.textContent = 'Open in Sudarshan';
    button.addEventListener('click', () => openFreeWebPlugin(spec));

    card.append(head, copy, meta, button);
    return card;
  }

  function ensureFreeWebPlugins() {
    const grid = $('pluginsGrid');
    if (!grid) return;

    const wanted = FREE_WEB_PLUGINS.filter(pluginMatchesSearch);
    const signature = wanted.map((x) => x.id).join('|');
    const existing = qsa('[data-kb-free-plugin]', grid);
    const current = existing.map((node) => node.dataset.kbFreePlugin).join('|');
    if (grid.dataset.kbFreePluginSignature === signature && current === signature) return;

    existing.forEach((node) => node.remove());
    const fragment = document.createDocumentFragment();
    wanted.forEach((spec) => fragment.appendChild(createFreePluginCard(spec)));
    grid.prepend(fragment);
    grid.dataset.kbFreePluginSignature = signature;
  }

  function wrapPluginRenderers() {
    if (typeof window.filterPlugins === 'function' && !window.filterPlugins.__kbFreeWrapped) {
      const original = window.filterPlugins;
      const wrapped = function(...args) {
        const result = original.apply(this, args);
        queueMicrotask(ensureFreeWebPlugins);
        return result;
      };
      wrapped.__kbFreeWrapped = true;
      window.filterPlugins = wrapped;
    }

    if (typeof window.loadPlugins === 'function' && !window.loadPlugins.__kbFreeWrapped) {
      const original = window.loadPlugins;
      const wrapped = async function(...args) {
        try {
          return await original.apply(this, args);
        } finally {
          queueMicrotask(ensureFreeWebPlugins);
        }
      };
      wrapped.__kbFreeWrapped = true;
      window.loadPlugins = wrapped;
    }

    const search = $('pluginSearch');
    if (search && !search.dataset.kbFreeBound) {
      search.dataset.kbFreeBound = '1';
      search.addEventListener('input', () => queueMicrotask(ensureFreeWebPlugins));
    }
  }

  let pluginQueued = false;
  function schedulePluginRepair() {
    if (pluginQueued) return;
    pluginQueued = true;
    queueMicrotask(() => {
      pluginQueued = false;
      wrapPluginRenderers();
      ensureFreeWebPlugins();
    });
  }

  function run() {
    normalizeOverflowButtons();
    bindBrowserSplit();
    wrapPluginRenderers();
    ensureFreeWebPlugins();
  }

  const domObserver = new MutationObserver((mutations) => {
    let menuChanged = false;
    let browserChanged = false;
    let pluginsChanged = false;

    for (const mutation of mutations) {
      if (mutation.type !== 'childList') continue;
      const target = mutation.target;

      if (target instanceof Element) {
        if (target.id === 'pluginsGrid' || target.closest?.('#pluginsGrid')) pluginsChanged = true;
        if (target.id === 'sudarshan' || target.closest?.('#sudarshan')) browserChanged = true;
        if (target.closest?.('.sidebarWorkspace') || target.closest?.('#projectChatList')) menuChanged = true;
      }

      for (const node of mutation.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.matches?.('.chatRow,.projectBranch,.chatMore,.projectBranchMore') || node.querySelector?.('.chatMore,.projectBranchMore')) menuChanged = true;
        if (node.matches?.('#kbBrowserDrawer,#kbBrowserToggle') || node.querySelector?.('#kbBrowserDrawer,#kbBrowserToggle')) browserChanged = true;
        if (node.matches?.('#pluginsGrid') || node.querySelector?.('#pluginsGrid')) pluginsChanged = true;
      }
    }

    if (menuChanged) normalizeOverflowButtons();
    if (browserChanged) bindBrowserSplit();
    if (pluginsChanged) {
      const grid = $('pluginsGrid');
      if (grid && !grid.querySelector('[data-kb-free-plugin]')) schedulePluginRepair();
    }
  });

  domObserver.observe(document.body, { childList: true, subtree: true });
  window.addEventListener('resize', bindBrowserSplit, { passive: true });
  run();
})();
