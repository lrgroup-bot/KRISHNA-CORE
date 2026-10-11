(() => {
  if (window.__KRISHNA_DISPLAY_FIT__) return;
  window.__KRISHNA_DISPLAY_FIT__ = true;

  const $ = (id) => document.getElementById(id);

  function isolateSudarshan() {
    const current = String(document.body.dataset.view || '').trim();
    const sudarshan = $('sudarshan');
    const composer = document.querySelector('.composerWrap');
    const liveWork = $('liveWork');
    const toggle = $('kbBrowserToggle');
    const main = document.querySelector('.main');
    const active = current === 'sudarshan';

    if (!active) {
      sudarshan?.classList.remove('active');
      if (composer instanceof HTMLElement) composer.hidden = true;
      if (liveWork instanceof HTMLElement) liveWork.hidden = true;
      if (toggle instanceof HTMLElement) toggle.hidden = true;
      main?.classList.remove('liveSplit');
      document.body.classList.remove('kb-real-browser-split');
      sudarshan?.classList.remove('kb-real-browser-split');
      return;
    }

    sudarshan?.classList.add('active');
    if (composer instanceof HTMLElement) composer.hidden = false;
    if (toggle instanceof HTMLElement) toggle.hidden = false;
  }

  function normalizeDesktopProfile() {
    const width = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
    const height = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
    document.documentElement.dataset.krishnaDisplay = width >= 1700 ? 'wide' : width >= 1200 ? 'desktop' : 'compact';
    document.documentElement.dataset.krishnaDisplayHeight = height >= 850 ? 'tall' : 'short';
  }

  const bodyObserver = new MutationObserver((mutations) => {
    if (mutations.some((mutation) => mutation.type === 'attributes' && mutation.attributeName === 'data-view')) {
      isolateSudarshan();
    }
  });

  bodyObserver.observe(document.body, { attributes: true, attributeFilter: ['data-view'] });
  window.addEventListener('resize', normalizeDesktopProfile, { passive: true });
  window.addEventListener('orientationchange', normalizeDesktopProfile, { passive: true });

  normalizeDesktopProfile();
  isolateSudarshan();
})();
