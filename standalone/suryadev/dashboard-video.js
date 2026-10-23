/* Existing SURYADEV dashboard extension: supervised R39 video evidence lane.
   No R39 frontend assets, HTTP pairing, automatic recording or auto-promotion. */
(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    const sources = document.getElementById('sources');
    if (!sources) return;
    const section = document.createElement('section');
    section.id = 'video-review';
    section.className = 'surface video-review-panel';
    section.innerHTML = `
      <div class="section-heading compact"><div><div class="overline">SUPERVISED OBSERVATION</div>
      <h2>Browser video review</h2></div></div>
      <p>Adaptive speed: <strong>1×</strong> important technical/safety material, <strong>1.5×</strong> explanations, <strong>2×</strong> ordinary talk, <strong>4×</strong> confirmed small talk only. Reverts to 1× when captions stop or audio-only transcription is used. High-speed audiovisual coverage is not certified.</p>
      <p>KRISHNA-approved jobs only. Browser observation stays local until separately verified KRISHNA evidence acceptance. No background recording starts here.</p>
      <label for="video-review-json">KRISHNA video_research job JSON</label>
      <textarea id="video-review-json" rows="5" spellcheck="false" placeholder='{"schema":"krishna.suryadev.job.v1","job_id":"lesson-01","kind":"video_research","target":"https://...","constraints":{"duration_seconds":60}}'></textarea>
      <div class="video-review-actions"><button id="video-review-import" type="button">Import for review</button><button id="video-review-refresh" type="button">Refresh jobs</button></div>
      <p class="video-review-hint">The complete target URL must already be in your local approved learning-plan.json. The exact URL, including query parameters, stays visible before approval.</p>
      <div id="video-review-status" role="status" aria-live="polite"></div>
      <div id="video-review-list"></div>`;
    sources.parentNode.insertBefore(section, sources);
    const nav = document.querySelector('.navigation');
    if (nav) {
      const link = document.createElement('a');
      link.href = '#video-review';
      link.className = 'nav-item';
      link.textContent = '▶ Video review';
      const assigned = nav.querySelector('a[href="#assignments"]');
      if (assigned) nav.insertBefore(link, assigned); else nav.append(link);
    }
    const el = id => document.getElementById(id);
    let csrf = null;
    const setStatus = value => { el('video-review-status').textContent = String(value); };
    const post = async (url, body) => {
      if (!csrf) {
        const response = await fetch('/api/operator/settings', {cache:'no-store'});
        if (!response.ok) throw new Error('Cannot obtain local CSRF authorization');
        csrf = (await response.json()).csrf_token;
        if (!csrf) throw new Error('CSRF authorization missing');
      }
      const response = await fetch(url, {method:'POST',
        headers: {'Content-Type':'application/json', 'X-SURYADEV-CSRF':csrf},
        body: JSON.stringify(body)});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Local operation rejected');
      return data;
    };
    const refresh = async () => {
      try {
        const response = await fetch('/api/video/review', {cache: 'no-store'});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Read failed');
        const list = el('video-review-list');
        list.replaceChildren();
        const status = document.createElement('p');
        status.textContent = (data.active_job ? 'Active: ' + data.active_job : 'No video currently running') +
          (data.runtime_ready ? ' · Observer source installed; device prerequisites unverified' : ' · Worker installation required') +
          (data.last_error ? ' · Last error: ' + data.last_error : '');
        list.append(status);
        if (data.playback) {
          const current = document.createElement('p');
          const rate = data.playback.observed_rate;
          current.textContent = 'Measured playback: ' +
            (rate == null ? 'unavailable' : String(rate) + '×') +
            ' · Mode: ' + String(data.playback.category || 'unknown') +
            ' · Video timestamp: ' + String(data.playback.video_seconds ?? '?') +
            's · Completeness: unverified';
          list.append(current);
        }
        for (const job of data.jobs || []) {
          const card = document.createElement('article');
          card.className = 'video-review-job';
          const heading = document.createElement('strong');
          heading.textContent = job.job_id + ' · ' + job.status;
          const url = document.createElement('code');
          url.textContent = job.target;
          const approval = document.createElement('label');
          const check = document.createElement('input');
          check.type = 'checkbox';
          approval.append(check, document.createTextNode(' I reviewed this exact URL and approve one observation'));
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.textContent = 'Run approved job';
          btn.disabled = !job.can_run || !data.runtime_ready;
          btn.addEventListener('click', async () => {
            if (!check.checked) return setStatus('Tick approval after reviewing the complete URL');
            btn.disabled = true;
            try {
              const result = await post('/api/operator/video/run', {
                job_id: job.job_id, expected_sha256: job.sha256, approved: true
              });
              setStatus('Started supervised job ' + result.job_id + '. No Core upload performed.');
            } catch (err) { setStatus(err.message); }
            await refresh();
          });
          card.append(heading, url, approval, btn);
          list.append(card);
        }
        if (!data.jobs?.length) list.append(document.createTextNode('No imported video jobs.'));
      } catch (err) { setStatus('Video review unavailable: ' + err.message); }
    };
    el('video-review-import').addEventListener('click', async () => {
      try {
        const job = JSON.parse(el('video-review-json').value);
        const result = await post('/api/operator/video/import', {job});
        setStatus('Imported ' + result.job_id + ' for review; no recording has started.');
        await refresh();
      } catch (err) { setStatus('Import rejected: ' + err.message); }
    });
    el('video-review-refresh').addEventListener('click', refresh);
    refresh();
  });
})();
