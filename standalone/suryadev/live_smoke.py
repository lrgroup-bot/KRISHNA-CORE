"""Real public-source SURYADEV smoke run.

Unlike unit mocks, this contacts approved public HTTPS sources. Network or
provider denial is reported as BLOCKED, never called learning success.

Run with: python live_smoke.py
Dependencies: python -m pip install pypdf yt-dlp
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import time
import traceback

from suryadev import Library
from suryadev_task_details import task_detail
from suryadev_ingest import caption_cues, caption_report
from suryadev import validate_url, StrictRedirect
from suryadev_extras import import_transcript
from suryadev_publisher import recover_failed_video_from_publisher
from suryadev_feeder import read_plan
from urllib.request import Request, build_opener, ProxyHandler

TEST_SOURCES = (
    ("website", "https://www.python.org/about/"),
    ("pdf", "https://samplepdf.org/files/sample.pdf"),
    ("pdf_multi", "https://raw.githubusercontent.com/tinytoolkit-org/pdf-sample-files/master/out/sample-10-pages.pdf"),
    ("pdf_scanned", "https://raw.githubusercontent.com/tinytoolkit-org/pdf-sample-files/master/out/sample-scanned.pdf"),
    ("youtube", "https://www.youtube.com/watch?v=mgBpcQRDtl0"),
    ("publisher_srt", "https://cdn.cs50.net/2017/fall/shorts/python/lang/en/python.srt"),
    ("publisher_auto_fallback", "https://cdn.cs50.net/2017/fall/shorts/python/lang/en/python.srt"),
)


def classify(error):
    lower = str(error).casefold()
    network = ("http error", "urlopen error", "timed out", "connection refused",
               "remote end closed", "forbidden", "certificate verify",
               "network is unreachable", "unable to download",
               "sign in to confirm", "requested format is not available",
               "video unavailable", "no supported youtube captions available",
               "unable to extract", "unsupported url")
    if any(s in lower for s in network):
        return "BLOCKED_EXTERNAL"
    return "FAILED"


def verify_result(detail, kind):
    if detail["status"] != "done":
        return False, "Worker did not finish: " + str(detail["error"])
    if detail["evidence_state"] != "verified":
        return False, "Evidence SHA-256 did not verify"
    coverage = detail.get("coverage", {})
    actual_kind = "pdf" if kind.startswith("pdf_") else kind
    if coverage.get("kind") != actual_kind:
        return False, "Source classification is incorrect"
    if coverage.get("summary_coverage") not in (
        "extractive_preview_only", "duplicate_reuses_existing_evidence"):
        return False, "Unexpected extraction-only coverage claim"
    if detail.get("complete_verified") is not False:
        return False, "Full-source learning was falsely marked verified"
    if kind == "website":
        ok = coverage.get("extracted_characters", 0) > 150
        return ok, "Extracted website HTML text" if ok else "Insufficient webpage text"
    if kind in ("pdf", "pdf_multi"):
        pages = coverage.get("pages_total")
        ok = isinstance(pages, int) and pages >= 1 and pages == coverage.get("pages_extracted")
        if kind == "pdf_multi":
            ok = ok and pages == 10
        return ok, f"Verified text extracted on {pages} PDF pages" if ok else "PDF page count mismatch"
    if kind == "youtube":
        cues = coverage.get("cue_count")
        seconds = coverage.get("last_cue_seconds")
        ok = isinstance(cues, int) and cues > 0 and seconds > 0 and (
            coverage.get("full_video_visuals_verified") is False)
        return ok, f"Processed {cues} timestamped cues, through {seconds}s; no visuals verified" if ok else "No timestamped caption coverage"
    return False, "Unknown source kind"



def publisher_transcript_smoke(lib, root, url):
    """Publisher-hosted real timed subtitles; NOT a successful YouTube video fetch."""
    validate_url(url)
    opener = build_opener(ProxyHandler({}), StrictRedirect())
    with opener.open(Request(url, headers={"Accept":"text/plain",
                                              "User-Agent":"SuryadevStandalone/0.3"}),
                     timeout=20) as response:
        raw = response.read(2_000_001)
    if not raw or len(raw) > 2_000_000:
        raise ValueError("Publisher transcript empty or exceeds the 2 MB limit")
    cues = caption_cues(raw.decode("utf-8-sig"))
    if len(cues) < 30:
        raise RuntimeError("Too few timestamped publisher cues")
    span = caption_report(cues, max(end for _,end,_ in cues))
    filename = Path(root) / "cs50-official-subtitles.srt"
    filename.write_bytes(raw)
    learning = import_transcript(lib, filename,
        "https://www.youtube.com/watch?v=mgBpcQRDtl0", use_ollama=False)
    saved = lib.db.execute("SELECT job_id FROM findings WHERE sha256=?",
                           (learning["sha256"],)).fetchone()
    if not saved:
        raise RuntimeError("Publisher captions did not reach the finding ledger")
    detail = task_detail(lib.db, root, saved[0])
    if detail["evidence_state"] != "verified" or detail["complete_verified"]:
        raise RuntimeError("Transcript evidence integrity failed or video falsely verified")
    return {
        "status": "PASS_TRANSCRIPT_ONLY", "evidence_state":"verified",
        "detail": f"Real CS50 publisher transcript: {len(cues)} timestamped cues; "
                  "imported and hash-verified. YouTube download/visuals NOT verified.",
        "coverage": {
            "cue_count":len(cues), "last_cue_seconds":span["last_cue_seconds"],
            "full_video_visuals_verified":False,
            "full_audio_coverage_verified":False,
            "learning_mode":"official_publisher_subtitles_manual_import",
        },
    }


def publisher_auto_recovery_smoke(lib, root, transcript_url):
    """Real direct CS50 CDN subtitle fallback, without a fresh YouTube request."""
    video="https://www.youtube.com/watch?v=mgBpcQRDtl0"
    plan_path=Path(root)/"approved-cs50-recovery.json"
    plan_path.write_text(json.dumps({
        "approved_urls":[],"approved_feeds":[],
        "allowed_source_hosts":["cdn.cs50.net"],
        "approved_publisher_transcripts":[{
            "video_url":video,"transcript_url":transcript_url}],
        "max_new_per_cycle":1,"max_queued":5}),encoding="utf-8")
    plan=read_plan(plan_path)
    job=lib.add(video)
    with lib.db:
        lib.db.execute(
            "UPDATE jobs SET status='failed',error=?,updated=? WHERE id=?",
            ("DownloadError: HTTP Error 429: Too Many Requests",
             time.time()-30,job))
    result=recover_failed_video_from_publisher(lib,plan,use_ollama=False)
    if result["status"] != "publisher_transcript_recovered":
        raise RuntimeError("CS50 publisher recovery not completed: " + str(result))
    detail=task_detail(lib.db,root,job)
    report=detail.get("coverage",{})
    if (detail["evidence_state"] != "verified" or
            detail.get("complete_verified") is not False or
            not detail.get("publisher_recovery") or
            report.get("cue_count",0) < 30 or
            report.get("youtube_extraction_success") is not False or
            report.get("full_video_visuals_verified") is not False):
        raise RuntimeError("Publisher-only recovery verification or provenance failed")
    return {
        "status":"PASS_PUBLISHER_RECOVERY_ONLY",
        "evidence_state":"verified",
        "detail":"Official publisher timed captions recovered for a previously "
                 "failed YouTube assignment; no YouTube access, visuals or "
                 "full audiovisual comprehension verified.",
        "coverage":{"cue_count":report["cue_count"],
                    "last_cue_seconds":report["last_cue_seconds"],
                    "publisher_transcript_only":True,
                    "youtube_video_verified":False,
                    "previous_youtube_error_audited":True},
    }


def run_real_sources():
    results = []
    with tempfile.TemporaryDirectory(prefix="suryadev-live-smoke-") as root:
        lib = Library(root)
        try:
            for kind, url in TEST_SOURCES:
                print("LIVE SOURCE START:", kind, url, flush=True)
                started = time.monotonic()
                item = {"kind": kind, "url": url, "status": "FAILED",
                        "duration_seconds": 0, "evidence_state": "not_recorded",
                        "detail": "", "coverage": {}}
                try:
                    if kind == "publisher_srt":
                        item.update(publisher_transcript_smoke(lib, root, url))
                        item["duration_seconds"] = round(time.monotonic() - started, 2)
                        results.append(item)
                        print("LIVE SOURCE RESULT:", json.dumps(item, ensure_ascii=False), flush=True)
                        continue
                    if kind == "publisher_auto_fallback":
                        item.update(publisher_auto_recovery_smoke(lib, root, url))
                        item["duration_seconds"] = round(time.monotonic() - started, 2)
                        results.append(item)
                        print("LIVE SOURCE RESULT:", json.dumps(item, ensure_ascii=False), flush=True)
                        continue
                    job_id = lib.add(url)
                    result = lib.run_next(use_ollama=False)
                    detail = task_detail(lib.db, root, job_id)
                    item["evidence_state"] = detail["evidence_state"]
                    item["coverage"] = detail.get("coverage", {})
                    if kind == "pdf_scanned":
                        err = detail.get("error") or result.get("error", "")
                        if (result["status"] == "failed" and
                                "PDF page text missing or scanned" in err and
                                detail.get("finding_id") is None):
                            item["status"] = "PASS_EXPECTED_REJECTION"
                            item["detail"] = "Scanned PDF has no readable text. Job failed safely without saved finding."
                        else:
                            item["status"] = classify(err) if result["status"] == "failed" else "FAILED"
                            item["detail"] = "Expected scanned PDF to fail without learning: " + err
                    elif result["status"] != "done":
                        item["detail"] = detail.get("error") or result.get("error", "")
                        item["status"] = classify(item["detail"])
                    else:
                        passed, explanation = verify_result(detail, kind)
                        if passed and kind == "pdf_multi":
                            digest = detail["sha256"]
                            saved = Path(root) / "evidence" / digest[:2] / (digest + ".txt")
                            stored = saved.read_text(encoding="utf-8")
                            passed = ("[PDF page 1/10]" in stored and
                                      "[PDF page 10/10]" in stored)
                            explanation = "All ten page markers verified in durable evidence" if passed else "Missing end-page content"
                        item["status"] = "PASS" if passed else "FAILED"
                        item["detail"] = explanation
                except Exception as exc:
                    item["detail"] = type(exc).__name__ + ": " + str(exc)[:350]
                    item["status"] = classify(item["detail"])
                item["duration_seconds"] = round(time.monotonic() - started, 2)
                results.append(item)
                print("LIVE SOURCE RESULT:", json.dumps(item, ensure_ascii=False), flush=True)
        finally:
            lib.db.close()
    return results


def main():
    results = run_real_sources()
    print("SURYDEV_REAL_SOURCE_REPORT=" + json.dumps(results, separators=(",", ":"), ensure_ascii=False))
    by_kind = {r["kind"]: r["status"] for r in results}
    print("TOTAL:", len(results), "PASS:", sum(s == "PASS" for s in by_kind.values()),
          "BLOCKED_EXTERNAL:", sum(s == "BLOCKED_EXTERNAL" for s in by_kind.values()),
          "FAILED:", sum(s == "FAILED" for s in by_kind.values()))
    print("EXPECTED_REJECTION:", sum(s == "PASS_EXPECTED_REJECTION" for s in by_kind.values()))
    print("REAL_PUBLISHER_TRANSCRIPTS:", sum(s == "PASS_TRANSCRIPT_ONLY" for s in by_kind.values()))
    print("REAL_PUBLISHER_RECOVERIES:",sum(
        s == "PASS_PUBLISHER_RECOVERY_ONLY" for s in by_kind.values()))
    # A provider/network block is a testing limitation; report explicitly.
    # Actual extraction/checksum defects fail CI rather than being hidden.
    if any(r["status"] == "FAILED" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
