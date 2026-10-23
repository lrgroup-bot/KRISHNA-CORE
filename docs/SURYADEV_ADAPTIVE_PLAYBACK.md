# SURYADEV adaptive browser-video playback (R39 unified repo frontend)

## Requested behavior (owner, 2026-10-23)
Speed varies with **importance of information**, not the wall-clock mission schedule.
- **1×** — technical details, numbers, commands, step-by-step instructions, warnings, equations, owner-provided capture terms, unfamiliar-language captions, missing captions, audio-only fallback.
- **1.5×** — explanatory material that needs careful understanding.
- **2×** — ordinary material with readable captions.
- **4×** — identifiable low-value chatter (e.g. greetings/subscribe reminders) **after two distinct consecutive chatter captions** and only while captions are visible and changing.

The observer continuously watches the selected YouTube/browser video. Its caption classifier is a **conservative heuristic**, not deep semantic understanding. Important points not matching a cue may still be missed, especially at 4×. It automatically drops to 1× on new critical material, unreadable/missing/stale captions or audio-only speech recognition. It never seeks forward and never downloads source video.

## Platform limits
The adapter requests one of exactly 1.0, 1.5, 2.0 or 4.0 via the browser's HTMLVideoElement playbackRate and reads back the **actual** rate; the video player may reject or reset 4×. It only reports observed rates. Sampling is capped at 0.5s wall time when adaptive playback is active (about 2s of video at 4×); this still does **not** guarantee complete timed-caption or audiovisual coverage.

## Job specification
Provide this JSON in the existing GitHub SURYADEV dashboard's **Video Review** section, after adding the **exact** URL to the local learning-plan.json. The example URL is a placeholder, not automatically approved.

\`\`\`json
{
  "schema": "krishna.suryadev.job.v1",
  "job_id": "video-speed-smoke-01",
  "kind": "video_research",
  "target": "https://www.youtube.com/watch?v=APPROVED_VIDEO_ID",
  "constraints": {
    "duration_seconds": 120,
    "adaptive_playback": true,
    "capture_terms": ["important", "voltage", "installation", "step", "diagram"],
    "allow_audio_asr_fallback": true
  }
}
\`\`\`

A new, explicitly approved job starts with default-safe 1×. The video replay engine is the canonical repository file \`scripts/SURYDEV_VIDEO_LEARNING_ADAPTER.py\`; the Windows installer copies it as \`suryadev_r39_adapter.py\` within the existing SURYADEV app. The ZIP frontend is not used.

## Live observability and truthful evidence
- The source video adapter writes \`video-review/runtime/jobs/JOB-ID/playback-speed.json\` with browser-readback speed, content classification and video timestamp.
- \`GET /api/video/review\` exposes current playback data only for an active supervised job. Use **Refresh jobs** in Video Review to see current speed.
- Final \`learning-bundle.json\` records recent speed transitions, number of transitions, whether 4× was observed, and explicitly records \`complete_caption_coverage_verified: false\`.
- Neither speeding up nor finishing a video proves that SURYADEV comprehended its content or that BRAHMAGYAN/Rishis accepted evidence.
- Connection to KRISHNA still requires pinned HTTPS and authorized evidence receipts. Do not use R39 HTTP bearer sync.

## Testing and release gates
The additional automated test module \`standalone/suryadev/tests/test_adaptive_video_playback.py\` covers ordinary, explanations, technical, owner terms, chatter stability, Hindi/Odia safety, missing captions, ASR mode, stalls, speed disabled and player readback. Source-level and Windows/Linux CI tests are necessary but insufficient.

For Windows real-device acceptance: use one approved short public video with captions, inspect the running dashboard readout and actual browser video speed, ensure technical material returns to 1×, verify 4× only for clear chatter, and inspect pending evidence without promoting or deleting it. Repeat with captions disabled and with unknown-language captions; both must stay at safe 1×. If 4× is unsupported in that browser, report the actual supported speed; never bypass the player.

## Status
Code implemented on \`feature/suryadev-r39-unified-repo-ui-20261023\` as part of draft PR #231. **No unattended deployment and no real-device 4× acceptance claim until Windows test evidence is received.**
