"""Opt-in, publisher-approved continuity learning from websites and RSS feeds.

A YouTube HTTP 429 does not block unrelated source lanes or grant permission
to evade YouTube access restrictions. This module never claims that studying
alternative public documentation is equivalent to watching a particular video.

All URL discovery is bounded by a plan the operator explicitly activates.
No open-web search, link following outside an allowlist, proxy rotation, or
automatic requeue of failed YouTube assignments is performed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

from suryadev_feeder import read_plan, feed_once
from suryadev_liveops import atomic_json
from suryadev_publisher import recover_failed_video_from_publisher

RUNTIME_FILE = "continuity-runtime.json"
PACK_NAME = "official-tech-education"
# Small, independent, official sources. Publishers may change or block any
# URL; each assignment is still verified or recorded as an honest failure.
OFFICIAL_TECH_URLS = (
    "https://docs.python.org/3/howto/argparse.html",
    "https://docs.python.org/3/howto/logging.html",
    "https://docs.python.org/3/howto/ipaddress.html",
    "https://docs.python.org/3/howto/urllib2.html",
    "https://docs.python.org/3/howto/sockets.html",
    "https://docs.python.org/3/howto/regex.html",
    "https://docs.python.org/3/library/asyncio-task.html",
    "https://docs.python.org/3/library/venv.html",
    "https://docs.python.org/3/library/contextlib.html",
    "https://developers.cloudflare.com/workers/",
    "https://developers.cloudflare.com/workflows/",
    "https://developers.cloudflare.com/durable-objects/",
    "https://developers.cloudflare.com/queues/",
    "https://developers.cloudflare.com/d1/",
    "https://developers.cloudflare.com/workers-ai/",
    "https://developers.cloudflare.com/ai-gateway/",
    "https://playwright.dev/python/docs/intro",
    "https://playwright.dev/python/docs/network",
    "https://playwright.dev/python/docs/browsers",
    "https://docs.github.com/en/actions",
    "https://docs.github.com/en/rest",
)
# Confirmed publisher feeds. They are fetched only after explicit plan opt-in.
OFFICIAL_TECH_FEEDS = (
    "https://blog.python.org/rss.xml",
    "https://github.blog/feed/",
    "https://github.blog/engineering/feed/",
)
# Official CS50 publisher captions already exercised by the real-source
# smoke test. The pairing is opt-in; it does not certify video visuals.
OFFICIAL_PUBLISHER_TRANSCRIPTS = (
    {"video_url":"https://www.youtube.com/watch?v=mgBpcQRDtl0",
     "transcript_url":"https://cdn.cs50.net/2017/fall/shorts/python/lang/en/python.srt"},
)
OFFICIAL_TECH_HOSTS = (
    "docs.python.org", "developers.cloudflare.com", "playwright.dev",
    "docs.github.com", "blog.python.org", "github.blog", "cdn.cs50.net",
)


def activate_official_pack(root):
    """Merge into, never replace, an operator's existing plan.

    Preserve quotas and all original entries. Back up an existing plan before
    a successful atomic update. Do not touch the SQLite library or launch work.
    """
    directory = Path(root).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    plan_file = directory / "learning-plan.json"
    if plan_file.is_file():
        original = json.loads(plan_file.read_text(encoding="utf-8"))
        if not isinstance(original, dict):
            raise ValueError("Existing learning-plan.json must be a JSON object")
        read_plan(plan_file)
        data = dict(original)
    else:
        data = {
            "description": "Explicitly activated official public tech learning sources",
            "approved_urls": [], "approved_feeds": [],
            "allowed_source_hosts": [],
            "max_new_per_cycle": 15, "max_queued": 60,
        }
    for key, proposed in (
        ("approved_urls", OFFICIAL_TECH_URLS),
        ("approved_feeds", OFFICIAL_TECH_FEEDS),
        ("allowed_source_hosts", OFFICIAL_TECH_HOSTS),
    ):
        items = list(data[key])
        for value in proposed:
            if value not in items:
                items.append(value)
        data[key] = items
    previous = list(data.get("approved_publisher_transcripts", []))
    for mapping in OFFICIAL_PUBLISHER_TRANSCRIPTS:
        if mapping not in previous:
            previous.append(dict(mapping))
    data["approved_publisher_transcripts"] = previous
    # All feed-discovered article hosts must be approved explicitly.
    # Validate bounds without network calls before touching existing plan.
    fd, staged_name = tempfile.mkstemp(prefix=".continuity-plan-", suffix=".tmp",
                                       dir=directory)
    os.close(fd)
    staged = Path(staged_name)
    try:
        staged.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        read_plan(staged)
        if plan_file.exists() and json.loads(plan_file.read_text(encoding="utf-8")) == data:
            return {"status":"unchanged", "plan":str(plan_file),
                    "approved_urls":len(data["approved_urls"]),
                    "approved_feeds":len(data["approved_feeds"]),
                    "source_pack":PACK_NAME}
        backup = ""
        if plan_file.is_file():
            candidate = directory / ("learning-plan.before-continuity-" +
                                     time.strftime("%Y%m%d-%H%M%S") + ".json")
            # A duplicate-safe private backup; never overwrite a previous one.
            number = 0
            while candidate.exists():
                number += 1
                candidate = directory / ("learning-plan.before-continuity-" +
                                         time.strftime("%Y%m%d-%H%M%S") +
                                         "-" + str(number) + ".json")
            shutil.copy2(plan_file, candidate)
            backup = str(candidate)
        os.replace(staged, plan_file)
        return {"status":"activated", "plan":str(plan_file),
                "backup":backup,
                "approved_urls":len(data["approved_urls"]),
                "approved_feeds":len(data["approved_feeds"]),
                "source_pack":PACK_NAME,
                "note":"A running worker requires --plan to discover new sources. "
                       "A running mission reloads the plan on its next refill."}
    finally:
        if staged.exists():
            staged.unlink()


class ContinuityFeeder:
    """Bounded, reloadable opt-in approved-source producer.

    The worker process already owns the single-worker lock. The feeder itself
    never starts workers and never retries completed/failed assignments.
    """
    def __init__(self, root, plan_path, *, refill_seconds=300,
                 fetcher=None, publisher_fetcher=None, clock=time.time):
        if not 60 <= refill_seconds <= 21600:
            raise ValueError("Refill interval must be 60..21600 seconds")
        self.root = Path(root).expanduser().resolve()
        self.plan_path = Path(plan_path).expanduser().resolve()
        self.refill_seconds = refill_seconds
        self.fetcher = fetcher
        self.publisher_fetcher = publisher_fetcher
        self.clock = clock
        self.next_due = 0
        self.last_refresh = None
        self.refresh_count = 0
        # Invalid plans fail before launching the worker, rather than
        # accidentally starting an unrestricted research process.
        read_plan(self.plan_path)

    def tick(self, lib, *, youtube_blocked=False):
        now = self.clock()
        if now < self.next_due:
            return None
        try:
            plan = read_plan(self.plan_path)  # hot reload approved-plan edits
            # Official publisher captions are independent of YouTube. A failed
            # video can get truthful TIMED-TEXT coverage without waiting for
            # YouTube's HTTP 429 guard or issuing any new YouTube request.
            publisher = (recover_failed_video_from_publisher(lib,plan) if
                         self.publisher_fetcher is None else
                         recover_failed_video_from_publisher(
                             lib,plan,fetcher=self.publisher_fetcher))
            outcome = (feed_once(lib, plan) if self.fetcher is None else
                       feed_once(lib, plan, fetcher=self.fetcher))
            error = ""
        except (ValueError, OSError, RuntimeError) as exc:
            outcome = {"added_total":0, "feed_errors":[
                {"error":type(exc).__name__ + ": " + str(exc)[:160]}]}
            error = type(exc).__name__ + ": " + str(exc)[:160]
            publisher = {"status":"error","recovered":0,"error":error}
        self.refresh_count += 1
        self.last_refresh = now
        self.next_due = now + self.refill_seconds
        counts = dict(lib.db.execute(
            "SELECT status,count(*) FROM jobs GROUP BY status").fetchall())
        result = {
            "active":True,
            "source_policy":"only_operator_approved_urls_and_feeds",
            "plan":str(self.plan_path),
            "last_refresh":now,
            "next_refresh":self.next_due,
            "refresh_count":self.refresh_count,
            "added_total":outcome.get("added_total",0),
            "publisher_recovery":publisher,
            "publisher_recovered":int(publisher.get("recovered",0)),
            "skipped_duplicate":outcome.get("skipped_duplicate",0),
            "feed_error_count":len(outcome.get("feed_errors",[])),
            "feed_errors":outcome.get("feed_errors",[])[:5],
            "queued_total":counts.get("queued",0),
            "youtube_blocked":bool(youtube_blocked),
            "alternatives":"websites_and_pdfs_only_when_approved",
            "youtube_video_equivalence_claimed":False,
            "error":error,
        }
        atomic_json(self.root, RUNTIME_FILE, result)
        return result

    def stop(self):
        # Intentionally do not clear the last observed source/feed errors.
        atomic_json(self.root, RUNTIME_FILE, {
            "active":False, "source_policy":"only_operator_approved_urls_and_feeds",
            "plan":str(self.plan_path), "last_refresh":self.last_refresh,
            "next_refresh":None, "refresh_count":self.refresh_count,
            "youtube_video_equivalence_claimed":False})


def main(argv=None):
    p = argparse.ArgumentParser(description="Opt-in continuity source plan")
    p.add_argument("--data", required=True)
    modes = p.add_subparsers(dest="command", required=True)
    modes.add_parser("activate-official-tech",
                     help="Merge public publisher documentation and two feeds into the approved plan")
    a = p.parse_args(argv)
    if a.command == "activate-official-tech":
        print(json.dumps(activate_official_pack(a.data), indent=2))


if __name__ == "__main__":
    main()
