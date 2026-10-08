(() => {
  if (window.__KRISHNA_PREVIEW_API_COMPAT__) return;
  window.__KRISHNA_PREVIEW_API_COMPAT__ = true;

  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    let next = input;
    if (typeof input === 'string') {
      if (input === '/api/mobile/status') next = '/api/mobile/connection';
    } else if (input instanceof Request) {
      const url = new URL(input.url, window.location.href);
      if (url.pathname === '/api/mobile/status') {
        url.pathname = '/api/mobile/connection';
        next = new Request(url.toString(), input);
      }
    }
    return originalFetch(next, init);
  };
})();
