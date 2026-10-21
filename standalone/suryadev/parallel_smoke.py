"""Real Garudanetra Chromium parallel-tab and PDF lane smoke check.

Run in a disposable SQLite directory. No Ollama needed. This demonstrates
automatic bounded concurrency, not video watching or AI comprehension.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from suryadev import Library
from suryadev_parallel import AdaptiveResearchWorkers
from suryadev_task_details import task_detail


def simulated_headroom():
    # Input fixture tests the scheduler's capacity response; the normal
    # SURYADEV worker always uses real psutil CPU/RAM/disk readings.
    return {
        "available": True, "cpu_percent": 10, "ram_percent": 30,
        "ram_total_gb": 16, "ram_used_gb": 5,
        "disk_percent": 25, "disk_free_gb": 90,
        "gpu": {"available": False},
    }


def run():
    with tempfile.TemporaryDirectory(prefix="suryadev-netra-parallel-") as root:
        lib = Library(root)
        urls = [
            "https://www.python.org/about/",
            "https://www.python.org/about/?suryadev_parallel=1",
            "https://samplepdf.org/files/sample.pdf",
        ]
        ids = {}
        try:
            for url in urls:
                ids[url] = lib.add(url)
            max_active = 0
            max_tabs = 0
            completed = []
            with AdaptiveResearchWorkers(root, use_ollama=False, check_seconds=10) as pool:
                with patch("suryadev_parallel.os.cpu_count",return_value=12):
                    first = pool.pump(telemetry=simulated_headroom())
                    if first["capacity"]["active_total"] < 3:
                        raise RuntimeError("Garudanetra scheduler did not admit 2 websites and 1 PDF")
                    until = time.monotonic()+65
                    while time.monotonic()<until:
                        max_active = max(max_active,len(pool.futures))
                        if pool.browser:
                            with pool.browser._lock:
                                max_tabs = max(max_tabs,len(pool.browser._tabs))
                        done = pool._reap()
                        completed.extend(done)
                        if not pool.futures:
                            break
                        time.sleep(.025)
                    if pool.futures:
                        raise RuntimeError("Parallel source processing did not finish within 65 seconds")
            statuses = dict(lib.db.execute("SELECT id,status FROM jobs"))
            evidence = [task_detail(lib.db, root, job_id) for job_id in ids.values()]
            print("PARALLEL_DIAGNOSTICS=" + json.dumps([
                {"id":item["id"],"status":item["status"],
                 "evidence_state":item["evidence_state"],
                 "error":item["error"],
                 "browser_engine":item.get("coverage",{}).get("browser_engine")}
                for item in evidence],ensure_ascii=False),flush=True)
            print("PARALLEL_COMPLETED=" + json.dumps(completed,ensure_ascii=False),flush=True)
            if any(item["status"]!="done" or item["evidence_state"]!="verified" for item in evidence):
                raise RuntimeError("Parallel run did not durably verify every real source")
            if max_active < 3 or max_tabs < 2:
                raise RuntimeError(f"Parallel concurrency not observed: jobs={max_active}, tabs={max_tabs}")
            if any(item.get("complete_verified") for item in evidence):
                raise RuntimeError("A source was incorrectly marked fully learned")
            result = {
                "result":"PASS", "jobs_submitted":3,
                "concurrent_jobs_observed":max_active,
                "concurrent_garudanetra_tabs_observed":max_tabs,
                "successful_findings":len(evidence),
                "website_engine":evidence[0]["coverage"].get("browser_engine"),
                "pdf_pages":evidence[-1]["coverage"].get("pages_total"),
                "full_comprehension_verified":False,
            }
            print("GARUDANETRA_REAL_PARALLEL_REPORT="+json.dumps(result),flush=True)
            return result
        finally:
            lib.db.close()


if __name__=="__main__":
    run()
