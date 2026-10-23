"""Owner-approved six-hour source feeder.

It does not invent topics or search the open internet. Sources arrive only from
explicit approved URLs and opted-in RSS/Atom feeds. Never enabled at install.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler
import xml.etree.ElementTree as ET

from suryadev import Library, validate_url, StrictRedirect
from suryadev_liveops import atomic_json

# Some approved publisher RSS feeds embed article HTML and exceed 1 MiB.
# Keep a strict finite per-response size; never allow unbounded downloads.
MAX_FEED_BYTES = 8 * 1024 * 1024
FEED_STATE = "feeder-runtime.json"
HOST_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,250}[a-z0-9])?$")


def approved_host(raw):
    if not isinstance(raw, str):
        raise ValueError("host must be a string")
    host = raw.strip().lower()
    if (len(host) > 253 or not HOST_PATTERN.fullmatch(host)
            or host.startswith(".") or ".." in host or host.endswith(".")):
        raise ValueError("invalid allowed host")
    return host


def read_plan(path):
    data = json.loads(Path(path).expanduser().resolve(strict=True).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("feed plan must be an object")
    approved_urls = data.get("approved_urls", [])
    approved_feeds = data.get("approved_feeds", [])
    allowed_hosts = data.get("allowed_source_hosts", [])
    if any(not isinstance(x, list) for x in (approved_urls, approved_feeds, allowed_hosts)):
        raise ValueError("approved_urls, approved_feeds and allowed_source_hosts must be arrays")
    if len(approved_urls) > 300 or len(approved_feeds) > 25 or len(allowed_hosts) > 200:
        raise ValueError("source feed plan exceeds configuration limits")
    approved_urls = [str(x) for x in approved_urls]
    approved_feeds = [str(x) for x in approved_feeds]
    hosts = {approved_host(x) for x in allowed_hosts}
    for url in approved_urls + approved_feeds:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("approved feed URLs must use HTTPS without credentials")
        if parsed.port not in (None, 443):
            raise ValueError("approved feed URL uses nonstandard port")
    # Publisher-hosted timed transcripts are NOT discovered or downloaded
    # implicitly. Each video-to-caption mapping is expressly approved, on
    # a public HTTPS host already named in the source allowlist.
    publisher = data.get("approved_publisher_transcripts", [])
    if not isinstance(publisher, list) or len(publisher) > 20:
        raise ValueError("approved_publisher_transcripts must be an array of at most 20 mappings")
    from suryadev_ingest import _youtube_url
    known_videos = set()
    approved_publisher = []
    for entry in publisher:
        if not isinstance(entry, dict) or set(entry) != {"video_url", "transcript_url"}:
            raise ValueError("publisher mapping must contain exactly video_url and transcript_url")
        video, transcript = entry["video_url"], entry["transcript_url"]
        if not isinstance(video, str) or not isinstance(transcript, str):
            raise ValueError("publisher mapping URLs must be strings")
        video_id = _youtube_url(video)
        if video_id in known_videos:
            raise ValueError("duplicate approved publisher mapping for a video")
        if not allowed_source(transcript, hosts):
            raise ValueError("publisher transcript URL must be HTTPS on an explicitly allowed host")
        if not urlsplit(transcript).path.lower().endswith((".srt", ".vtt")):
            raise ValueError("publisher alternate must be a timestamped .srt or .vtt URL")
        known_videos.add(video_id)
        approved_publisher.append({"video_url":video, "transcript_url":transcript})

    delegate = data.get("paired_core_host_delegation", False)
    if not isinstance(delegate, bool):
        raise ValueError("paired_core_host_delegation must be a boolean")
    budget = data.get("max_new_per_cycle", 20)
    backlog = data.get("max_queued", 75)
    if not isinstance(budget, int) or not (1 <= budget <= 100):
        raise ValueError("max_new_per_cycle must be from 1 to 100")
    if not isinstance(backlog, int) or not (1 <= backlog <= 1000):
        raise ValueError("max_queued must be from 1 to 1000")
    return {"approved_urls": approved_urls, "approved_feeds": approved_feeds,
            "allowed_source_hosts": hosts,
            "paired_core_host_delegation": delegate,
            "approved_publisher_transcripts":approved_publisher,
            "max_new_per_cycle": budget,
            "max_queued": backlog}


def paired_core_source_allowed(url, plan):
    """Admit only a paired KRISHNA task within the operator-delegated policy.

    This is a *source permission*, not permission to execute source content,
    authorize new hosts, accept knowledge or bypass provider restrictions.
    The caller must already have authenticated KRISHNA using pinned TLS.
    """
    if not isinstance(url, str) or len(url) > 2048 or not url:
        return False
    if url in plan["approved_urls"]:
        return True
    if plan.get("paired_core_host_delegation") is not True:
        return False
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.hostname not in plan["allowed_source_hosts"]
                or parsed.username or parsed.password
                or parsed.fragment or parsed.port not in (None,443)):
            return False
        # Resolves DNS and rejects loopback/private/non-public IPs.
        from suryadev import validate_url
        validate_url(url)
    except (OSError, ValueError):
        return False
    return True


def fetch_feed(url):
    validate_url(url)
    opener = build_opener(ProxyHandler({}), StrictRedirect())
    req = Request(url, headers={"User-Agent": "SURYADEVFeed/1.0 (approved RSS)",
                                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
                                "Accept-Encoding": "identity"})
    with opener.open(req, timeout=25) as response:
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("compressed feed not supported")
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_FEED_BYTES:
            raise ValueError(f"feed is too large (maximum {MAX_FEED_BYTES} bytes)")
        data = response.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("feed is too large")
    return data


def feed_links(raw):
    """Extract RSS item or Atom entry URLs. No recursive crawling or content exec."""
    # A raw-byte substring search incorrectly flags examples inside CDATA,
    # including articles quoting an HTML <!DOCTYPE>. Parse XML structure
    # instead, rejecting *actual* DTD/ENTITY declarations before ElementTree
    # builds a document. This retains the strict no-entity-expansion policy.
    from xml.parsers import expat
    def reject_declaration(*_args):
        raise ValueError("DTD/ENTITY declarations are forbidden in feeds")
    probe = expat.ParserCreate()
    probe.StartDoctypeDeclHandler = reject_declaration
    probe.EntityDeclHandler = reject_declaration
    probe.ExternalEntityRefHandler = reject_declaration
    probe.Parse(raw, True)
    root = ET.fromstring(raw)
    urls = []
    for item in root.iter():
        tag = item.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        for child in item:
            suffix = child.tag.rsplit("}", 1)[-1]
            if suffix == "link":
                link = (child.get("href") or child.text or "").strip()
                relation = child.get("rel", "alternate")
                if link and relation in ("alternate", ""):
                    urls.append(link)
                    break
    return urls[:250]


def allowed_source(url, hosts):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or
            parsed.username or parsed.password or parsed.port not in (None, 443)):
        return False
    return parsed.hostname.lower() in hosts


def feed_once(lib, plan, *, fetcher=fetch_feed):
    """Idempotent producer; completed URLs are not silently re-enqueued."""
    stats = lib.stats()
    space = max(0, plan["max_queued"] -
                stats.get("queued", 0) - stats.get("running", 0))
    budget = min(plan["max_new_per_cycle"], space)
    known = {row[0] for row in lib.db.execute("SELECT DISTINCT url FROM jobs")}
    candidates = [(url, "owner-approved") for url in plan["approved_urls"]]
    errors = []
    if budget:
        for feed in plan["approved_feeds"]:
            try:
                for url in feed_links(fetcher(feed)):
                    if allowed_source(url, plan["allowed_source_hosts"]):
                        candidates.append((url, "approved-feed:" + feed))
            except (ValueError, OSError, ET.ParseError, RuntimeError) as exc:
                errors.append({"feed": feed, "error": type(exc).__name__ + ": " + str(exc)[:140]})
    added = []
    skipped = 0
    for url, origin in candidates:
        if len(added) >= budget:
            break
        if url in known:
            skipped += 1
            continue
        try:
            if origin != "owner-approved" and not allowed_source(url, plan["allowed_source_hosts"]):
                skipped += 1
                continue
            # Library.add applies public-DNS and HTTPS URL validation again.
            job_id = lib.add(url)
            known.add(url)
            added.append({"job_id": job_id, "url": url, "origin": origin})
        except (ValueError, OSError) as exc:
            errors.append({"url": url[:170], "error": type(exc).__name__ + ": " + str(exc)[:140]})
    return {"added": added, "added_total": len(added),
            "skipped_duplicate": skipped, "queued_before": stats.get("queued", 0),
            "capacity": budget, "feed_errors": errors[:30]}


def serve_feeder(data, plan_filename, *, loop=False, hours=6):
    if not (1 <= hours <= 48):
        raise ValueError("hours must be from 1 to 48")
    root = Path(data).expanduser().resolve()
    plan = read_plan(plan_filename)
    while True:
        started = time.time()
        lib = Library(root)
        try:
            outcome = feed_once(lib, plan)
        finally:
            lib.db.close()
        next_at = started + hours * 3600 if loop else None
        atomic_json(root, FEED_STATE, {
            "last_run": started, "next_run": next_at,
            "period_hours": hours if loop else None,
            "loop_enabled": bool(loop), "added_total": outcome["added_total"],
            "feed_error_count": len(outcome["feed_errors"]),
        })
        print(json.dumps(outcome, indent=2, ensure_ascii=False), flush=True)
        if not loop:
            return outcome
        time.sleep(max(1, next_at - time.time()))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Explicit approved-source six-hour research queue feeder")
    ap.add_argument("--data", required=True)
    ap.add_argument("--plan", required=True, help="JSON with approved URLs/feeds and permitted hosts")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--loop", action="store_true", help="recheck opted-in RSS/Atom feeds every six hours")
    ap.add_argument("--hours", type=int, default=6)
    args = ap.parse_args(argv)
    serve_feeder(args.data, args.plan, loop=args.loop, hours=args.hours)


if __name__ == "__main__":
    main()
