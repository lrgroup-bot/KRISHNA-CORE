"""Operator-requested source workload caps. Never increases hardware admission.

No new source approvals or retries. The optional video-trial selection is
persisted once, using only SHA-derived job IDs for fresh, currently approved
URLs. Subsequent restarts preserve that exact selection; changing the allowed
source plan cannot quietly authorize a replacement video.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import time

VIDEO_FILE = "video-trial-selection.json"
VIDEO_SCHEMA = "suryadev.video-trial-selection.v1"
ENV_KEYS = {
    "website": ("SURYADEV_TRIAL_WEBSITE_TARGET", 5),
    "pdf": ("SURYADEV_TRIAL_PDF_TARGET", 5),
    "book": ("SURYADEV_TRIAL_BOOK_TARGET", 5),
    "video": ("SURYADEV_TRIAL_VIDEO_COUNT", 3),
}


def trial_cap(kind, *, environ=None):
    """None=ordinary defaults. Invalid explicit caps fail closed (zero)."""
    environ = os.environ if environ is None else environ
    key, maximum = ENV_KEYS[kind]
    raw = environ.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.isdecimal():
        return 0
    value = int(raw)
    return value if 1 <= value <= maximum else 0


def video_job_id(url):
    return "approved-video-" + hashlib.sha256(
        url.encode("utf-8")).hexdigest()[:16]


def _eligible_trial_jobs(urls, count, previously_tried):
    selected = []
    for url in urls:
        job_id = video_job_id(url)
        if job_id not in selected and not previously_tried(job_id):
            selected.append(job_id)
        if len(selected) == count:
            break
    return selected


def select_trial_videos(root, urls, *, previously_tried, recover_empty=False):
    """Return durable selected IDs, or None if this trial was not requested.

    Only the existing approved plan is inspected. Never authorizes a URL.
    Does not change attempts or source evidence. Fails closed if an existing
    selection is malformed, even if a different approved URL becomes available.
    """
    count = trial_cap("video")
    if count is None:
        return None
    if count == 0:
        return frozenset()
    root = Path(root).resolve()
    selection = root / VIDEO_FILE
    allowed = {video_job_id(url) for url in urls}
    if selection.exists():
        if selection.is_symlink() or selection.stat().st_size > 8192:
            raise RuntimeError("Invalid video trial selection file")
        try:
            state = json.loads(selection.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise RuntimeError("Unreadable video trial selection file") from exc
        ids = state.get("job_ids") if isinstance(state, dict) else None
        if (not isinstance(state, dict) or state.get("schema") != VIDEO_SCHEMA or
                state.get("target") != count or not isinstance(ids, list) or
                len(ids) > count or len(ids) != len(set(ids)) or
                any(not isinstance(x, str) or not x.startswith("approved-video-")
                    or len(x) != len("approved-video-") + 16 for x in ids)):
            raise RuntimeError("Corrupt/mismatched video trial selection: no new videos")
        # Repair ONLY the empty selection produced by old staged-job
        # misclassification, and only under an explicit active video-target
        # opt-in. Never add to a nonempty/frozen selection, replay attempts,
        # change approved URLs or erase the original trial receipt.
        if ids or not recover_empty:
            return frozenset(ids) & allowed
        fresh = _eligible_trial_jobs(urls, count, previously_tried)
        if not fresh:
            return frozenset()
        backup = root / ("video-trial-selection.before-empty-repair-"
                         + hashlib.sha256(selection.read_bytes()).hexdigest()[:16]
                         + ".json")
        with backup.open("xb") as output:
            output.write(selection.read_bytes())
        amended = dict(state, job_ids=fresh, repaired_from_empty=True,
                       repaired_at=time.time(),
                       previous_selection_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
                       note="Recovered previously approved, truly unattempted videos only; original archived")
        stage = root / (".video-trial-recovery-" + secrets.token_hex(8) + ".tmp")
        try:
            stage.write_text(json.dumps(amended, indent=2)+"\n", encoding="utf-8")
            os.replace(stage, selection)
        finally:
            stage.unlink(missing_ok=True)
        return frozenset(fresh)
    selected = _eligible_trial_jobs(urls, count, previously_tried)
    record = {
        "schema": VIDEO_SCHEMA, "target": count, "job_ids": selected,
        "updated_at": time.time(), "approved_videos_available": len(allowed),
        "note": "One-time set of existing approved, unattempted videos only."
    }
    selection.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation and never replace a previous trial's selection.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(selection,flags,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as handle:
            handle.write(json.dumps(record,indent=2)+"\n")
    except BaseException:
        # Never delete partially written audit/selection files silently.
        raise
    return frozenset(selected)
