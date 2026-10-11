(() => {
  if (window.__KRISHNA_OWNER_CORRECTIONS_V2__) return;
  window.__KRISHNA_OWNER_CORRECTIONS_V2__ = true;

  const $ = (id) => document.getElementById(id);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const SUPERVISED_WEB_PLUGINS = [
    {
      id: 'chatgpt-free-web',
      name: 'ChatGPT Free',
      provider: 'OpenAI',
      mark: '◎',
      url: 'https://chatgpt.com/',
      description: 'Supervised web plugin. KRISHNA opens the free ChatGPT website inside Garudanetra; owner sign-in and provider limits still apply.',
    },
    {
      id: 'claude-free-web',
      name: 'Claude Free',
      provider: 'Anthropic',
      mark: 'C',
      url: 'https://claude.ai/',
      description: 'Supervised web plugin. KRISHNA opens the free Claude website inside Garudanetra; owner sign-in and provider limits still apply.',
    },
  ];

  function pluginSpecByName(name) {
    const wanted = String(name || '').trim().toLowerCase();
    return SUPERVISED_WEB_PLUGINS.find((spec) => spec.name.toLowerCase() === wanted) || null;
  }

  function normalizeOverflowButtons() {
    qsa('.chatMore,.projectBranchMore').forEach((button) => {
      button.textContent = '⋯';
      button.type = 'button';
      button.setAttribute('aria-haspopup', 'menu');
      button.setAttribute('aria-expanded', button.getAttribute('aria-expanded') || 'false');
      button.setAttribute(
        'aria-label',
        button.classList.contains('projectBranchMore') ? 'Project actions' : 'Chat actions',
      );
      button.title = button.classList.contains('projectBranchMore') ? 'Project actions' : 'Chat actions';
    });

    const chatMenu = $('krishnaChatMenu');
    if (chatMenu) chatMenu.setAttribute('aria-label', 'Chat actions: Rename, Pin, Share, Move to Project, Delete');
    const projectMenu = $('krishnaProjectMenu');
    if (projectMenu) projectMenu.setAttribute('aria-label', 'Project actions: Rename, Share, Delete');
  }

  function isSudarshanActive() {
    const view = String(document.body.dataset.view || '').trim();
    return view === 'sudarshan' || Boolean($('sudarshan')?.classList.contains('active'));
  }

  function enforceSudarshanIsolation() {
    const sudarshan = $('sudarshan');
    if (!sudarshan) return;
    const active = isSudarshanActive();
    sudarshan.toggleAttribute('data-owner-active', active);
    if (!active) {
      sudarshan.classList.remove('kb-real-browser-split');
      document.body.classList.remove('kb-real-browser-split');
    }
  }

  function realBrowserIsOpen() {
    const panel = $('liveWork');
    const main = document.querySelector('.main');
    return Boolean(panel && main && !panel.hidden && main.classList.contains('liveSplit'));
  }

  function updateBrowserToggleState() {
    const open = realBrowserIsOpen();
    const button = $('kbBrowserToggle');
    if (button) {
      button.setAttribute('aria-pressed', open ? 'true' : 'false');
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
      button.title = open ? 'Close Garudanetra browser' : 'Open Garudanetra browser';
      const label = button.querySelector('[data-kb-browser-label]');
      if (label) label.textContent = open ? 'Close Browser' : 'Browser';
      else button.textContent = open ? '◫ Close Browser' : '◫ Browser';
    }
    const sudarshan = $('sudarshan');
    sudarshan?.classList.toggle('kb-real-browser-split', open && isSudarshanActive());
    document.body.classList.toggle('kb-real-browser-split', open && isSudarshanActive());
  }

  function setRealBrowserOpen(open) {
    if (open && typeof window.showView === 'function' && !isSudarshanActive()) {
      window.showView('sudarshan');
    }

    if (typeof window.toggleLiveWork === 'function') {
      window.toggleLiveWork(Boolean(open));
    } else {
      const panel = $('liveWork');
      const main = document.querySelector('.main');
      if (panel) panel.hidden = !open;
      main?.classList.toggle('liveSplit', Boolean(open));
    }

    updateBrowserToggleState();
  }

  function replaceBrowserToggleWithRealSplit() {
    const existing = $('kbBrowserToggle');
    if (!existing || existing.dataset.kbRealBrowser === '1') {
      updateBrowserToggleState();
      return;
    }

    const clean = existing.cloneNode(true);
    clean.id = 'kbBrowserToggle';
    clean.dataset.kbRealBrowser = '1';
    clean.type = 'button';
    clean.textContent = '◫ Browser';
    clean.setAttribute('aria-label', 'Toggle Garudanetra browser split');
    clean.setAttribute('aria-pressed', 'false');
    clean.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      setRealBrowserOpen(!realBrowserIsOpen());
    });
    existing.replaceWith(clean);

    // The owner overlay drawer was a duplicate browser UI. The canonical browser
    // is KRISHNA's existing liveWork/Garudanetra panel, which streams real frames.
    const duplicateDrawer = $('kbBrowserDrawer');
    if (duplicateDrawer) {
      duplicateDrawer.classList.remove('open');
      duplicateDrawer.hidden = true;
      duplicateDrawer.setAttribute('aria-hidden', 'true');
    }
    updateBrowserToggleState();
  }

  async function openSupervisedWebPlugin(spec) {
    if (!spec) return;
    if (typeof window.showView === 'function') window.showView('sudarshan');
    setRealBrowserOpen(true);

    const address = $('garudaAddress');
    if (address) address.value = spec.url;

    try {
      if (typeof window.startGarudanetraBrowser === 'function') {
        await window.startGarudanetraBrowser(spec.url);
      } else if (typeof window.garudaNavigate === 'function') {
        await window.garudaNavigate();
      } else {
        throw new Error('Garudanetra browser runtime is not available in this frontend session.');
      }
    } catch (error) {
      const empty = $('garudaFrameEmpty');
      if (empty) empty.textContent = error instanceof Error ? error.message : String(error);
      if (typeof window.log === 'function') window.log(error instanceof Error ? error.message : String(error));
    }
    updateBrowserToggleState();
  }

  function searchMatches(spec) {
    const q = String($('pluginSearch')?.value || '').trim().toLowerCase();
    if (!q) return true;
    return `${spec.name} ${spec.provider} supervised web free garudanetra zero spend browser`
      .toLowerCase()
      .includes(q);
  }

  function createFallbackPluginCard(spec) {
    const card = document.createElement('article');
    card.className = 'kb-supervised-plugin-card';
    card.dataset.kbSupervisedPlugin = spec.id;

    const header = document.createElement('div');
    header.className = 'kb-supervised-plugin-head';

    const icon = document.createElement('span');
    icon.className = 'kb-supervised-plugin-icon';
    icon.textContent = spec.mark;

    const identity = document.createElement('div');
    identity.className = 'kb-supervised-plugin-identity';
    const name = document.createElement('strong');
    name.textContent = spec.name;
    const meta = document.createElement('small');
    meta.textContent = `${spec.provider} · supervised web plugin`;
    identity.append(name, meta);

    const badge = document.createElement('span');
    badge.className = 'kb-supervised-plugin-badge';
    badge.textContent = 'FREE WEB';
    header.append(icon, identity, badge);

    const copy = document.createElement('p');
    copy.textContent = spec.description;

    const chips = document.createElement('div');
    chips.className = 'kb-supervised-plugin-chips';
    ['₹0 API spend', 'Owner supervised', 'Garudanetra', 'No API key'].forEach((text) => {
      const chip = document.createElement('span');
      chip.textContent = text;
      chips.appendChild(chip);
    });

    const open = document.createElement('button');
    open.type = 'button';
    open.className = 'kb-supervised-plugin-open';
    open.textContent = 'Open in Sudarshan';
    open.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      void openSupervisedWebPlugin(spec);
    });

    card.append(header, copy, chips, open);
    return card;
  }

  function enhanceRegistryPluginCards() {
    const grid = $('pluginsGrid');
    if (!grid) return;

    qsa('.plugin', grid).forEach((card) => {
      const name = card.querySelector('.pluginName')?.textContent || '';
      const spec = pluginSpecByName(name);
      if (!spec) return;
      card.dataset.kbSupervisedRegistry = spec.id;

      let actions = card.querySelector('.kb-supervised-registry-actions');
      if (!actions) {
        actions = document.createElement('div');
        actions.className = 'kb-supervised-registry-actions';
        const badge = document.createElement('span');
        badge.textContent = 'SUPERVISED WEB';
        badge.className = 'kb-supervised-plugin-badge';
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'kb-supervised-plugin-open';
        button.textContent = 'Open in Sudarshan';
        button.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          void openSupervisedWebPlugin(spec);
        });
        actions.append(badge, button);
        card.querySelector('.pluginBody')?.appendChild(actions);
      }
    });
  }

  function ensurePluginCards() {
    const grid = $('pluginsGrid');
    if (!grid) return;
    enhanceRegistryPluginCards();

    const registryNames = new Set(
      qsa('.pluginName', grid).map((node) => String(node.textContent || '').trim().toLowerCase()),
    );

    const wanted = SUPERVISED_WEB_PLUGINS.filter(searchMatches).filter(
      (spec) => !registryNames.has(spec.name.toLowerCase()),
    );

    qsa('[data-kb-supervised-plugin]', grid).forEach((node) => node.remove());
    if (!wanted.length) return;
    const fragment = document.createDocumentFragment();
    wanted.forEach((spec) => fragment.appendChild(createFallbackPluginCard(spec)));
    grid.prepend(fragment);
  }

  async function persistPluginsInRegistry() {
    try {
      const response = await fetch('/api/plugins', { cache: 'no-store' });
      if (!response.ok) return;
      const payload = await response.json();
      const ids = new Set((payload.plugins || []).map((row) => String(row.id || '')));
      let changed = false;

      for (const spec of SUPERVISED_WEB_PLUGINS) {
        if (ids.has(spec.id)) continue;
        const result = await fetch('/api/plugins/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: spec.id,
            name: spec.name,
            description: spec.description,
            kind: 'connector',
            auth_type: 'none',
            permissions: ['browser.inspect', 'network.external'],
            project_scope: ['*'],
            risk: 'medium',
            enabled: false,
            builtin: false,
            source_url: spec.url,
            license: 'provider-free-web',
            free: true,
            project: 'KRISHNA',
          }),
        });
        if (result.ok) changed = true;
      }

      if (changed && typeof window.loadPlugins === 'function') {
        await window.loadPlugins();
      }
    } catch (_) {
      // Frontend-only mode remains useful; fallback plugin cards stay visible.
    }
  }

  function wrapPluginRendering() {
    if (typeof window.filterPlugins === 'function' && !window.filterPlugins.__kbSupervisedWrapped) {
      const original = window.filterPlugins;
      const wrapped = function(...args) {
        const result = original.apply(this, args);
        queueMicrotask(ensurePluginCards);
        return result;
      };
      wrapped.__kbSupervisedWrapped = true;
      window.filterPlugins = wrapped;
    }

    if (typeof window.loadPlugins === 'function' && !window.loadPlugins.__kbSupervisedWrapped) {
      const original = window.loadPlugins;
      const wrapped = async function(...args) {
        try {
          return await original.apply(this, args);
        } finally {
          queueMicrotask(ensurePluginCards);
        }
      };
      wrapped.__kbSupervisedWrapped = true;
      window.loadPlugins = wrapped;
    }

    const search = $('pluginSearch');
    if (search && search.dataset.kbSupervisedBound !== '1') {
      search.dataset.kbSupervisedBound = '1';
      search.addEventListener('input', () => queueMicrotask(ensurePluginCards));
    }
  }

  function wrapViewSwitching() {
    const original = window.showView;
    if (typeof original !== 'function' || original.__kbRealSplitWrapped) return;
    const wrapped = function(id, ...args) {
      if (id !== 'sudarshan' && realBrowserIsOpen()) setRealBrowserOpen(false);
      const result = original.call(this, id, ...args);
      queueMicrotask(() => {
        enforceSudarshanIsolation();
        replaceBrowserToggleWithRealSplit();
        updateBrowserToggleState();
      });
      return result;
    };
    wrapped.__kbRealSplitWrapped = true;
    window.showView = wrapped;
  }

  let repairQueued = false;
  function scheduleRepair() {
    if (repairQueued) return;
    repairQueued = true;
    queueMicrotask(() => {
      repairQueued = false;
      normalizeOverflowButtons();
      enforceSudarshanIsolation();
      replaceBrowserToggleWithRealSplit();
      wrapPluginRendering();
      ensurePluginCards();
      updateBrowserToggleState();
    });
  }

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type !== 'childList' || (!mutation.addedNodes.length && !mutation.removedNodes.length)) continue;
      const target = mutation.target;
      if (!(target instanceof Element)) continue;
      if (
        target.closest?.('.sidebarWorkspace') ||
        target.closest?.('#projectChatList') ||
        target.closest?.('#pluginsGrid') ||
        target.closest?.('#sudarshan') ||
        target.id === 'pluginsGrid' ||
        target.id === 'sudarshan'
      ) {
        scheduleRepair();
        return;
      }
    }
  });

  function install() {
    // Remove the obsolete duplicate browser drawer; the real Garudanetra liveWork
    // panel is the only browser surface used by this correction layer.
    const duplicateDrawer = $('kbBrowserDrawer');
    if (duplicateDrawer) {
      duplicateDrawer.hidden = true;
      duplicateDrawer.setAttribute('aria-hidden', 'true');
    }

    wrapViewSwitching();
    normalizeOverflowButtons();
    enforceSudarshanIsolation();
    replaceBrowserToggleWithRealSplit();
    wrapPluginRendering();
    ensurePluginCards();
    updateBrowserToggleState();
    void persistPluginsInRegistry();

    observer.observe(document.body, { childList: true, subtree: true });
  }

  install();
})();
