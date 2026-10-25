"""Explicit opt-in 13-source teaching/capacity canary, NOT automatic source discovery.

Operator running --approve-curated-trial authorizes precisely the named open
technical books/pages/papers/videos. Safe to run ONLY while the one existing
SURYADEV worker is stopped; retains all prior evidence and approved sources.
Downloaded book PDFs remain local and are SHA-256-verified by the book ledger.
No unsupported live-YouTube availability, comprehension or Rishi claim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import time
from urllib.request import Request, build_opener, HTTPSHandler, ProxyHandler, HTTPRedirectHandler

BOOKS = (
    ("Think Python 2e", "thinkpython2.pdf", "https://greenteapress.com/thinkpython2/thinkpython2.pdf"),
    ("Think Stats 2e", "thinkstats2.pdf", "https://greenteapress.com/thinkstats2/thinkstats2.pdf"),
    ("Think Bayes 1e", "thinkbayes.pdf", "https://www.greenteapress.com/thinkbayes/thinkbayes.pdf"),
    ("Think Complexity 2e", "thinkcomplexity2.pdf", "https://greenteapress.com/complexity2/thinkcomplexity2.pdf"),
    ("Think DSP 1e", "thinkdsp.pdf", "https://greenteapress.com/thinkdsp/thinkdsp.pdf"),
)
PDFS = (
    "https://arxiv.org/pdf/1706.03762.pdf",  # Attention Is All You Need
    "https://arxiv.org/pdf/2106.09685.pdf",  # LoRA
    "https://arxiv.org/pdf/1810.04805.pdf",  # BERT
)
WEBSITES = (
    "https://docs.python.org/3/library/asyncio.html",
    "https://docs.python.org/3/library/sqlite3.html",
)
VIDEOS = (
    "https://www.youtube.com/watch?v=JP7ITIXGpHk",  # CS50P: functions, variables
    "https://www.youtube.com/watch?v=_b6NgY_pMdw",  # CS50P: conditionals
    "https://www.youtube.com/watch?v=-7xg8pGcP6w",  # CS50P: loops
)
MAX_BOOK_BYTES = 30 * 1024 * 1024


class DenyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download_book(url, destination, *, opener=None):
    """No redirects, public first-party URL, 30MiB cap, atomic PDF verification."""
    if url not in {x[2] for x in BOOKS}:
        raise ValueError("Unknown book URL is not approved by this trial")
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError("Book destination must not be a symlink")
    if destination.is_file():
        if not (1000 < destination.stat().st_size <= MAX_BOOK_BYTES):
            raise ValueError("Existing book size is invalid")
        with destination.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise ValueError("Existing book is not a PDF")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    opener = opener or build_opener(ProxyHandler({}),
                                  HTTPSHandler(context=ssl.create_default_context()),
                                  DenyRedirect())
    response = opener.open(Request(url, headers={"User-Agent":"Suryadev13Canary/1.0",
                "Accept":"application/pdf", "Accept-Encoding":"identity"}), timeout=35)
    tmp=destination.with_name(destination.name + ".partial-" + str(os.getpid()))
    try:
        with response:
            if getattr(response,"status",None) != 200:
                raise ValueError("Approved publisher PDF request did not return HTTP 200")
            content_type=response.headers.get("Content-Type","").split(";")[0].strip().lower()
            if content_type not in ("application/pdf","application/octet-stream"):
                raise ValueError("Publisher response is not advertised as a PDF")
            if int(response.headers.get("Content-Length") or 0)>MAX_BOOK_BYTES:
                raise ValueError("Book exceeds bounded 30MiB limit")
            count=0
            with tmp.open("xb") as output:
                while True:
                    chunk=response.read(65536)
                    if not chunk: break
                    count += len(chunk)
                    if count>MAX_BOOK_BYTES: raise ValueError("Book download over limit")
                    if count == len(chunk) and not chunk.startswith(b"%PDF-"):
                        raise ValueError("Publisher content is not a PDF")
                    output.write(chunk)
            if count<1024: raise ValueError("Book is unexpectedly small")
        os.replace(tmp,destination)
    finally:
        tmp.unlink(missing_ok=True)
    return destination


def prepare(root, *, downloader=download_book):
    from suryadev_book_continuity import approve_book,read_book_plan
    from suryadev_book_reader import file_sha256
    from suryadev_feeder import read_plan
    from suryadev_liveops import atomic_json
    from suryadev_lock import worker_lock
    from suryadev_video_review import VideoReview

    root=Path(root).expanduser().resolve(strict=True)
    if root.is_symlink() or not (root/"suryadev.sqlite3").is_file():
        raise ValueError("Requires the original SURYADEV canary root; no fresh workspace")
    book_paths=[]
    # Guard the entire operation with the SAME worker lock as the dashboard.
    with worker_lock(root):
        for title, filename, url in BOOKS:
            file=downloader(url,root/"benchmark-books"/filename)
            book_paths.append((title,file))
        for title,file in book_paths:
            report=approve_book(root,file,lines_per_step=20)
            print(json.dumps({"approved_book":title,"status":report["status"],
                              "sha256":report["source_sha256"]}),flush=True)
        books=read_book_plan(root/"book-plan.json")
        hashes={str(row["path"]):row["sha256"] for row in books["books"]}
        selected_books=[hashes[str(p)] for _,p in book_paths]
        if len(set(selected_books))!=5:
            raise ValueError("Five independently hashed book sources required")
        plan_file=root/"learning-plan.json"
        if not plan_file.is_file():
            raise ValueError("Existing owner source approval plan missing")
        read_plan(plan_file)
        prior=json.loads(plan_file.read_text(encoding="utf-8"))
        selected_urls=list(PDFS)+list(WEBSITES)+list(VIDEOS)
        from urllib.parse import urlsplit
        edited=dict(prior)
        edited["approved_urls"]=list(dict.fromkeys(
            list(prior.get("approved_urls",[]))+selected_urls))
        edited["allowed_source_hosts"]=list(dict.fromkeys(
            list(prior.get("allowed_source_hosts",[]))+
            [urlsplit(u).hostname for u in selected_urls]))
        temp=plan_file.with_name("learning-plan.canary-review.tmp")
        if temp.exists():
            raise FileExistsError("Previous unfinished candidate plan exists; review it")
        try:
            temp.write_text(json.dumps(edited,indent=2,ensure_ascii=False)+"\n",
                            encoding="utf-8")
            read_plan(temp)
            backup=plan_file.with_name(
                "learning-plan.before-13-source-"+str(time.time_ns())+".json")
            shutil.copy2(plan_file,backup)
            os.replace(temp,plan_file)
        finally:
            temp.unlink(missing_ok=True)
        manifest={"schema":"suryadev.workload-13.v1",
                  "pdf_urls":list(PDFS),"website_urls":list(WEBSITES),
                  "youtube_urls":list(VIDEOS),"book_sha256":selected_books}
        target=root/"benchmark-13-manifest.json"
        if target.exists():
            if json.loads(target.read_text(encoding="utf-8"))!=manifest:
                raise FileExistsError("Existing benchmark manifest differs; refusing overwrite")
        else:
            atomic_json(root,"benchmark-13-manifest.json",manifest)
        video=VideoReview(root,Path(__file__).resolve().parent)
        video.set_auto(True)
        return {"status":"approved_source_trial_prepared",
                "manifest":str(target),"books":len(selected_books),
                "pdf":len(PDFS),"website":len(WEBSITES),"youtube":len(VIDEOS),
                "existing_job_data_preserved":True,
                "worker_started":False,"understanding_verified":False,
                "video_provider_access_verified":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description="Explicit opt-in 13-source test material")
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--show",action="store_true")
    parser.add_argument("--approve-curated-trial",action="store_true")
    a=parser.parse_args(argv)
    inventory={"books":[{"title":x[0],"pdf_url":x[2]} for x in BOOKS],
               "pdf_urls":PDFS,"website_urls":WEBSITES,"youtube_urls":VIDEOS}
    if a.show:
        print(json.dumps(inventory,indent=2))
        return 0
    if not a.approve_curated_trial:
        parser.error("Review --show, then opt in with --approve-curated-trial")
    result=prepare(a.data)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
