(() => {
  if (window.__KRISHNA_PREVIEW_API_COMPAT__) return;
  window.__KRISHNA_PREVIEW_API_COMPAT__ = true;

  const originalFetch = window.fetch.bind(window);
  const lrReadPaths = new Set(['/health', '/api/providers', '/api/distribution/platforms', '/api/market-intelligence/schema']);
  window.fetch = (input, init) => {
    let next = input;
    if (typeof input === 'string') {
      if (input === '/api/mobile/status') next = '/api/mobile/connection';
      const lrPath = input.startsWith('/lr-universe-api/') ? input.slice('/lr-universe-api'.length) : '';
      if (lrReadPaths.has(lrPath) && (!init?.method || init.method.toUpperCase() === 'GET') &&
          ['127.0.0.1', 'localhost'].includes(window.location.hostname) && ['8766', '8876'].includes(window.location.port)) {
        return originalFetch(`http://127.0.0.1:8788${lrPath}`, { ...init, credentials: 'omit' });
      }
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
