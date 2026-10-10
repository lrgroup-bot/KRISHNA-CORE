(() => {
  if (window.__KRISHNA_OWNER_ENHANCEMENTS__) return;
  window.__KRISHNA_OWNER_ENHANCEMENTS__ = true;

  const $ = (id) => document.getElementById(id);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const SVG_NS = 'http://www.w3.org/2000/svg';

  function normalizeOverflowButtons() {
    qsa('.chatMore,.projectBranchMore').forEach((button) => {
      button.textContent = '⋯';
      button.setAttribute('aria-haspopup', 'menu');
      if (!button.getAttribute('aria-label')) {
        button.setAttribute('aria-label', button.classList.contains('projectBranchMore') ? 'Project actions' : 'Chat actions');
      }
    });

    const chatMenu = $('krishnaChatMenu');
    if (chatMenu) chatMenu.setAttribute('aria-label', 'Chat actions: rename, pin, share, move or delete');
    const projectMenu = $('krishnaProjectMenu');
    if (projectMenu) projectMenu.setAttribute('aria-label', 'Project actions: rename, share or delete');
  }

  function enhanceFlow() {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    const svg = $('kbGraphSvg');
    if (!svg) return;

    qsa('.kb-flow-drop', svg).forEach((node) => node.remove());
    const paths = qsa('path.kb-edge.active,path.kb-edge.green', svg);

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
    sudarshan.setAttribute('aria-label', 'Sudarshan full-screen conversation workspace');
    const messages = $('messages');
    if (messages) messages.setAttribute('aria-live', 'polite');
  }

  function run() {
    normalizeOverflowButtons();
    makeSudarshanClear();
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
  run();
})();
