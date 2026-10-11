(() => {
  if (window.__KRISHNA_DESIGN_INTELLIGENCE__) return;
  window.__KRISHNA_DESIGN_INTELLIGENCE__ = true;

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]));

  function statusText(value, fallback = '—') {
    if (value === true) return 'YES';
    if (value === false) return 'NO';
    if (value === null || value === undefined || value === '') return fallback;
    return String(value);
  }

  function render(data) {
    const body = $('kbDesignBody');
    if (!body) return;
    const design = data?.design || {};
    const vishvakarma = data?.vishvakarma || {};
    const lifecycle = data?.project_lifecycle || {};
    const scout = data?.model_scout || {};
    const gates = Array.isArray(design.hard_acceptance_checks) ? design.hard_acceptance_checks : [];

    body.innerHTML = `
      <div class="kb-design-grid">
        <article class="kb-design-card">
          <span>RISHI VISHVAKARMA</span>
          <strong>${esc(vishvakarma.name || 'Vishvakarma')}</strong>
          <small>Verified knowledge ${esc(statusText(vishvakarma.verified, '0'))} · candidates ${esc(statusText(vishvakarma.candidate, '0'))}</small>
        </article>
        <article class="kb-design-card">
          <span>DESIGN ENGINE</span>
          <strong>${design.knowledge_bound ? 'VERIFIED KNOWLEDGE BOUND' : 'AWAITING VERIFIED KNOWLEDGE'}</strong>
          <small>Version ${esc(statusText(design.version))} · lifecycle bound ${esc(statusText(lifecycle.design_engine_bound))}</small>
        </article>
        <article class="kb-design-card">
          <span>LOCAL MODEL SCOUT</span>
          <strong>${esc(statusText(scout.active_candidates, '0'))} ACCEPTED</strong>
          <small>Evaluated ${esc(statusText(scout.evaluated, '0'))} · cloud billing authority ${esc(statusText(scout.cloud_billing_authority))}</small>
        </article>
        <article class="kb-design-card kb-design-card-wide">
          <span>HARD ACCEPTANCE GATES</span>
          <div class="kb-design-gates">${gates.length ? gates.map((gate) => `<i>${esc(gate)}</i>`).join('') : '<i>Runtime did not report acceptance gates.</i>'}</div>
        </article>
      </div>`;
  }

  async function refresh() {
    const status = $('kbDesignStatus');
    if (status) status.textContent = 'CHECKING';
    try {
      const response = await fetch('/api/design/status', { cache: 'no-store' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data?.error || `HTTP ${response.status}`);
      render(data);
      if (status) {
        status.textContent = 'LIVE';
        status.className = 'kb-design-status good';
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const body = $('kbDesignBody');
      if (body) body.innerHTML = `<div class="kb-design-offline">Design runtime unavailable. ${esc(message)}</div>`;
      if (status) {
        status.textContent = 'OFFLINE';
        status.className = 'kb-design-status bad';
      }
    }
  }

  function setOpen(open) {
    const panel = $('kbDesignIntelligence');
    const button = $('kbDesignToggle');
    if (!panel || !button) return;
    panel.hidden = !open;
    button.setAttribute('aria-expanded', open ? 'true' : 'false');
    button.classList.toggle('active', open);
    if (open) void refresh();
  }

  function install() {
    const brahmand = $('brahmand');
    const toolbar = $('kbGraphToolbar');
    if (!brahmand || !toolbar) return false;

    let button = $('kbDesignToggle');
    if (!button) {
      button = document.createElement('button');
      button.id = 'kbDesignToggle';
      button.type = 'button';
      button.textContent = 'Design';
      button.title = 'Open Design Intelligence';
      button.setAttribute('aria-expanded', 'false');
      const refreshButton = $('kbGraphRefresh2');
      toolbar.insertBefore(button, refreshButton || null);
    }

    if (!$('kbDesignIntelligence')) {
      const panel = document.createElement('aside');
      panel.id = 'kbDesignIntelligence';
      panel.className = 'kb-design-intelligence';
      panel.hidden = true;
      panel.setAttribute('aria-label', 'Design Intelligence');
      panel.innerHTML = `
        <div class="kb-design-head">
          <div><small>SUDARSHAN DESIGN · INTERNAL</small><strong>Design Intelligence</strong></div>
          <div class="kb-design-head-actions"><span id="kbDesignStatus" class="kb-design-status">READY</span><button id="kbDesignRefresh" type="button">↻</button><button id="kbDesignClose" type="button" aria-label="Close Design Intelligence">×</button></div>
        </div>
        <p class="kb-design-copy">Verified Vishvakarma knowledge, design acceptance gates and local model scouting remain internal to KRISHNA. This panel is deliberately not part of the main sidebar.</p>
        <div id="kbDesignBody"><div class="kb-design-offline">Open the panel to load design intelligence.</div></div>`;
      brahmand.appendChild(panel);
    }

    button.onclick = () => setOpen($('kbDesignIntelligence')?.hidden !== false);
    const close = $('kbDesignClose');
    if (close) close.onclick = () => setOpen(false);
    const refresh = $('kbDesignRefresh');
    if (refresh) refresh.onclick = () => void refresh();
    return true;
  }

  let attempts = 0;
  const tryInstall = () => {
    if (install()) return;
    attempts += 1;
    if (attempts < 25) window.setTimeout(tryInstall, 80);
  };
  tryInstall();
})();
