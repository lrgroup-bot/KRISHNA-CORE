/* Existing SURYADEV dashboard extension: supervised R39 video evidence lane.
   No R39 frontend assets, HTTP pairing, automatic recording or auto-promotion. */
(() => {
  'use strict';
  document.addEventListener('DOMContentLoaded', () => {
    // The sole Video Review panel is authored in dashboard.html.
    // Do not inject a second panel or duplicate navigation entry.
    if (!document.getElementById('video-review')) return;
    const el = id => document.getElementById(id);
    const setStatus = value => { el('video-review-status').textContent = String(value); };
    const refresh = async () => {
      try {
        const response = await window.suryadevRead('/api/video/review', {cache: 'no-store'});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Read failed');
        el('video-auto-state').textContent = data.auto_enabled
          ? 'Approved-video observation: ' + String(data.auto_status || 'enabled') +
              (data.auto_error ? ' · ' + data.auto_error : '')
          : 'Video observation not yet enabled. This trial is activated by the worker startup package.';
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
          card.append(heading, url);
          list.append(card);
        }
        if (!data.jobs?.length) list.append(document.createTextNode('No imported video jobs.'));
      } catch (err) { setStatus('Video review unavailable: ' + err.message); }
    };
    const auditTarget = el('youtube-audit-results');
    const durationText = seconds => {
      if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) return 'not recorded';
      if (seconds < 60) return seconds.toFixed(1) + 's';
      return Math.floor(seconds / 60) + 'm ' + Math.floor(seconds % 60) + 's';
    };
    const addLine = (parent, value, strong=false) => {
      const item = document.createElement('p');
      item.textContent = String(value);
      if (strong) item.style.fontWeight = '600';
      parent.append(item);
    };
    async function refreshAudit() {
      try {
        const response = await window.suryadevRead('/api/youtube/audit', {cache:'no-store'});
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const audit = await response.json();
        if (audit.schema !== 'suryadev.youtube-learning-audit.v1') {
          throw new Error('Update SURYADEV backend to enable evidence audit');
        }
        auditTarget.replaceChildren();
        const captions = audit.caption_extraction || [];
        const observed = audit.browser_observations || [];
        addLine(auditTarget, captions.length + ' caption jobs · ' + observed.length +
          ' browser observation jobs · Independent Rishi verification not established', true);
        if (!captions.length && !observed.length) {
          addLine(auditTarget, 'No measured YouTube learning found in this local data directory yet.');
          return;
        }
        const section = title => {
          const h = document.createElement('h4');
          h.textContent = title;
          auditTarget.append(h);
        };
        section('Caption extraction · NO video playback claimed');
        for (const item of captions.slice(0,12)) {
          const card = document.createElement('article');
          card.className = 'video-review-job';
          addLine(card, '#' + item.job_id + ' · ' + (item.title || item.url) + ' · ' + item.status, true);
          addLine(card, 'Actual wall time: collection ' + durationText(item.acquisition_wall_seconds) +
            ' · analysis ' + durationText(item.analysis_wall_seconds) +
            ' · total ' + durationText(item.total_wall_seconds));
          addLine(card, 'Video duration: ' + durationText(item.video_duration_seconds) +
            ' · timed caption cues: ' + (item.caption_cues ?? 'unknown') +
            ' · last cue: ' + durationText(item.last_caption_seconds) +
            ' · missing-caption gaps: ' + item.long_caption_gaps);
          addLine(card, 'Analysis: ' + (item.analysis_method || 'not available') +
            ' · chunks summarized: ' + (item.chunks_summarized ?? '?') +
            '/' + (item.chunks_total ?? '?'));
          addLine(card, 'What text says (not verified learning): ' +
            (item.what_extracted_or_summarized || item.error || 'No saved finding yet'));
          addLine(card, 'Video footage watched: NO · BRAHMAGYAN exam verified: NO');
          auditTarget.append(card);
        }
        section('Browser playback observation · completeness UNVERIFIED');
        for (const item of observed.slice(0,12)) {
          const card = document.createElement('article');
          card.className = 'video-review-job';
          addLine(card, item.job_id + ' · ' + (item.title || item.url) + ' · ' + item.status, true);
          addLine(card, 'Actual wall time: ' + durationText(item.wall_clock_seconds) +
            ' · last video position: ' + durationText(item.last_playback_position_seconds) +
            ' / ' + durationText(item.source_duration_seconds) +
            ' · ended: ' + (item.video_ended ? 'yes' : 'not verified'));
          addLine(card, 'Captured: ' + (item.captured_caption_lines ?? '?') +
            ' caption/ASR lines · ' + item.learning_candidate_chunks +
            ' candidate topic chunks · ' + item.visual_frame_samples +
            ' selected frame samples');
          addLine(card, 'Recorded source: ' + item.caption_or_asr_source +
            ' · high-speed 4x observed: ' + (item.four_x_observed ? 'yes' : 'no') +
            ' · KRISHNA receipt: ' + (item.receipt_recorded ? 'recorded; independently unverified' :
              item.awaiting_server_ack ? 'pending' : 'not recorded'));
          for (const chunk of item.what_was_collected || []) {
            addLine(card, 'Candidate topic ' + (chunk.topic || 'unclassified') +
              ' [' + durationText(chunk.start_seconds) + '–' +
              durationText(chunk.end_seconds) + ']: ' + chunk.candidate_text);
          }
          addLine(card, 'Full audio/visual understanding: NOT VERIFIED · Rishi exam: NOT VERIFIED');
          auditTarget.append(card);
        }
      } catch (err) {
        auditTarget.textContent = 'YouTube learning audit unavailable: ' + (err.message || err);
      }
    }
    el('youtube-audit-refresh').addEventListener('click', refreshAudit);
    setInterval(refreshAudit, 15000);

    async function refreshTrial() {
      try {
        const response = await window.suryadevRead('/api/trial/audit', {cache:'no-store'});
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const report = await response.json();
        const book = report.book || {}, video = report.video || {};
        el('learning-trial-audit').textContent =
          'Book: ' + String(book.model_lines_processed ?? 0) + ' / ' +
          String(book.indexed_lines ?? 0) + ' lines processed · Journal: ' +
          String(book.journal_integrity || 'not checked') +
          ' · YouTube: ' + String(video.assignment_status || 'not queued') +
          ' · Measured candidate chunks: ' + String(video.candidate_chunks ?? 0) +
          ' · Sampled frames: ' + String(video.sampled_frames ?? 0) +
          ' · Rishi verified comprehension: NO';
      } catch (err) {
        el('learning-trial-audit').textContent =
          'Automated trial audit unavailable: ' + String(err.message || err);
      }
    }
    el('video-review-refresh').addEventListener('click', () => {
      refresh(); refreshTrial(); refreshAudit();
    });
    setInterval(refreshTrial, 30000);
    setInterval(refresh, 15000);
    refreshTrial();
    refresh();
    refreshAudit();
  });
})();
