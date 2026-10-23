/* Existing SURYADEV dashboard extension: supervised R39 video evidence lane.
   No R39 frontend assets, HTTP pairing, automatic recording or auto-promotion. */
(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    // The sole Video Review panel is authored in dashboard.html.
    // Do not inject a second panel or duplicate navigation entry.
    if (!document.getElementById('video-review')) return;
    const el = id => document.getElementById(id);
    let autoEnabled = false;
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
        autoEnabled = data.auto_enabled === true;
        const autoToggle = el('video-auto-toggle');
        autoToggle.disabled = false;
        autoToggle.textContent = autoEnabled ? 'Disable automatic video' : 'Enable automatic video';
        el('video-auto-state').textContent = autoEnabled
          ? 'Auto video: ' + (data.auto_status || 'enabled') +
              (data.auto_error ? ' · ' + data.auto_error : '') +
              (data.auto_status === 'waiting_for_research_worker' ? ' · Waits for the other learning worker to stop.' : '')
          : 'Auto video is off. Enable it to process previously approved YouTube URLs without per-video review.';
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
    el('video-auto-toggle').addEventListener('click', async () => {
      const button = el('video-auto-toggle');
      button.disabled = true;
      try {
        const outcome = await post('/api/operator/video/auto', {enabled: !autoEnabled});
        el('video-auto-state').textContent = outcome.auto_enabled
          ? 'Automatic approved-video observations enabled.'
          : 'Automatic video observations disabled.';
      } catch (err) {
        el('video-auto-state').textContent = 'Video automation: ' + (err.message || err);
      }
      await refresh();
    });
    el('video-review-import').addEventListener('click', async () => {
      try {
        const advanced = el('video-review-json').value.trim();
        let job;
        if (advanced) {
          job = JSON.parse(advanced);
        } else {
          const target = el('video-review-url').value.trim();
          let parsed;
          try { parsed = new URL(target); } catch (_) {
            throw new Error('Enter a complete HTTPS video URL');
          }
          if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.hash) {
            throw new Error('Only public HTTPS video URLs without credentials or fragments are supported');
          }
          const rawTerms = el('video-review-terms').value.trim();
          const terms = rawTerms ? rawTerms.split(',').map(x => x.trim()).filter(Boolean) : [];
          if (terms.length > 80 || terms.some(term => term.length > 100)) {
            throw new Error('Use at most 80 important terms, each under 100 characters');
          }
          const duration = Number(el('video-review-minutes').value);
          if (![2,10,30,60].includes(duration)) throw new Error('Invalid observation duration');
          job = {
            schema: 'krishna.suryadev.job.v1',
            job_id: 'video-' + Date.now().toString(36) + '-' +
              Math.random().toString(36).slice(2,8),
            kind: 'video_research',
            target,
            constraints: {
              duration_seconds: duration * 60,
              adaptive_playback: el('video-review-adaptive').checked,
              capture_terms: terms,
              allow_audio_asr_fallback: false
            }
          };
        }
        const result = await post('/api/operator/video/import', {job});
        if (advanced) el('video-review-json').value = '';
        setStatus('Imported ' + result.job_id + ' for review; no recording has started.');
        await refresh();
      } catch (err) { setStatus('Import rejected: ' + err.message); }
    });
    el('video-review-refresh').addEventListener('click', refresh);
    refresh();
  });
})();
