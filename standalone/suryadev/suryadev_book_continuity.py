"""Owner-approved books learned sequentially during idle SURYADEV worker cycles.

One book model step per tick, same process/single-worker lock. Never discover,
download, change book source approvals, or treat indexing as learning.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

from suryadev_book_reader import BookLedger, file_sha256
from suryadev_book_visuals import BookVisualAuditor
from suryadev_liveops import atomic_json

PLAN_SCHEMA = "suryadev.book-plan.v1"
RUNTIME = "book-continuity-runtime.json"
MAX_APPROVED_BOOKS = 100


def read_book_plan(path):
    plan_file = Path(path).expanduser().resolve(strict=True)
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise ValueError("invalid local book plan schema")
    entries = plan.get("books")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_APPROVED_BOOKS:
        raise ValueError("book plan requires 1..100 explicitly approved books")
    lines_per_step = plan.get("lines_per_step", 1)
    if type(lines_per_step) is not int or not 1 <= lines_per_step <= 40:
        raise ValueError("book plan lines_per_step requires 1..40")
    accepted = []
    known = set()
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError("book plan entries must contain only path and sha256")
        file = Path(item["path"]).expanduser()
        if not file.is_absolute():
            raise ValueError("book source must be an owner-approved absolute local path")
        file = file.resolve(strict=True)
        if (not file.is_file() or file.suffix.lower() not in (".txt",".md",".pdf",".epub")
                or file.stat().st_size > 100*1024*1024):
            raise ValueError("book file is not a supported local book <=100 MiB")
        digest = item["sha256"]
        if (not isinstance(digest, str) or len(digest) != 64
                or any(x not in "0123456789abcdef" for x in digest)):
            raise ValueError("book plan requires a lowercase SHA-256 fingerprint")
        if str(file).casefold() in known:
            raise ValueError("duplicate book plan path")
        known.add(str(file).casefold())
        accepted.append({"path":file,"sha256":digest})
    return {"books":accepted,"lines_per_step":lines_per_step}


def approve_book(root, source, *, lines_per_step=1, ocr=None):
    """Explicit operator action, not autonomous source selection/approval."""
    from suryadev_book_reader import file_sha256
    import shutil
    root=Path(root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    path=Path(source).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in (".txt",".md",".pdf",".epub"):
        raise ValueError("approve only an existing local supported book")
    if type(lines_per_step) is not int or not 1<=lines_per_step<=40:
        raise ValueError("lines_per_step must be 1..40")
    digest=file_sha256(path)
    plan=root/"book-plan.json"
    if plan.is_file():
        prior=read_book_plan(plan)
        if any(str(item["path"]).casefold()==str(path).casefold() and
               item["sha256"]!=digest for item in prior["books"]):
            raise ValueError("previously approved book changed; manual review/reapproval required")
    # Read all pages and reject OCR/EPUB errors BEFORE changing approvals.
    ledger=BookLedger(root)
    try:
        imported=ledger.import_book(path,ocr=ocr)
    finally:
        ledger.close()
    if file_sha256(path)!=digest or digest != imported["book_id"][5:]:
        raise RuntimeError("local book changed during import; approval refused")
    if plan.is_file():
        raw=json.loads(plan.read_text(encoding="utf-8"))
        validated=read_book_plan(plan)
        if any(str(item["path"]).casefold()==str(path).casefold() and
               item["sha256"]!=digest for item in validated["books"]):
            raise ValueError("previously approved book changed; manual review/reapproval required")
        if not any(str(item["path"]).casefold()==str(path).casefold()
                   for item in validated["books"]):
            if len(raw["books"])>=MAX_APPROVED_BOOKS:
                raise ValueError("owner-approved book limit reached")
            raw["books"].append({"path":str(path),"sha256":digest})
            backup=plan.with_name("book-plan.backup-"+str(time.time_ns())+".json")
            shutil.copy2(plan,backup)
        else:
            return {"status":"already_approved","book_id":imported["book_id"],
                    "plan":str(plan),"approved_books":len(raw["books"])}
    else:
        raw={"schema":PLAN_SCHEMA,"books":[{"path":str(path),"sha256":digest}],
             "lines_per_step":lines_per_step}
    atomic_json(root,"book-plan.json",raw)
    return {"status":"approved","book_id":imported["book_id"],"plan":str(plan),
            "approved_books":len(raw["books"]),"source_sha256":digest}



class BookEvidenceCollector:
    """Index approved local books into a verifiable source ledger; NEVER call an LLM.

    Safe to run in the existing single worker. A collection receipt means source
    lines were indexed, not that the model understood or tested the contents.
    """
    def __init__(self, root, plan, *, clock=time.time, min_gap_seconds=20):
        self.root=Path(root).expanduser().resolve()
        self.plan=read_book_plan(plan)
        self.clock=clock
        self.next_at=0
        self.cursor=0
        self.handled=set()
        self.min_gap_seconds=min_gap_seconds

    def tick(self, *, available=True):
        now=float(self.clock())
        if not available or now < self.next_at:
            return None
        self.next_at=now+self.min_gap_seconds
        for _ in range(len(self.plan["books"])):
            item=self.plan["books"][self.cursor % len(self.plan["books"])]
            self.cursor+=1
            path=item["path"]
            source_key=(str(path),item["sha256"])
            if source_key in self.handled:
                continue
            self.handled.add(source_key)
            try:
                if file_sha256(path)!=item["sha256"]:
                    raise ValueError("Approved book source SHA-256 changed; collection refused")
                ledger=BookLedger(self.root)
                try:
                    result=ledger.import_book(path)
                    check=ledger.verify(result["book_id"])
                finally:
                    ledger.close()
                if file_sha256(path)!=item["sha256"]:
                    raise RuntimeError("Approved book source changed during collection")
                state={"state":"indexed_evidence_only","book_id":result["book_id"],
                       "title":result["title"],"source_sha256":item["sha256"],
                       "lines_indexed":check["indexed_lines_verified"],
                       "already_indexed":result.get("already_imported",False),
                       "model_calls":0,"knowledge_verified":False,
                       "brahmagyan_acknowledged":False,"updated_at":time.time()}
            except (OSError,RuntimeError,ValueError,ImportError) as exc:
                state={"state":"collection_failed","source_sha256":item["sha256"],
                       "error":type(exc).__name__+": "+str(exc)[:240],
                       "model_calls":0,"knowledge_verified":False,
                       "updated_at":time.time()}
            atomic_json(self.root,"book-collection-runtime.json",state)
            return state
        return None


def may_study_books(capacity, pending_urls, *, youtube_rate_limited):
    """Read-only safe admission to idle research; cooldown is lane-specific."""
    from suryadev_sources import source_kind
    if (not isinstance(capacity,dict) or capacity.get("safe") is not True
            or capacity.get("max_total",0)<=0
            or capacity.get("active_total",0)!=0):
        return False
    return all(youtube_rate_limited and source_kind(url)=="youtube"
               for url in pending_urls)


class BookContinuity:
    def __init__(self, root, plan, *, model, use_ollama, clock=time.time,
                 min_gap_seconds=10, vision_model=None):
        self.root = Path(root).resolve()
        self.path = Path(plan).resolve()
        self.plan = read_book_plan(self.path)
        if not use_ollama:
            raise ValueError("Book continuity needs explicitly enabled Ollama; no preview-only learning")
        self.model = model
        self.vision_model = vision_model
        self.clock = clock
        self.next_at = 0
        self.min_gap_seconds = min_gap_seconds
        self.cursor = 0
        self.failed_until = {}

    def tick(self, *, available=True, observe=None):
        now = float(self.clock())
        if not available or now < self.next_at:
            return None
        self.next_at = now + self.min_gap_seconds
        ledger = BookLedger(self.root)
        try:
            books = self.plan["books"]
            for _ in range(len(books)):
                item = books[self.cursor % len(books)]
                self.cursor += 1
                path = item["path"]
                if self.failed_until.get(str(path), 0) > now:
                    continue
                try:
                    # Revalidate immutable approved file bytes on each selection.
                    if file_sha256(path) != item["sha256"]:
                        raise ValueError("owner-approved book SHA-256 changed")
                    imported = ledger.import_book(path)
                    book_id = imported["book_id"]
                    current = ledger.status(book_id)
                    session = current["sessions"].get("ollama:"+self.model)
                    if session and session["reached_end"]:
                        if self.vision_model and path.suffix.lower() in (".pdf",".epub"):
                            audit = BookVisualAuditor(self.root)
                            try:
                                completed = audit.ledger.db.execute(
                                    "SELECT completed_at FROM book_visual_runs WHERE book_id=?",
                                    (book_id,)).fetchone()
                                if completed:
                                    continue
                                atomic_json(self.root,RUNTIME,{
                                    "state":"book_visual_in_progress","book_id":book_id,
                                    "title":current["title"],"model":self.vision_model,
                                    "processed_lines":session["lines_processed"],
                                    "total_lines":current["lines_indexed"],
                                    "updated_at":time.time(),
                                    "brahmagyan_acknowledged":False})
                                visual = audit.run(book_id,model=self.vision_model,max_items=1)
                                result={"state":"book_visual_step","book_id":book_id,
                                        "visual":visual,"model":self.vision_model,
                                        "brahmagyan_acknowledged":False,"updated_at":time.time()}
                                atomic_json(self.root,RUNTIME,result)
                                return result
                            finally:
                                audit.close()
                        continue
                    atomic_json(self.root,RUNTIME,{
                        "state":"book_reading_in_progress","book_id":book_id,
                        "title":current["title"],"model":self.model,
                        "processed_lines":session["lines_processed"] if session else 0,
                        "total_lines":current["lines_indexed"],
                        "updated_at":time.time(),"brahmagyan_acknowledged":False})
                    receipt = ledger.read(book_id, model=self.model,
                        lines_per_step=self.plan["lines_per_step"],
                        max_steps=1, observe=observe)
                    result = {"state":"learning_book_step","book_id":book_id,
                              "title":receipt["title"],
                              "processed_lines":receipt["lines_processed_total"],
                              "total_lines":receipt["lines_total"],
                              "complete":receipt["reached_end"],
                              "model":self.model,
                              "brahmagyan_acknowledged":False,"updated_at":time.time()}
                    atomic_json(self.root, RUNTIME, result)
                    return result
                except (ValueError, RuntimeError, OSError, ImportError) as exc:
                    self.failed_until[str(path)] = now + 300
                    result = {"state":"book_paused_error",
                              "source":str(path), "error":type(exc).__name__ +
                              ": "+str(exc)[:200], "retry_after":now+300,
                              "updated_at":now,"brahmagyan_acknowledged":False}
                    atomic_json(self.root, RUNTIME, result)
                    return result
            result = {"state":"approved_books_complete_or_in_cooldown",
                      "approved_books":len(books),"updated_at":now,
                      "brahmagyan_acknowledged":False}
            atomic_json(self.root, RUNTIME, result)
            return result
        finally:
            ledger.close()
