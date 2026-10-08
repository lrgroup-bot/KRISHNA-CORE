(() => {
  if (window.__KRISHNA_OWNER_HOTFIX__) return;
  window.__KRISHNA_OWNER_HOTFIX__ = true;

  let attempts = 0;
  const timer = window.setInterval(() => {
    attempts += 1;
    const sudarshan = document.getElementById('sudarshan');
    const toggle = document.getElementById('kbBrowserToggle');
    if (sudarshan && toggle) {
      toggle.classList.add('kb-browser-floating-toggle');
      if (toggle.parentElement !== sudarshan) sudarshan.appendChild(toggle);
      window.clearInterval(timer);
      return;
    }
    if (attempts > 120) window.clearInterval(timer);
  }, 50);
})();
