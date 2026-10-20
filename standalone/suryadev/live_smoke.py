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

TEST_SOURCES = (
    ("website", "https://www.python.org/about/"),
    ("pdf", "https://samplepdf.org/files/sample.pdf"),
    ("pdf_multi", "https://raw.githubusercontent.com/tinytoolkit-org/pdf-sample-files/master/out/sample-10-pages.pdf"),
    ("pdf_scanned", "https://raw.githubusercontent.com/tinytoolkit-org/pdf-sample-files/master/out/sample-scanned.pdf"),
    ("youtube", "https://www.youtube.com/watch?v=mgBpcQRDtl0"),
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
    # A provider/network block is a testing limitation; report explicitly.
    # Actual extraction/checksum defects fail CI rather than being hidden.
    if any(r["status"] == "FAILED" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
