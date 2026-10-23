/* One bounded retry for local read-only dashboard API requests.
 * Never retries POST, job execution, security approvals or external URLs.
 */
"use strict";
(function () {
  const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function suryadevRead(url, options = {}) {
    if (typeof url !== "string" || !url.startsWith("/api/") || url.startsWith("//")) {
      throw new TypeError("Dashboard reads must use a local /api/ path");
    }
    const method = String(options.method || "GET").toUpperCase();
    if (method !== "GET" || options.body !== undefined) {
      throw new TypeError("Read-only dashboard API retry cannot submit changes");
    }
    const init = {...options, method:"GET", cache:"no-store", credentials:"same-origin"};
    let error;
    for (let attempt = 0; attempt < 2; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 9000);
      try {
        const response = await fetch(url, {...init, signal:controller.signal});
        if (response.status !== 502 && response.status !== 503 &&
            response.status !== 504) return response;
        // The server may be busy while research commits an evidence record.
        if (attempt === 1) return response;
      } catch (exc) {
        error = exc;
        if (attempt === 1) break;
      } finally {
        clearTimeout(timer);
      }
      await delay(300);
    }
    throw new Error("Local dashboard connection unavailable after retry: " +
                    (error?.message || "network request failed"));
  }
  window.suryadevRead = suryadevRead;
})();
