/* Existing SURYADEV dashboard extension: supervised R39 video evidence lane.
   No R39 frontend assets, HTTP pairing, automatic recording or auto-promotion. */
(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    // The sole Video Review panel is authored in dashboard.html.
    // Do not inject a second panel or duplicate navigation entry.
    if (!document.getElementById('video-review')) return;
    const el = id => document.getElementById(id);
    let csrf = null;
    const setStatus = value => { el('video-review-status').textContent = String(value); };
    const post = async (url, body) => {
      if (!csrf) {
        const response = await window.suryadevRead('/api/operator/settings', {cache:'no-store'});
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
        const response = await window.suryadevRead('/api/video/review', {cache: 'no-store'});
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
