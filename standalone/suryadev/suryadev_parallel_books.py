"""Up to five independently checkpointed approved books in ONE SURYADEV worker.

I/O, source verification and bookkeeping can progress in parallel. Expensive
model interpretation is serialized with source LLM work using the same lock.
One book is never worked on twice simultaneously; unfinished lines persist
in the canonical book journal. This is not a second supervisor/process.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import time

from suryadev_book_continuity import read_book_plan
from suryadev_book_reader import BookLedger, file_sha256
from suryadev_liveops import atomic_json

MAX_ACTIVE_BOOKS = 5
RUNTIME = "book-concurrent-runtime.json"


class ParallelBookReader:
    def __init__(self, root, plan, *, model, use_ollama=True, vision_model=None,
                 clock=time.time, min_gap_seconds=10, observe=None,
                 fast_mode=False):
        if not use_ollama:
            raise ValueError("Parallel model reading requires enabled local Ollama")
        self.root = Path(root).resolve()
        self.path = Path(plan).resolve()
        self.plan = read_book_plan(self.path)
        self.model = model
        self.vision_model = vision_model
        self.clock = clock
        if type(fast_mode) is not bool:
            raise ValueError("fast_mode must be a boolean")
        self.fast_mode = fast_mode
        # With a checkpoint fully committed, the next pass needs no
        # arbitrary ten-second reading penalty. Capacity is remeasured by
        # the one supervisor before admitting another book.
        self.min_gap_seconds = (1.0 if fast_mode else
                                max(1.0, float(min_gap_seconds)))
        self.observe = observe
        self.summary_lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=MAX_ACTIVE_BOOKS,
                                       thread_name_prefix="suryadev-book")
        self.futures = {}
        self.next_at = {}
        self.cursor = 0
        self.closed = False

    def attach_model_lock(self, shared_lock):
        if self.futures:
            raise RuntimeError("Cannot replace model lock while books are running")
        self.summary_lock = shared_lock

    def _one(self, item):
        sha = item["sha256"]
        path = Path(item["path"])
        try:
            # Owner approval pins full source contents, not only pathname.
            if file_sha256(path) != sha:
                raise ValueError("Approved book SHA-256 changed")
            ledger = BookLedger(self.root)
            try:
                imported = ledger.import_book(path)
                if imported["book_id"] != "book-" + sha:
                    raise ValueError("Book identity mismatch")
                current = ledger.status(imported["book_id"])
                session = current["sessions"].get("ollama:" + self.model)
                if session and session.get("reached_end"):
                    if self.vision_model and path.suffix.lower() in (".pdf", ".epub"):
                        from suryadev_book_visuals import BookVisualAuditor
                        auditor = BookVisualAuditor(self.root)
                        try:
                            completed = auditor.ledger.db.execute(
                                "SELECT completed_at FROM book_visual_runs WHERE book_id=?",
                                (imported["book_id"],)).fetchone()
                            if completed:
                                return {"state":"book_complete","book_id":imported["book_id"]}
                            with self.summary_lock:
                                visual = auditor.run(imported["book_id"],
                                                     model=self.vision_model,max_items=1)
                            return {"state":"book_visual_step","book_id":imported["book_id"],
                                    "visual":visual,"comprehension_verified":False}
                        finally:
                            auditor.close()
                    return {"state":"book_complete","book_id":imported["book_id"]}
                def model_call(prompt, model):
                    with self.summary_lock:
                        if self.observe:
                            return self.observe(prompt, model)
                        from suryadev import summarize
                        return summarize(prompt, model,
                                         max_predict=320 if self.fast_mode else 512)
                receipt = ledger.read(imported["book_id"],model=self.model,
                    use_ollama=True,lines_per_step=self.plan["lines_per_step"],
                    max_steps=1,observe=model_call,
                    fast_mode=self.fast_mode)
                if file_sha256(path) != sha:
                    raise ValueError("Approved book changed during processing")
                return {"state":"learning_book_step","book_id":receipt["book_id"],
                    "title":receipt["title"],"processed_lines":receipt["lines_processed_total"],
                    "total_lines":receipt["lines_total"],"complete":receipt["reached_end"],
                    "model":self.model,"brahmagyan_acknowledged":False,
                    "comprehension_verified":False}
            finally:
                ledger.close()
        except (OSError,RuntimeError,ValueError,ImportError) as exc:
            return {"state":"book_paused_error","source":str(path),
                    "error":type(exc).__name__+": "+str(exc)[:180],
                    "brahmagyan_acknowledged":False}

    def tick(self, *, capacity, source_active=0, video_active=0):
        if self.closed:
            raise RuntimeError("Book worker pool is closed")
        now=float(self.clock())
        finished=[]
        for f, item in list(self.futures.items()):
            if not f.done():
                continue
            del self.futures[f]
            try:
                outcome = f.result()
            except Exception as exc:
                outcome = {"state":"book_paused_error",
                    "error":type(exc).__name__+": "+str(exc)[:160],
                    "source":item["path"],"brahmagyan_acknowledged":False}
            finished.append(outcome)
            self.next_at[item["sha256"]] = now + (300 if outcome["state"]=="book_paused_error"
                    else 3600 if outcome["state"]=="book_complete" else self.min_gap_seconds)
            atomic_json(self.root,"book-continuity-runtime.json",
                        dict(outcome, updated_at=now))
        safe=capacity.get("safe") is True
        allotted=min(MAX_ACTIVE_BOOKS,
            int(capacity.get("reserved_book_slots",0)),
            max(0,int(capacity.get("max_total",0))-max(0,int(source_active))-max(0,int(video_active))))
        started=[]
        if safe:
            occupied={item["sha256"] for item in self.futures.values()}
            books=self.plan["books"]
            for _ in range(len(books)):
                if len(self.futures)>=allotted or len(started)>=allotted:
                    break
                item=books[self.cursor % len(books)]
                self.cursor+=1
                sha=item["sha256"]
                if sha in occupied or self.next_at.get(sha,0)>now:
                    continue
                task=self.pool.submit(self._one,item)
                self.futures[task]=item
                occupied.add(sha)
                started.append(sha[:12])
        record={"schema":"suryadev.concurrent-books.v1",
            "target":MAX_ACTIVE_BOOKS, "active":len(self.futures),
            "started_this_tick":started,
            "finished":finished[-MAX_ACTIVE_BOOKS:],
            "reserved_capacity":int(capacity.get("reserved_book_slots",0)),
            "safe":safe, "updated_at":now,
            "local_model_concurrency":1,
            "fast_mode":self.fast_mode,
            "batch_target_lines":40 if self.fast_mode else self.plan["lines_per_step"],
            "verified_learning":False}
        atomic_json(self.root,RUNTIME,record)
        return record

    def close(self):
        if self.closed:
            return
        self.closed=True
        self.pool.shutdown(wait=True)
