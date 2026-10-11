(() => {
  if (window.__KRISHNA_LIVE_FEED_RICHTEXT__) return;
  window.__KRISHNA_LIVE_FEED_RICHTEXT__ = true;

  const $ = (id) => document.getElementById(id);
  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  let feedBusy = false;
  let lastFeedSignature = '';
  let richObserverBusy = false;

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function safeUrl(raw) {
    try {
      const url = new URL(String(raw || ''), window.location.href);
      if (!['http:', 'https:'].includes(url.protocol)) return '#';
      return url.href;
    } catch (_) {
      return '#';
    }
  }

  function renderInline(raw) {
    let text = escapeHtml(raw);
    const codeTokens = [];
    text = text.replace(/`([^`\n]+)`/g, (_, code) => {
      const token = `@@KC_CODE_${codeTokens.length}@@`;
      codeTokens.push(`<code>${code}</code>`);
      return token;
    });
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, href) => {
      const safe = escapeHtml(safeUrl(href));
      return `<a href="${safe}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });
    text = text.replace(/\*\*([^*\n][\s\S]*?[^*\n]|[^*\n])\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__([^_\n][\s\S]*?[^_\n]|[^_\n])__/g, '<strong>$1</strong>');
    text = text.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
    text = text.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, '$1<em>$2</em>');
    codeTokens.forEach((html, index) => {
      text = text.replace(`@@KC_CODE_${index}@@`, html);
    });
    return text;
  }

  function isTableSeparator(line) {
    const cells = line.trim().replace(/^\||\|$/g, '').split('|').map((x) => x.trim());
    return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
  }

  function tableCells(line) {
    return line.trim().replace(/^\||\|$/g, '').split('|').map((x) => x.trim());
  }

  function markdownToHtml(source) {
    const text = String(source ?? '').replace(/\r\n?/g, '\n');
    const lines = text.split('\n');
    const out = [];
    let i = 0;
    let inUl = false;
    let inOl = false;

    const closeLists = () => {
      if (inUl) { out.push('</ul>'); inUl = false; }
      if (inOl) { out.push('</ol>'); inOl = false; }
    };

    while (i < lines.length) {
      const line = lines[i];

      if (/^```/.test(line.trim())) {
        closeLists();
        const language = line.trim().slice(3).trim();
        const code = [];
        i += 1;
        while (i < lines.length && !/^```/.test(lines[i].trim())) {
          code.push(lines[i]);
          i += 1;
        }
        const lang = language ? `<span class="kc-code-lang">${escapeHtml(language)}</span>` : '<span class="kc-code-lang">CODE</span>';
        out.push(`<div class="kc-code-block"><div class="kc-code-head">${lang}<button type="button" class="kc-copy-code">COPY</button></div><pre><code>${escapeHtml(code.join('\n'))}</code></pre></div>`);
        i += 1;
        continue;
      }

      if (i + 1 < lines.length && line.includes('|') && isTableSeparator(lines[i + 1])) {
        closeLists();
        const headers = tableCells(line);
        const rows = [];
        i += 2;
        while (i < lines.length && lines[i].includes('|') && lines[i].trim()) {
          rows.push(tableCells(lines[i]));
          i += 1;
        }
        out.push('<div class="kc-table-wrap"><table><thead><tr>' + headers.map((h) => `<th>${renderInline(h)}</th>`).join('') + '</tr></thead><tbody>' + rows.map((row) => '<tr>' + headers.map((_, idx) => `<td>${renderInline(row[idx] ?? '')}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>');
        continue;
      }

      const heading = line.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        closeLists();
        const level = Math.min(4, heading[1].length + 1);
        out.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        i += 1;
        continue;
      }

      const quote = line.match(/^>\s?(.*)$/);
      if (quote) {
        closeLists();
        out.push(`<blockquote>${renderInline(quote[1])}</blockquote>`);
        i += 1;
        continue;
      }

      const ul = line.match(/^\s*[-*+]\s+(.+)$/);
      if (ul) {
        if (inOl) { out.push('</ol>'); inOl = false; }
        if (!inUl) { out.push('<ul>'); inUl = true; }
        out.push(`<li>${renderInline(ul[1])}</li>`);
        i += 1;
        continue;
      }

      const ol = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (ol) {
        if (inUl) { out.push('</ul>'); inUl = false; }
        if (!inOl) { out.push('<ol>'); inOl = true; }
        out.push(`<li>${renderInline(ol[1])}</li>`);
        i += 1;
        continue;
      }

      closeLists();
      if (!line.trim()) {
        out.push('<div class="kc-rich-gap"></div>');
      } else {
        out.push(`<p>${renderInline(line)}</p>`);
      }
      i += 1;
    }
    closeLists();
    return out.join('');
  }

  function bindCodeCopy(root) {
    qsa('.kc-copy-code', root).forEach((button) => {
      if (button.dataset.kcBound === '1') return;
      button.dataset.kcBound = '1';
      button.addEventListener('click', async () => {
        const code = button.closest('.kc-code-block')?.querySelector('code')?.textContent || '';
        try {
          await navigator.clipboard.writeText(code);
          button.textContent = 'COPIED';
          window.setTimeout(() => { button.textContent = 'COPY'; }, 1200);
        } catch (_) {
          button.textContent = 'COPY FAILED';
          window.setTimeout(() => { button.textContent = 'COPY'; }, 1200);
        }
      });
    });
  }

  function upgradeBubble(bubble) {
    if (!bubble || bubble.dataset.kcRich === '1') return;
    const raw = bubble.textContent || '';
    bubble.dataset.kcRich = '1';
    bubble.dataset.kcRaw = raw;
    bubble.classList.add('kc-rich-text');
    bubble.innerHTML = markdownToHtml(raw);
    bindCodeCopy(bubble);
  }

  function upgradeExistingMessages() {
    if (richObserverBusy) return;
    richObserverBusy = true;
    try {
      qsa('#messages .bubble,.krishnaPopupBody .popupMsg').forEach((node) => {
        if (node.classList.contains('popupMsg')) {
          const ownText = Array.from(node.childNodes).filter((child) => child.nodeType === Node.TEXT_NODE).map((child) => child.textContent || '').join('').trim();
          if (ownText && !node.querySelector('.kc-popup-rich')) {
            Array.from(node.childNodes).filter((child) => child.nodeType === Node.TEXT_NODE).forEach((child) => child.remove());
            const rich = document.createElement('div');
            rich.className = 'kc-popup-rich kc-rich-text';
            rich.innerHTML = markdownToHtml(ownText);
            node.appendChild(rich);
            bindCodeCopy(rich);
          }
        } else {
          upgradeBubble(node);
        }
      });
    } finally {
      richObserverBusy = false;
    }
  }

  function installRichMessageRenderer() {
    if (typeof window.addMsg === 'function' && !window.addMsg.__kcRichWrapped) {
      const original = window.addMsg;
      const wrapped = function(...args) {
        const result = original.apply(this, args);
        queueMicrotask(upgradeExistingMessages);
        return result;
      };
      wrapped.__kcRichWrapped = true;
      window.addMsg = wrapped;
    }
    upgradeExistingMessages();
  }

  function injectLiveFeed() {
    const main = qs('.main');
    if (!main || $('kcLiveFeed')) return;
    const feed = document.createElement('aside');
    feed.id = 'kcLiveFeed';
    feed.className = 'kc-live-feed';
    feed.innerHTML = `
      <div class="kc-live-feed-head">
        <div><span class="kc-feed-eye">◉</span><span>LIVE INTELLIGENCE FEED</span></div>
        <button id="kcLiveFeedToggle" type="button" aria-label="Collapse live feed">−</button>
      </div>
      <div class="kc-live-current"><span>CURRENT ACTIVITY</span><strong id="kcLiveCurrent">WAITING FOR CORE</strong></div>
      <div id="kcLiveRows" class="kc-live-rows"><div class="kc-feed-empty">Connecting to KRISHNA telemetry…</div></div>
      <div class="kc-live-foot"><span id="kcLiveState" class="offline">OFFLINE</span><span id="kcLiveUpdated">--:--:--</span></div>`;
    main.appendChild(feed);
    $('kcLiveFeedToggle')?.addEventListener('click', () => {
      feed.classList.toggle('collapsed');
      $('kcLiveFeedToggle').textContent = feed.classList.contains('collapsed') ? '+' : '−';
    });
  }

  function feedSignature(payload) {
    return JSON.stringify({ current: payload?.current_activity || '', recent: payload?.recent || [] });
  }

  function renderFeed(payload) {
    injectLiveFeed();
    const rows = $('kcLiveRows');
    const current = $('kcLiveCurrent');
    const state = $('kcLiveState');
    const updated = $('kcLiveUpdated');
    const recent = Array.isArray(payload?.recent) ? payload.recent.slice(0, 18) : [];
    if (current) current.textContent = payload?.current_activity || 'Idle';
    if (rows) {
      rows.replaceChildren();
      if (!recent.length) {
        const empty = document.createElement('div');
        empty.className = 'kc-feed-empty';
        empty.textContent = 'No verified activity yet.';
        rows.appendChild(empty);
      } else {
        recent.forEach((entry, index) => {
          const row = document.createElement('div');
          row.className = 'kc-feed-row';
          const time = document.createElement('time');
          time.textContent = String(entry?.time || '--:--:--');
          const pulse = document.createElement('span');
          pulse.className = 'kc-feed-pulse' + (index === 0 ? ' hot' : '');
          const event = document.createElement('div');
          event.textContent = String(entry?.event ?? entry ?? 'Activity');
          row.append(time, pulse, event);
          rows.appendChild(row);
        });
      }
    }
    if (state) { state.textContent = 'LIVE'; state.className = 'online'; }
    if (updated) updated.textContent = new Date().toLocaleTimeString([], { hour12: false });
    document.documentElement.dataset.kcFeed = 'online';
  }

  function renderFeedOffline() {
    injectLiveFeed();
    const state = $('kcLiveState');
    const updated = $('kcLiveUpdated');
    const current = $('kcLiveCurrent');
    if (state) { state.textContent = 'CORE OFFLINE'; state.className = 'offline'; }
    if (updated) updated.textContent = new Date().toLocaleTimeString([], { hour12: false });
    if (current) current.textContent = 'Waiting for KRISHNA Core';
    const rows = $('kcLiveRows');
    if (rows && !rows.querySelector('.kc-feed-row')) rows.innerHTML = '<div class="kc-feed-empty">Live feed will resume automatically when Core reconnects.</div>';
    document.documentElement.dataset.kcFeed = 'offline';
  }

  async function refreshFeed() {
    if (feedBusy || document.hidden) return;
    feedBusy = true;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 1800);
    try {
      const response = await fetch('/api/dashboard', { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(String(response.status));
      const payload = await response.json();
      const signature = feedSignature(payload);
      if (signature !== lastFeedSignature) {
        lastFeedSignature = signature;
        renderFeed(payload);
      } else {
        const state = $('kcLiveState');
        const updated = $('kcLiveUpdated');
        if (state) { state.textContent = 'LIVE'; state.className = 'online'; }
        if (updated) updated.textContent = new Date().toLocaleTimeString([], { hour12: false });
      }
    } catch (_) {
      renderFeedOffline();
    } finally {
      window.clearTimeout(timer);
      feedBusy = false;
    }
  }

  function syncFeedVisibility() {
    injectLiveFeed();
    const feed = $('kcLiveFeed');
    if (!feed) return;
    const view = String(document.body.dataset.view || 'home');
    feed.hidden = view === 'sudarshan' || view === 'plugins' || view === 'projects';
  }

  const messageRoot = $('messages') || document.body;
  const messageObserver = new MutationObserver(() => queueMicrotask(() => {
    installRichMessageRenderer();
  }));
  messageObserver.observe(messageRoot, { childList: true, subtree: true });

  const bodyObserver = new MutationObserver((mutations) => {
    if (mutations.some((m) => m.type === 'attributes' && m.attributeName === 'data-view')) syncFeedVisibility();
  });
  bodyObserver.observe(document.body, { attributes: true, attributeFilter: ['data-view'] });

  injectLiveFeed();
  installRichMessageRenderer();
  syncFeedVisibility();
  void refreshFeed();
  window.setInterval(() => { void refreshFeed(); }, 2000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) void refreshFeed(); });
  window.addEventListener('online', () => void refreshFeed());
})();
