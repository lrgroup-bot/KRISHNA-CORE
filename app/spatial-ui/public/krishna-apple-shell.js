(() => {
  if (window.__KRISHNA_APPLE_SHELL__) return;
  window.__KRISHNA_APPLE_SHELL__ = true;

  const $ = (id) => document.getElementById(id);
  const q = (selector, root = document) => root.querySelector(selector);

  function enhanceBrand() {
    const brand = q('.brand');
    if (!brand) return;
    const small = q('small', brand);
    const wanted = 'LOCAL INTELLIGENCE SYSTEM';
    if (small && small.textContent !== wanted) small.textContent = wanted;
  }

  function enhanceHero() {
    const home = $('#home');
    const host = q('.assistantHome', home || document);
    const om = $('#assistantOm');
    if (!host || !om || host.dataset.appleHero === '1') return;
    host.dataset.appleHero = '1';

    const eyebrow = document.createElement('div');
    eyebrow.className = 'appleHeroEyebrow';
    eyebrow.textContent = 'LOCAL INTELLIGENCE SYSTEM';

    const title = document.createElement('h1');
    title.className = 'appleHeroTitle';
    title.textContent = 'KRISHNA';

    const subtitle = document.createElement('p');
    subtitle.className = 'appleHeroSubtitle';
    subtitle.textContent = 'Quiet power. Clear control.';

    host.insertBefore(eyebrow, om);
    host.insertBefore(title, om);
    host.insertBefore(subtitle, om);

    const hint = Array.from(host.children).find((node) => node.tagName === 'P' && node !== subtitle);
    if (hint) {
      hint.classList.add('appleHeroHint');
      hint.textContent = 'Tap the Om to talk or type to KRISHNA.';
    }

    const actions = document.createElement('div');
    actions.className = 'appleHeroActions';

    const sudarshan = document.createElement('button');
    sudarshan.type = 'button';
    sudarshan.className = 'appleHeroAction primary';
    sudarshan.textContent = 'Open Sudarshan';
    sudarshan.addEventListener('click', () => {
      if (typeof window.showView === 'function') window.showView('sudarshan');
    });

    const brahmand = document.createElement('button');
    brahmand.type = 'button';
    brahmand.className = 'appleHeroAction';
    brahmand.textContent = 'Explore Brahmand';
    brahmand.addEventListener('click', () => {
      const nav = $('#kbNavBrahmand');
      if (nav) nav.click();
      else if (typeof window.showView === 'function') window.showView('brahmand');
    });

    actions.append(sudarshan, brahmand);
    host.appendChild(actions);
  }

  function sectionStateKey(kind) {
    return `krishnaAppleSection:${kind}`;
  }

  function applySectionState(kind, collapsed) {
    const workspace = q('.sidebarWorkspace');
    if (!workspace) return;
    const head = q(kind === 'projects' ? '.projectsHead' : '.chatsHead', workspace);
    const toggle = head?.querySelector('.appleSectionLabel');
    const targets = kind === 'projects'
      ? [$('#projectMenuTree')]
      : [q('.chatSearchWrap', workspace), $('#recentChats')];

    toggle?.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    targets.forEach((node) => node?.classList.toggle('apple-section-collapsed', collapsed));
    try { localStorage.setItem(sectionStateKey(kind), collapsed ? '1' : '0'); } catch {}
  }

  function addSectionToggle(kind, label) {
    const workspace = q('.sidebarWorkspace');
    if (!workspace) return;
    const head = q(kind === 'projects' ? '.projectsHead' : '.chatsHead', workspace);
    if (!head || head.dataset.appleSection === '1') return;
    head.dataset.appleSection = '1';

    const originalLabel = Array.from(head.children).find((node) => node.tagName === 'SPAN');
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'appleSectionLabel';
    toggle.innerHTML = '<span class="appleSectionChevron">⌄</span><span></span>';
    toggle.querySelector('span:last-child').textContent = label;
    if (originalLabel) originalLabel.replaceWith(toggle);
    else head.prepend(toggle);

    let stored = null;
    try { stored = localStorage.getItem(sectionStateKey(kind)); } catch {}
    const collapsed = stored === '1';
    applySectionState(kind, collapsed);
    toggle.addEventListener('click', () => {
      const nextCollapsed = toggle.getAttribute('aria-expanded') !== 'false';
      applySectionState(kind, nextCollapsed);
    });
  }

  function syncSidebarEmptiness() {
    const workspace = q('.sidebarWorkspace');
    if (!workspace) return;

    const chats = $('#recentChats');
    const hasChats = Boolean(chats?.querySelector('.chatRow'));
    workspace.classList.toggle('apple-no-chats', !hasChats);

    const projects = $('#projectMenuTree');
    const hasProjects = Boolean(projects?.querySelector('.projectBranch'));
    workspace.classList.toggle('apple-no-projects', !hasProjects);
  }

  function cleanTopBar() {
    const context = $('#contextBadge');
    if (context) context.hidden = true;
    const mode = $('#modeBadge');
    if (mode && mode.textContent !== 'KRISHNA') mode.textContent = 'KRISHNA';
    const pageTitle = $('#pageTitle');
    if (pageTitle && !pageTitle.dataset.appleTitle) {
      pageTitle.dataset.appleTitle = '1';
      pageTitle.textContent = 'Local Intelligence';
    }
  }

  function markActiveNavigation() {
    const current = String(document.body.dataset.view || 'home');
    q('.mainMenuPlugin')?.classList.toggle('active', current === 'plugins');
  }

  function wrapViewSwitch() {
    const original = window.showView;
    if (typeof original !== 'function' || original.__krishnaAppleWrapped) return;
    const wrapped = function(id, ...args) {
      const result = original.call(this, id, ...args);
      queueMicrotask(() => {
        markActiveNavigation();
        syncSidebarEmptiness();
      });
      return result;
    };
    wrapped.__krishnaAppleWrapped = true;
    window.showView = wrapped;
  }

  let queued = false;
  function repair() {
    if (queued) return;
    queued = true;
    queueMicrotask(() => {
      queued = false;
      enhanceBrand();
      enhanceHero();
      addSectionToggle('projects', 'PROJECTS');
      addSectionToggle('chats', 'CHATS');
      syncSidebarEmptiness();
      cleanTopBar();
      markActiveNavigation();
    });
  }

  function install() {
    wrapViewSwitch();
    repair();

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type !== 'childList' || (!mutation.addedNodes.length && !mutation.removedNodes.length)) continue;
        const target = mutation.target;
        if (!(target instanceof Element)) continue;
        if (
          target.closest?.('.side') ||
          target.closest?.('#home') ||
          target.id === 'recentChats' ||
          target.id === 'projectMenuTree'
        ) {
          repair();
          break;
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  install();
})();
