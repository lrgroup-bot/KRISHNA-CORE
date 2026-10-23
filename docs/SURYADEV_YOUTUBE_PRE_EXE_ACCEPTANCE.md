# SURYADEV YouTube learning: mandatory gates BEFORE any EXE installation

## Distinct processing lanes (cannot infer one from the other)

A. Source/SQLite **YouTube captions**: yt-dlp only downloads timed VTT captions on one approved video. The video and original audio are NOT downloaded/decoded. The worker records in SQLite \`job_timing\` acquisition_seconds, summary_phase_seconds and elapsed_seconds, while \`findings\` stores a local Ollama summary or explicit extractive preview and \`job_provenance\` stores caption cue/gap metrics. HTTP 429 must stop new provider requests and is not auto-retried. This is **caption-text processing**, not full-video viewing, audio comprehension, or proven mastery.

B. Canonical **browser-video observer**: Chrome/Playwright opens an owner-approved YouTube video; the R39 adapter reads on-screen captions and occasional frame screenshots, optionally local audio ASR, and writes bounded candidate chunks in \`video-review/runtime/jobs/<job_id>/learning-bundle.json\` plus real timing/playback-position metadata. A playback timestamp (named \`watched_seconds\` in legacy R39 bundle) is HTML \`video.currentTime\`, NOT independently verified elapsed time watched. Wall-clock \`ended_at-started_at\` can differ due to 1.5x/2x/4x speed, buffering, pauses or starts. \`video_ended\` records the browser flag only. No eye/ear/factual mastery is proven.

C. BRAHMAGYAN / Rishi: learning-bundle existence or \`AWAITING_SERVER_ACK\` does not prove the content has been accepted, retained, examined or used. Separate authenticated Core intake receipt + independent Rishi practical/theory exam are required.

## Read-only diagnostic

From a current checked-out development source after the audit commit:

\`\`\`powershell
cd "D:\Work\SURYADEV-UNIFIED-R39-SOURCE\standalone\suryadev"
python .\suryadev_youtube_audit.py --data "D:\Work\SURYADEV-UNIFIED-TEST-DATA" --limit 20
\`\`\`

No new YouTube calls, no worker restart, no media file edits and no SQLite schema changes. If \`/api/youtube/audit\` is installed in the **updated** dashboard, \`Invoke-RestMethod http://127.0.0.1:8771/api/youtube/audit | ConvertTo-Json -Depth 7\` presents the same fields. The UI's Video review section displays them in separate caption/observer categories. An old installed dashboard cannot expose that endpoint until safely updated.

## A concrete supervised live YouTube acceptance trial

1. Record baseline \`/api/youtube/audit\` and \`/api/video/review\`. The latter MUST clearly report \`auto_status\` and whether a research worker holds the lock. Distinguish active worker from actual video playback.
2. Use ONE publicly available, explicitly approved ≤10-minute technical/educational video with captions and real examples. Record its exact URL, duration, title, speaker/publisher, language and expected learning questions. Do not attempt to bypass YouTube 429 or login/CAPTCHA requirements.
3. Verify the caption lane separately. Expect one task row with completed/failure status, acquisition and analysis time, cue count/timeline/gaps, evidence hash, saved summary method, \`chunks_summarized/chunks_total\`. A \`done\` means source task done only.
4. If the owner wants browser observation, stop the **existing** worker gracefully *on its own terminal* (do not kill it or delete the lock), enable the reviewed video-auto lane or run one explicitly approved video job, and observe that Chromium actually plays it. Record requested vs observed rate, time position, actual elapsed seconds, selected frames/caption lines, and the evidence bundle SHA-256. Do not claim complete coverage from the first/last timestamp.
5. If a continuous research worker is running, the current browser auto scheduler deliberately reports \`waiting_for_research_worker\`, so **it cannot proceed unattended**. A future safe, cooperative single-worker handoff is needed. This is a *known release blocker*, not a passing automatic video-learning test.
6. Inspect a real learning chunk. Identify at least 3 factual claims with precise source timestamps; identify any examples or demonstrations that require frames rather than captions; identify missing speech/captions, contradictions and ambiguous frames. Run an independent Rishi exam or mark no mastery.
7. Verify Core ACK and a genuine BRAHMAGYAN intake receipt separately. Never accept local \`AWAITING_SERVER_ACK\` as a Core receipt. Verify 429 recovery only after provider cooldown, no retry loops, dedup, Windows CPU/RAM safety, and persistence across reboot.
8. Browser acceptance / worker regression / Windows+Linux unit tests must all pass. **No new EXE release** until an actual two-PC replay demonstrates the work and the self-refilling observer can reliably run without starving the primary worker.

## Required actual evidence for any 'learned' claim

- Real source title+URL+duration+language; timestamped captions and observed frames, both checked
- Actual acquisition, local inference and observer wall times (distinct from playback position)
- Traceable source chunk content, claim IDs, counterexamples, tests, errors and missing windows
- Verified evidence hashes/ACKs; independent Rishi examiner score and provenance

\`rishi_exams_verified: 0\` from the new local audit means **no exams are verified by this audit**, not necessarily that no other system has an exam ledger.
