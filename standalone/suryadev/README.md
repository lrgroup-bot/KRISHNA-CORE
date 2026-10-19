# SURYADEV Standalone — experimental Windows laptop worker

**Scope:** independent local learning; does not connect to KRISHNA, BRAHMA, or other agents.
This is an initial working slice, **not** a certified autonomous video/screen learner.

## Prerequisites
- Python 3.10+ on Windows.
- Optional: Ollama running locally on `127.0.0.1:11434` with `qwen3.5:9b`.
- No paid API keys and no inbound LAN port required.

## First-run commands (PowerShell)

```powershell
cd standalone\suryadev
python suryadev.py --data "$env:USERPROFILE\SURYADEV-DATA" status
python suryadev.py add "https://example.com/"
python suryadev.py run --no-ollama
python suryadev.py search "Example"
python -m unittest discover -s tests -v
```

For Qwen summarization: `python suryadev.py run --model qwen3.5:9b`.
Each `run` processes **one** queued job. Use Task Scheduler only after the tests pass.
Data is stored in `~/SURYADEV-DATA/suryadev.sqlite3`. Back up the SQLite database
while the worker is stopped or via SQLite's online backup API.

## Present capabilities
- Explicitly approved public HTTPS HTML/plain-text fetch (2 MB response cap).
- Local SQLite queue, findings, hashes, duplicate identification, keyword search.
- Optional loopback Qwen summarization with extractive fallback.
- Resumption of interrupted jobs on the next `run` command.
- No dependence on the main PC or other agents.

## Important limitations
- **Not** a full YouTube watcher, video downloader, STT system, screen capture tool,
  GitHub analyzer, autonomous browser or GUI dashboard.
- No continuous scheduling, multi-source verification, semantic retrieval or guaranteed
  factual validation yet. Failed jobs are retained for inspection, not automatically retried.
- Public URL checks and redirect blocking are defense in depth; DNS rebinding and network
  interception need additional controls before accepting untrusted URLs at scale.
- Respect copyright, robots.txt, site policies and authorization. Only add sources
  you have permission to process.
- This experimental module has unit tests but requires Windows hardware acceptance.
- Never claim a source summary is independently verified simply because Qwen generated it.

## Release acceptance checklist
1. Run all unit tests and repository CI.
2. Verify the Windows Python/Ollama setup on the laptop.
3. Study an approved real public page and inspect its stored finding.
4. Restart and verify persistent search and queue recovery.
5. Test offline, bad URLs, large responses and model-unavailable fallback.
6. Only then consider background scheduling and further media capabilities.


## Added standalone extensions

Run these commands from `standalone\\suryadev`:

```powershell
# Import a locally saved transcript (.txt, .srt, or .vtt)
python suryadev_extras.py import-transcript "C:\\Videos\\lesson.vtt" --no-ollama

# Use local Qwen for transcript summaries
python suryadev_extras.py import-transcript "C:\\Videos\\lesson.vtt" --model qwen3.5:9b

# Run queued, explicitly added HTTPS research jobs every 60 seconds
python suryadev_extras.py worker --interval 60

# In a separate terminal, open the local read-only dashboard
python suryadev_extras.py dashboard --port 8769
# Open http://127.0.0.1:8769/
```

The worker does not discover or enqueue sources automatically. The dashboard
is loopback-only, read-only and searches saved findings. The importer does not
download YouTube videos or generate transcripts from audio; provide a lawful
transcript file. A full media capture/transcription pipeline and packaged Windows
installer still require separate development and real-device tests.

## Operational caution
Do not run multiple writer processes against the same database until the
single-writer/locking design is strengthened. Back up the database before
upgrading. Keep local files containing personal/private content out of the
learning queue unless you explicitly authorize processing.

## Optional media-learning modules

These features are opt-in and need additional free Python packages:

```powershell
python -m pip install faster-whisper yt-dlp playwright
python -m playwright install chromium
```

Examples, run from `standalone\\suryadev`:

```powershell
# Transcribe a local audio/video file and save findings
python suryadev_media.py transcribe "C:\\Learning\\lecture.mp3" --device cpu

# Import YouTube captions if publicly available (no video download)
python suryadev_media.py youtube-subtitles "https://www.youtube.com/watch?v=VIDEO_ID"

# Screenshot only a user-approved public website
python suryadev_media.py capture-page "https://example.com/" "captures\\example.png" --allow-host example.com
```

Audio decoding/transcription uses faster-whisper; CPU int8 is the default.
YouTube subtitle retrieval uses yt-dlp and may fail for unavailable captions,
geo restrictions or service changes. Browser capture uses Playwright with
explicit host allowlisting and does not click, submit or authenticate.
Capture is **not** permission to monitor private screens. These tools do not
start automatically or access a microphone.

## Remaining release gates
- Run actual Windows unit and integration tests, including the optional packages.
- Test YouTube subtitle availability and local transcription quality.
- Add a verified single-instance worker lock, source policy/robots review,
  provenance and evidence retention improvements, and browser egress hardening
  before unattended broad-scale crawling.
- Test the dashboard in Chromium and perform restart, outage and backup drills.
- Package a Windows installer only after these gates pass.

## Full evidence and backup

Web and transcript ingestion now store up to 2 MB of normalized full text in
`SURYADEV-DATA/evidence/<first-two-hash-chars>/<sha256>.txt`. Findings
still contain short excerpts and summaries for search. Evidence is
content-addressed; use the integrity command to detect changed files.

```powershell
python suryadev_extras.py verify-evidence
python suryadev_extras.py backup "C:\\Backups\\suryadev.sqlite3"
```

The database backup uses SQLite's online backup API. **The evidence directory
must also be backed up**; the database backup alone does not preserve full text.
Source URLs and hashes are retained in the findings database, but a formal
source-verification and licensing policy remains to be implemented.
